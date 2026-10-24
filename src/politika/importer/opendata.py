"""Stažení ZIPů otevřených dat PSP a jejich import do databáze.

Zdroj je vždy kompletní snímek (rozdílové aktualizace PSP neposkytuje), proto
import každou tabulku v jedné transakci smaže a naplní znovu – je idempotentní.
Popis tabulek: psp.cz → Otevřená data (dokumentace jednotlivých sad).
"""

import shutil
import sqlite3
import time
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import httpx

from politika import config
from politika.importer.unl import parse_unl

Radek = dict[str, str | None]


def datum_cz(hodnota: str | None) -> str | None:
    """Převede datum ``dd.mm.yyyy`` na ISO ``yyyy-mm-dd``."""
    if hodnota is None:
        return None
    d, m, r = hodnota.split(".")
    return f"{r}-{m}-{d}"


def datum_iso(hodnota: str | None) -> str | None:
    """Zkrátí časový údaj ``yyyy-mm-dd hh`` na datum ``yyyy-mm-dd``."""
    return hodnota[:10] if hodnota else None


@dataclass(frozen=True)
class Tabulka:
    """Popis importu jednoho UNL souboru do jedné tabulky DB.

    :param soubor: glob souboru relativně ke složce sad (``poslanci/osoby.unl``)
    :param sloupce: všechny sloupce UNL v pořadí ze souboru
    :param cil: název tabulky v DB
    :param mapovani: sloupec DB → funkce vytvářející hodnotu z řádku UNL
    :param filtr: řádky, pro které vrátí False, se přeskočí
    :param poradi: klíč řazení před vložením; s ``INSERT OR REPLACE`` vyhrává poslední
        řádek se stejným klíčem (u schůzí a bodů tak schválený pořad přepíše pozvánku)
    """

    soubor: str
    sloupce: list[str]
    cil: str
    mapovani: dict[str, Callable[[Radek], object]]
    filtr: Callable[[Radek], bool] | None = None
    poradi: Callable[[Radek], object] | None = None


def _s(sloupec: str) -> Callable[[Radek], object]:
    """Vrátí funkci, která z řádku vezme hodnotu sloupce beze změny."""
    return lambda r: r[sloupec]


def _bez_pozvanky_naposled(r: Radek) -> bool:
    """Klíč řazení: řádky pozvánky (``pozvanka = 1``) první, schválený pořad poslední."""
    return r["pozvanka"] != "1"


TABULKY: list[Tabulka] = [
    Tabulka(
        "poslanci/osoby.unl",
        ["id_osoba", "pred", "prijmeni", "jmeno", "za", "narozeni", "pohlavi", "zmena", "umrti"],
        "osoba",
        {
            "id_osoba": _s("id_osoba"), "titul_pred": _s("pred"), "prijmeni": _s("prijmeni"),
            "jmeno": _s("jmeno"), "titul_za": _s("za"),
            "narozeni": lambda r: datum_cz(r["narozeni"]), "pohlavi": _s("pohlavi"),
        },
    ),
    Tabulka(
        "poslanci/poslanec.unl",
        ["id_poslanec", "id_osoba", "id_kraj", "id_kandidatka", "id_obdobi", "web", "ulice",
         "obec", "psc", "email", "telefon", "fax", "psp_telefon", "facebook", "foto"],
        "poslanec",
        {
            "id_poslanec": _s("id_poslanec"), "id_osoba": _s("id_osoba"), "id_kraj": _s("id_kraj"),
            "id_obdobi": _s("id_obdobi"), "email": _s("email"),
        },
    ),
    Tabulka(
        "poslanci/organy.unl",
        ["id_organ", "organ_id_organ", "id_typ_organu", "zkratka", "nazev_organu_cz",
         "nazev_organu_en", "od_organ", "do_organ", "priorita", "cl_organ_base"],
        "organ",
        {
            "id_organ": _s("id_organ"), "id_nadrazeny": _s("organ_id_organ"),
            "id_typ": _s("id_typ_organu"), "zkratka": _s("zkratka"), "nazev": _s("nazev_organu_cz"),
            "od": lambda r: datum_cz(r["od_organ"]), "do": lambda r: datum_cz(r["do_organ"]),
        },
    ),
    Tabulka(
        "poslanci/zarazeni.unl",
        ["id_osoba", "id_of", "cl_funkce", "od_o", "do_o", "od_f", "do_f"],
        "zarazeni",
        {
            "id_osoba": _s("id_osoba"), "id_organ": _s("id_of"),
            "od": lambda r: datum_iso(r["od_o"]), "do": lambda r: datum_iso(r["do_o"]),
        },
        filtr=lambda r: r["cl_funkce"] == "0",  # 1 = funkce, id_of je pak id funkce
    ),
    Tabulka(
        "schuze/schuze.unl",
        ["id_schuze", "id_org", "schuze", "od_schuze", "do_schuze", "aktualizace", "pozvanka"],
        "schuze",
        {
            "id_schuze": _s("id_schuze"), "id_organ": _s("id_org"), "cislo": _s("schuze"),
            "od": lambda r: datum_iso(r["od_schuze"]), "do": lambda r: datum_iso(r["do_schuze"]),
        },
        poradi=_bez_pozvanky_naposled,
    ),
    Tabulka(
        "schuze/bod_schuze.unl",
        ["id_bod", "id_schuze", "id_tisk", "id_typ", "bod", "uplny_naz", "uplny_kon", "poznamka",
         "id_bod_stav", "pozvanka", "rj", "pozn2", "druh_bodu", "id_sd", "zkratka"],
        "bod",
        {
            "id_bod": _s("id_bod"), "id_schuze": _s("id_schuze"), "id_tisk": _s("id_tisk"),
            "cislo": _s("bod"), "nazev": _s("uplny_naz"), "zkratka": _s("zkratka"),
        },
        poradi=_bez_pozvanky_naposled,
    ),
    Tabulka(
        "tisky/tisky.unl",
        ["id_tisk", "id_druh", "id_stav", "ct", "cislo_za", "id_navrh", "id_org", "id_org_obd",
         "id_osoba", "navrhovatel", "nazev_tisku", "predlozeno", "rozeslano", "dal",
         "tech_nos_dat", "uplny_nazev_tisku", "zm_lhuty", "lhuta", "rj", "t_url", "is_eu", "roz",
         "is_sdv", "status"],
        "tisk",
        {
            "id_tisk": _s("id_tisk"), "ct": _s("ct"), "id_obdobi": _s("id_org_obd"),
            "nazev": _s("nazev_tisku"), "uplny_nazev": _s("uplny_nazev_tisku"),
            "predlozeno": lambda r: datum_cz(r["predlozeno"]),
        },
    ),
    Tabulka(
        f"hl-{config.OBDOBI}/hl{config.OBDOBI[:4]}s.unl",
        ["id_hlasovani", "id_organ", "schuze", "cislo", "bod", "datum", "cas", "pro", "proti",
         "zdrzel", "nehlasoval", "prihlaseno", "kvorum", "druh_hlasovani", "vysledek",
         "nazev_dlouhy", "nazev_kratky"],
        "hlasovani",
        {
            **{k: _s(k) for k in ["id_hlasovani", "id_organ", "schuze", "cislo", "bod", "cas",
                                  "pro", "proti", "zdrzel", "nehlasoval", "prihlaseno", "kvorum",
                                  "vysledek", "nazev_dlouhy", "nazev_kratky"]},
            "datum": lambda r: datum_cz(r["datum"]), "druh": _s("druh_hlasovani"),
        },
    ),
    Tabulka(
        # Hlasy jsou rozdělené do více souborů (h1, h2, …).
        f"hl-{config.OBDOBI}/hl{config.OBDOBI[:4]}h*.unl",
        ["id_poslanec", "id_hlasovani", "vysledek"],
        "hlas",
        {"id_poslanec": _s("id_poslanec"), "id_hlasovani": _s("id_hlasovani"),
         "vysledek": _s("vysledek")},
    ),
]


