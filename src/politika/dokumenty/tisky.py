"""Odkazy na soubory sněmovních tisků: PDF verzí tisku a DOCX pozměňovacích návrhů (rozhodnutí 1A).

Odkazy nejsou v otevřených datech, proto se pro každý tisk čte stránka historie
(``historie.sqw``) a stránky jednotlivých verzí (``tiskt.sqw``). Historie aktivních tisků
(projednávaných v nedávné schůzi) se obnovuje po ``OBNOVA_HISTORIE``, ostatní jen jednou.
Samotné soubory se nestahují – v evidenci je jen jejich odkaz na psp.cz (``cesta`` je NULL)
a aplikace na něj odkazuje; uživatel si otevře jen to, co chce číst.
"""

import sqlite3
from datetime import date, timedelta
from pathlib import PurePosixPath

from politika import config
from politika.db.dotazy.spolecne import aktualni_obdobi
from politika.dokumenty.evidence import je_starsi_nez, zaeviduj
from politika.dokumenty.odkazy import pdf_tisku, pozmenovaci_navrhy, verze_tisku
from politika.dokumenty.stahovani import PSP_URL, Stahovac, precti_html

OBNOVA_HISTORIE = timedelta(hours=20)
DNY_AKTIVITY = 60


def _relativni(url: str) -> str:
    """Odstraní z URL doménu psp.cz, aby byl jeden dokument evidován pod jedním klíčem."""
    return url.removeprefix(PSP_URL)


def bezpecny_nazev(nazev: str) -> str | None:
    """Vrátí jen jméno souboru z textu odkazu (bez cesty); prázdné nebo „..“ → ``None``.

    Název přichází ze stránky psp.cz – nesmí umožnit zápis mimo složku dat.
    """
    jmeno = PurePosixPath(nazev.replace("\\", "/")).name.strip()
    return jmeno if jmeno and jmeno not in (".", "..") else None


def _evidovano(conn: sqlite3.Connection, url: str) -> bool:
    """Zda je dokument už v evidenci (tj. byl někdy stažen)."""
    return conn.execute("SELECT 1 FROM dokument WHERE url = ?", (url,)).fetchone() is not None


def tisky_obdobi(conn: sqlite3.Connection) -> list[tuple[int, bool]]:
    """Vrátí tisky aktuálního období, o kterých se hlasovalo, jako ``[(ct, aktivni), …]``.

    Aktivní = projednávaný na schůzi, která skončila před méně než ``DNY_AKTIVITY`` dny nebo probíhá.
    """
    hranice = (date.today() - timedelta(days=DNY_AKTIVITY)).isoformat()
    return [(r[0], bool(r[1])) for r in conn.execute(
        """
        SELECT t.ct, MAX(s.do IS NULL OR s.do >= :hranice)
        FROM hlasovani h
        JOIN schuze s ON s.id_organ = h.id_organ AND s.cislo = h.schuze
        JOIN bod b ON b.id_schuze = s.id_schuze AND b.cislo = h.bod
        JOIN tisk t ON t.id_tisk = b.id_tisk
        WHERE h.id_organ = :obdobi AND t.id_obdobi = :obdobi
        GROUP BY t.ct ORDER BY t.ct
        """,
        {"hranice": hranice, "obdobi": aktualni_obdobi(conn)},
    )]


def tisky_schuzi(conn: sqlite3.Connection, schuze: set[int]) -> set[int]:
    """Vrátí čísla tisků aktuálního období, o kterých se hlasovalo na daných schůzích."""
    if not schuze:
        return set()
    return {r[0] for r in conn.execute(
        f"""
        SELECT DISTINCT t.ct
        FROM hlasovani h
        JOIN schuze s ON s.id_organ = h.id_organ AND s.cislo = h.schuze
        JOIN bod b ON b.id_schuze = s.id_schuze AND b.cislo = h.bod
        JOIN tisk t ON t.id_tisk = b.id_tisk
        WHERE h.id_organ = ? AND t.id_obdobi = h.id_organ
          AND h.schuze IN ({', '.join('?' * len(schuze))})
        """,
        (aktualni_obdobi(conn), *schuze),
    )}


def stahni_odkazy_tisku(conn: sqlite3.Connection, st: Stahovac, ct: int,
                        aktivni: bool = True) -> int:
    """Stáhne historii tisku a stránky jeho verzí a zaeviduje odkazy na PDF verzí a DOCX návrhů.

    :param aktivni: u aktivního tisku se stránka historie po čase stáhne znovu (přibývají návrhy)
    :return: počet nově zaevidovaných odkazů (PDF + DOCX)
    """
    slozka = config.DATA_DIR / "dokumenty" / "tisky" / f"{ct:04d}"
    url_historie = f"/sqw/historie.sqw?T={ct}&O=10"
    evidovano = _evidovano(conn, url_historie)
    prepsat = evidovano and aktivni and je_starsi_nez(conn, url_historie, OBNOVA_HISTORIE)
    cesta = st.stahni(url_historie, slozka / "historie.html", prepsat=prepsat)
    if prepsat or not evidovano:
        zaeviduj(conn, url_historie, "tisk_historie", cesta, ct=ct)
    historie = precti_html(cesta)

    nove = 0

    def odkaz(url: str, typ: str, **udaje) -> None:
        """Zaeviduje odkaz na neměnný soubor (bez stažení), pokud ještě není v evidenci."""
        nonlocal nove
        url = _relativni(url)
        if _evidovano(conn, url):
            return
        zaeviduj(conn, url, typ, None, ct=ct, **udaje)
        nove += 1

    for ct1 in verze_tisku(historie, ct):
        url_verze = f"/sqw/text/tiskt.sqw?o=10&ct={ct}&ct1={ct1}"
        cesta = st.stahni(url_verze, slozka / f"verze_{ct1}.html")
        if not _evidovano(conn, url_verze):
            zaeviduj(conn, url_verze, "tisk_verze", cesta, ct=ct, ct1=ct1)
        for url_pdf, nazev in pdf_tisku(precti_html(cesta)):
            if (nazev := bezpecny_nazev(nazev)) is not None:
                odkaz(url_pdf, "tisk_pdf", ct1=ct1, nazev=nazev)

    for navrh in pozmenovaci_navrhy(historie):
        if (nazev := bezpecny_nazev(navrh.soubor)) is None:
            continue
        odkaz(navrh.url, "sd_docx", cislo_sd=navrh.cislo_sd, id_osoba=navrh.id_osoba,
              nazev=nazev, popis=navrh.popis, datum=navrh.datum)
    conn.commit()
    return nove
