"""Stažení textů stenozáznamů – jen úseků, ve kterých se hlasovalo.

psp.cz zavírá spojení po každé odpovědi (``Connection: close``) a omezuje počet nových spojení,
takže každý požadavek je drahý. Úseky (``sNNNttt.htm``, ~10 minut jednání) se proto vybírají
podle časů z otevřených dat (tabulka ``steno``): úsek, do jehož času hlasování spadá, a jeho
sousedé – výsledek se často vyhlašuje až v dalším úseku a předmět bývá v předchozím.
Neautorizované úseky se po ``OBNOVA_NEAUTORIZOVANYCH`` stáhnou znovu.
"""

import sqlite3
from datetime import date, timedelta

import httpx

from politika import config
from politika.db.dotazy.spolecne import aktualni_obdobi
from politika.dokumenty.evidence import je_starsi_nez, zaeviduj
from politika.dokumenty.odkazy import je_autorizovano
from politika.dokumenty.stahovani import Stahovac, precti_html

OBNOVA_NEAUTORIZOVANYCH = timedelta(days=3)


def schuze_obdobi(conn: sqlite3.Connection) -> list[int]:
    """Vrátí čísla schůzí aktuálního období, ve kterých se hlasovalo (vzestupně)."""
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT schuze FROM hlasovani WHERE id_organ = ? ORDER BY schuze",
        (aktualni_obdobi(conn),),
    )]


def cerstve_schuze(conn: sqlite3.Connection, dny: int) -> set[int]:
    """Vrátí čísla schůzí aktuálního období s hlasováním za posledních ``dny`` dní."""
    hranice = (date.today() - timedelta(days=dny)).isoformat()
    return {r[0] for r in conn.execute(
        "SELECT DISTINCT schuze FROM hlasovani WHERE id_organ = ? AND datum >= ?",
        (aktualni_obdobi(conn), hranice),
    )}


def _minuty(cas: str) -> int:
    """Převede ``HH:MM`` na minuty od půlnoci."""
    return int(cas[:2]) * 60 + int(cas[3:5])


def potrebne_useky(conn: sqlite3.Connection, schuze: int) -> list[int]:
    """Vrátí čísla úseků schůze, ve kterých (nebo vedle kterých) se hlasovalo.

    Úseky bez známého času se berou, pokud je ten den nějaké hlasování.
    """
    obdobi = aktualni_obdobi(conn)
    useky = conn.execute(
        "SELECT turn, datum, od_t, do_t FROM steno WHERE id_organ = ? AND schuze = ?",
        (obdobi, schuze),
    ).fetchall()
    hlasovani = conn.execute(
        "SELECT datum, cas FROM hlasovani WHERE id_organ = ? AND schuze = ?", (obdobi, schuze)
    ).fetchall()
    dny = {h["datum"] for h in hlasovani}
    existujici = {u["turn"] for u in useky}
    potrebne: set[int] = set()
    s_casem = []  # (turn, začátek, konec) v absolutních minutách – úsek přes půlnoc i hlasování po ní
    for u in useky:
        if u["od_t"] is None or u["do_t"] is None or u["od_t"] < 0 or u["do_t"] < 0:
            if u["datum"] in dny:
                potrebne.add(u["turn"])
            continue
        delka = (u["do_t"] - u["od_t"]) % 1440  # přes půlnoc je do_t < od_t
        zacatek = _absolutni_minuta(u["datum"], u["od_t"])
        s_casem.append((u["turn"], zacatek, zacatek + delka))
    for h in hlasovani:
        cas = _absolutni_minuta(h["datum"], _minuty(h["cas"]))
        pokryvajici = [t for t, od, do in s_casem if od <= cas <= do]
        if not pokryvajici:
            # Čas hlasování v metadatech chybí (typicky pozdě večer): nejbližší dřívější úsek
            # téhož jednacího dne (nejvýš 24 h zpět).
            drivejsi = [(od, t) for t, od, _ in s_casem if 0 <= cas - od < 1440]
            pokryvajici = [max(drivejsi)[1]] if drivejsi else []
        for t in pokryvajici:
            potrebne |= {t - 1, t, t + 1}
    return sorted(potrebne & existujici)


def _absolutni_minuta(datum: str, minuta: int) -> int:
    """Minuta od počátku letopočtu – časy různých dnů jdou porovnávat (i přes půlnoc)."""
    return date.fromisoformat(datum).toordinal() * 1440 + minuta


def stahni_steno_schuze(conn: sqlite3.Connection, st: Stahovac, schuze: int) -> int:
    """Stáhne a zaeviduje potřebné úseky stenozáznamu schůze.

    Úsek, který psp.cz ještě nezveřejnil (404), se přeskočí a zkusí se při příštím běhu.

    :return: počet nově stažených nebo obnovených úseků
    """
    zaklad = f"/eknih/{config.OBDOBI}/stenprot/{schuze:03d}schuz/"
    slozka = config.DATA_DIR / "steno" / config.OBDOBI / f"{schuze:03d}"
    stazeno = 0
    for turn in potrebne_useky(conn, schuze):
        soubor = f"s{schuze:03d}{turn:03d}.htm"
        url = zaklad + soubor
        stav = conn.execute("SELECT autorizovano FROM dokument WHERE url = ?", (url,)).fetchone()
        if stav is not None and (stav[0] or not je_starsi_nez(conn, url, OBNOVA_NEAUTORIZOVANYCH)):
            continue
        try:
            cesta = st.stahni(url, slozka / soubor, prepsat=stav is not None)
        except httpx.HTTPStatusError as chyba:
            if chyba.response.status_code == 404:
                continue
            raise
        zaeviduj(conn, url, "steno_usek", cesta, schuze=schuze, poradi=turn,
                 autorizovano=int(je_autorizovano(precti_html(cesta))))
        conn.commit()
        stazeno += 1
    return stazeno