def stahni_opendata(cil: Path, sady: list[str], client: httpx.Client | None = None) -> list[Path]:
    """Stáhne ZIPy otevřených dat a rozbalí každý do vlastní podsložky ``cil/<sada>/``.

    Předchozí obsah podsložky se smaže, aby nezůstaly soubory ze starého snímku.

    :param cil: složka pro ZIPy a rozbalená data
    :param sady: názvy sad bez přípony (``poslanci``, ``hl-2025ps`` …)
    :param client: HTTP klient (pro testy), jinak se vytvoří vlastní
    :return: cesty k rozbaleným podsložkám
    """
    cil.mkdir(parents=True, exist_ok=True)
    vlastni = client is None
    # retries opakuje jen nepovedené navázání spojení (psp.cz občas neodpoví na první pokus).
    client = client or httpx.Client(headers={"User-Agent": config.USER_AGENT}, timeout=120,
                                    transport=httpx.HTTPTransport(retries=3))
    slozky = []
    try:
        for i, sada in enumerate(sady):
            if i:
                time.sleep(config.PAUZA_MEZI_POZADAVKY)
            zip_cesta = cil / f"{sada}.zip"
            odpoved = client.get(f"{config.OPENDATA_URL}{sada}.zip")
            odpoved.raise_for_status()
            zip_cesta.write_bytes(odpoved.content)
            slozka = cil / sada
            shutil.rmtree(slozka, ignore_errors=True)
            with zipfile.ZipFile(zip_cesta) as z:
                z.extractall(slozka)
            slozky.append(slozka)
    finally:
        if vlastni:
            client.close()
    return slozky


def _radky(adresar: Path, t: Tabulka) -> Iterable[Radek]:
    """Vrátí řádky všech souborů tabulky (po filtru a seřazené, je-li to zadáno)."""
    soubory = sorted(adresar.glob(t.soubor))
    if not soubory:
        raise FileNotFoundError(f"V {adresar} chybí {t.soubor}")
    radky: Iterable[Radek] = (r for s in soubory for r in parse_unl(s, t.sloupce))
    if t.filtr:
        radky = filter(t.filtr, radky)
    if t.poradi:
        radky = sorted(radky, key=t.poradi)
    return radky


def importuj_vse(conn: sqlite3.Connection, adresar: Path) -> dict[str, int]:
    """Naimportuje všechny tabulky z rozbalených sad v ``adresar``.

    Každá tabulka se nahradí celá; vše proběhne v jedné transakci, takže při chybě
    zůstane v DB předchozí stav.

    :return: počty řádků v jednotlivých tabulkách po importu
    """
    pocty = {}
    with conn:
        for t in TABULKY:
            sloupce = list(t.mapovani)
            sql = (f"INSERT OR REPLACE INTO {t.cil} ({', '.join(sloupce)}) "
                   f"VALUES ({', '.join('?' * len(sloupce))})")
            conn.execute(f"DELETE FROM {t.cil}")
            conn.executemany(
                sql, ([f(r) for f in t.mapovani.values()] for r in _radky(adresar, t))
            )
            pocty[t.cil] = conn.execute(f"SELECT COUNT(*) FROM {t.cil}").fetchone()[0]
    return pocty
