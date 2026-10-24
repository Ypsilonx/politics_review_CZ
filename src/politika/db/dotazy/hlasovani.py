"""Dotazy: hlasování – historie poslance, detail, rozdělení po klubech."""

import sqlite3
from dataclasses import dataclass, field

from politika.db.dotazy.spolecne import aktualni_obdobi, klub_sql

# Hlasování spojené s bodem schůze a tiskem (bod je v hlasování číslo bodu v rámci schůze).
# Bod 0 je u PSP „Pořad schůze“ = souhrn procedurálních hlasování mimo projednávaný bod
# (přestávky, přerušení…), proto bez vlastního názvu nese obecný popis místo názvu bodu.
# Připojený je i předmět ze stenozáznamu (predmet_hlasovani), pokud už je spárovaný.
# Pod jedním číslem bodu může být víc tisků (sloučená rozprava) – bere se první bod, aby
# hlasování nebylo ve výsledku dvakrát; hlasování k tisku hledá tisky.hlasovani_tisku zvlášť.
HLASOVANI_S_BODEM = """
    SELECT h.*, b.nazev AS bod_nazev, b.id_tisk, t.ct AS tisk_ct,
           COALESCE(REPLACE(h.nazev_dlouhy, '**', ' '),
                    CASE WHEN h.bod = 0 THEN 'Procedurální hlasování' ELSE b.nazev END) AS popis,
           p.druh AS predmet_druh, p.oznaceni AS predmet_oznaceni, p.otazka AS predmet_otazka,
           p.uryvek AS predmet_uryvek, p.zdroj_url AS predmet_zdroj,
           p.dokument_url AS predmet_dokument, p.autorizovano AS predmet_autorizovano
    FROM hlasovani h
    LEFT JOIN schuze s ON s.id_organ = h.id_organ AND s.cislo = h.schuze
    LEFT JOIN bod b ON b.id_bod = (SELECT MIN(b2.id_bod) FROM bod b2
                                   WHERE b2.id_schuze = s.id_schuze AND b2.cislo = h.bod)
    LEFT JOIN tisk t ON t.id_tisk = b.id_tisk
    LEFT JOIN predmet_hlasovani p ON p.id_hlasovani = h.id_hlasovani
"""


def hlasovani_poslance(
    conn: sqlite3.Connection, id_poslanec: int, limit: int = 50, offset: int = 0
) -> list[sqlite3.Row]:
    """Vrátí hlasování poslance od nejnovějšího, i s jeho hlasem (sloupec ``hlas``)."""
    return conn.execute(
        f"""
        SELECT x.*, hl.vysledek AS hlas FROM ({HLASOVANI_S_BODEM}) x
        JOIN hlas hl ON hl.id_hlasovani = x.id_hlasovani AND hl.id_poslanec = ?
        ORDER BY x.datum DESC, x.cas DESC, x.cislo DESC
        LIMIT ? OFFSET ?
        """,
        (id_poslanec, limit, offset),
    ).fetchall()


# Těsné hlasování: počet hlasů pro se od potřebného počtu liší nejvýš o tolik hlasů.
TESNE_ROZPETI = 5


def seznam_hlasovani(
    conn: sqlite3.Connection, schuze: int | None = None, vysledek: str | None = None,
    tesna: bool = False, druh: str | None = None, limit: int = 50, offset: int = 0,
) -> list[sqlite3.Row]:
    """Vrátí hlasování aktuálního období od nejnovějšího s volitelnými filtry.

    :param schuze: jen hlasování dané schůze
    :param vysledek: ``A`` přijato / ``R`` zamítnuto
    :param tesna: jen hlasování, kde rozhodlo nejvýš ``TESNE_ROZPETI`` hlasů
    :param druh: druh předmětu ze stenozáznamu (``pozmenovaci``, ``celek``, ``proceduralni``)
    """
    podminky, parametry = ["id_organ = ?"], [aktualni_obdobi(conn)]
    if schuze is not None:
        podminky.append("schuze = ?")
        parametry.append(schuze)
    if vysledek:
        podminky.append("vysledek = ?")
        parametry.append(vysledek)
    if tesna:
        podminky.append(f"ABS(pro - kvorum) <= {TESNE_ROZPETI}")
    if druh:
        podminky.append("predmet_druh = ?")
        parametry.append(druh)
    return conn.execute(
        f"SELECT * FROM ({HLASOVANI_S_BODEM}) WHERE {' AND '.join(podminky)} "
        "ORDER BY datum DESC, cas DESC, cislo DESC LIMIT ? OFFSET ?",
        [*parametry, limit, offset],
    ).fetchall()


def hlasovani_detail(conn: sqlite3.Connection, id_hlasovani: int) -> sqlite3.Row | None:
    """Vrátí jedno hlasování s názvem bodu a číslem tisku, nebo ``None``."""
    return conn.execute(
        f"SELECT * FROM ({HLASOVANI_S_BODEM}) WHERE id_hlasovani = ?", (id_hlasovani,)
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
               {klub_sql("p.id_osoba", "h.id_organ", "h.datum")} AS klub
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
