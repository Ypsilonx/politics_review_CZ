"""Čtecí dotazy nad databází pro webové rozhraní."""

import sqlite3
import unicodedata
from dataclasses import dataclass, field

ID_TYP_SNEMOVNA = 11
ID_TYP_KLUB = 1


def _bez_diakritiky(text: str) -> str:
    """Vrátí text malými písmeny bez diakritiky (pro vyhledávání „strzinek“ = „Stržínek“)."""
    rozlozeny = unicodedata.normalize("NFKD", text.casefold())
    return "".join(z for z in rozlozeny if not unicodedata.combining(z))


def aktualni_obdobi(conn: sqlite3.Connection) -> int:
    """Vrátí ``id_organ`` posledního volebního období Poslanecké sněmovny."""
    return conn.execute(
        "SELECT id_organ FROM organ WHERE id_typ = ? ORDER BY od DESC LIMIT 1", (ID_TYP_SNEMOVNA,)
    ).fetchone()[0]


def _klub_sql(osoba: str, obdobi: str, datum: str) -> str:
    """Poddotaz na zkratku klubu, jehož byla osoba členem k datu.

    Parametry jsou výrazy SQL z nadřazeného dotazu (např. ``p.id_osoba``, ``h.datum``).
    """
    return f"""(SELECT o.zkratka FROM zarazeni z JOIN organ o ON o.id_organ = z.id_organ
        WHERE z.id_osoba = {osoba} AND o.id_typ = {ID_TYP_KLUB} AND o.id_nadrazeny = {obdobi}
          AND z.od <= {datum} AND (z.do IS NULL OR z.do >= {datum}) LIMIT 1)"""


def hledej_poslance(conn: sqlite3.Connection, text: str = "") -> list[dict]:
    """Najde poslance aktuálního období podle jména (bez ohledu na velikost písmen a diakritiku).

    :param text: část jména nebo příjmení; prázdný řetězec vrátí všechny
    :return: seznam ``{id_poslanec, jmeno, klub}`` seřazený podle příjmení
    """
    id_obdobi = aktualni_obdobi(conn)
    radky = conn.execute(
        f"""
        SELECT p.id_poslanec, o.titul_pred, o.jmeno, o.prijmeni, o.titul_za,
               {_klub_sql("p.id_osoba", "p.id_obdobi", "date('now')")} AS klub
        FROM poslanec p JOIN osoba o USING (id_osoba)
        WHERE p.id_obdobi = ?
        """,
        (id_obdobi,),
    ).fetchall()
    hledany = _bez_diakritiky(text.strip())
    vysledek = [
        {"id_poslanec": r["id_poslanec"], "jmeno": f"{r['jmeno']} {r['prijmeni']}",
         "prijmeni": r["prijmeni"], "klub": r["klub"]}
        for r in radky
        if hledany in _bez_diakritiky(f"{r['jmeno']} {r['prijmeni']}")
    ]
    return sorted(vysledek, key=lambda p: (_bez_diakritiky(p["prijmeni"]), p["jmeno"]))


def poslanec_detail(conn: sqlite3.Connection, id_poslanec: int) -> sqlite3.Row | None:
    """Vrátí základní údaje poslance včetně aktuálního klubu, nebo ``None``."""
    return conn.execute(
        f"""
        SELECT p.id_poslanec, p.id_osoba, p.id_obdobi, p.email, o.titul_pred, o.jmeno,
               o.prijmeni, o.titul_za,
               {_klub_sql("p.id_osoba", "p.id_obdobi", "date('now')")} AS klub
        FROM poslanec p JOIN osoba o USING (id_osoba)
        WHERE p.id_poslanec = ?
        """,
        (id_poslanec,),
    ).fetchone()


# Hlasování spojené s bodem schůze a tiskem (bod je v hlasování číslo bodu v rámci schůze).
# Bod 0 je u PSP „Pořad schůze“ = souhrn procedurálních hlasování mimo projednávaný bod
# (přestávky, přerušení…), proto bez vlastního názvu nese obecný popis místo názvu bodu.
_HLASOVANI_S_BODEM = """
    SELECT h.*, b.nazev AS bod_nazev, t.ct AS tisk_ct,
           COALESCE(h.nazev_dlouhy,
                    CASE WHEN h.bod = 0 THEN 'Procedurální hlasování' ELSE b.nazev END) AS popis
    FROM hlasovani h
    LEFT JOIN schuze s ON s.id_organ = h.id_organ AND s.cislo = h.schuze
    LEFT JOIN bod b ON b.id_schuze = s.id_schuze AND b.cislo = h.bod
    LEFT JOIN tisk t ON t.id_tisk = b.id_tisk
"""


def hlasovani_poslance(
    conn: sqlite3.Connection, id_poslanec: int, limit: int = 50, offset: int = 0
) -> list[sqlite3.Row]:
    """Vrátí hlasování poslance od nejnovějšího, i s jeho hlasem (sloupec ``hlas``)."""
    return conn.execute(
        f"""
        SELECT x.*, hl.vysledek AS hlas FROM ({_HLASOVANI_S_BODEM}) x
        JOIN hlas hl ON hl.id_hlasovani = x.id_hlasovani AND hl.id_poslanec = ?
        ORDER BY x.datum DESC, x.cas DESC, x.cislo DESC
        LIMIT ? OFFSET ?
        """,
        (id_poslanec, limit, offset),
    ).fetchall()


def hlasovani_detail(conn: sqlite3.Connection, id_hlasovani: int) -> sqlite3.Row | None:
    """Vrátí jedno hlasování s názvem bodu a číslem tisku, nebo ``None``."""
    return conn.execute(
        f"SELECT * FROM ({_HLASOVANI_S_BODEM}) WHERE id_hlasovani = ?", (id_hlasovani,)
    ).fetchone()


@dataclass
class Klub:
    """Hlasy jednoho klubu v hlasování: počty podle kódu hlasu a seznam poslanců."""

    zkratka: str
    pocty: dict[str, int] = field(default_factory=dict)
    poslanci: list[dict] = field(default_factory=list)


def hlasy_po_klubech(conn: sqlite3.Connection, id_hlasovani: int) -> list[Klub]:
    """Rozdělí hlasy poslanců podle klubu, jehož byli členy v den hlasování.

    :return: kluby seřazené podle počtu poslanců (sestupně); bez klubu = „nezařazení“
    """
    radky = conn.execute(
        f"""
        SELECT hl.id_poslanec, hl.vysledek, o.jmeno, o.prijmeni,
               {_klub_sql("p.id_osoba", "h.id_organ", "h.datum")} AS klub
        FROM hlas hl
        JOIN hlasovani h ON h.id_hlasovani = hl.id_hlasovani
        JOIN poslanec p ON p.id_poslanec = hl.id_poslanec
        JOIN osoba o ON o.id_osoba = p.id_osoba
        WHERE hl.id_hlasovani = ?
        ORDER BY o.prijmeni
        """,
        (id_hlasovani,),
    ).fetchall()
    kluby: dict[str, Klub] = {}
    for r in radky:
        klub = kluby.setdefault(r["klub"] or "nezařazení", Klub(r["klub"] or "nezařazení"))
        klub.pocty[r["vysledek"]] = klub.pocty.get(r["vysledek"], 0) + 1
        klub.poslanci.append({"id_poslanec": r["id_poslanec"], "hlas": r["vysledek"],
                              "jmeno": f"{r['jmeno']} {r['prijmeni']}"})
    return sorted(kluby.values(), key=lambda k: -len(k.poslanci))
