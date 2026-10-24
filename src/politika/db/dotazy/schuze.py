"""Dotazy: schůze – seznam, pořad bodů a hlasování po bodech."""

import sqlite3
from collections import defaultdict

from politika.db.dotazy.hlasovani import HLASOVANI_S_BODEM
from politika.db.dotazy.spolecne import aktualni_obdobi


def seznam_schuzi(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Vrátí schůze aktuálního období (nejdřív s nejčerstvějším hlasováním) s počty bodů a hlasování."""
    return conn.execute(
        """
        SELECT s.cislo, s.od, s.do,
               (SELECT COUNT(*) FROM bod b WHERE b.id_schuze = s.id_schuze AND b.cislo > 0) AS bodu,
               (SELECT COUNT(*) FROM hlasovani h WHERE h.id_organ = s.id_organ AND h.schuze = s.cislo)
                 AS hlasovani,
               (SELECT MAX(h.datum) FROM hlasovani h
                 WHERE h.id_organ = s.id_organ AND h.schuze = s.cislo) AS posledni_hlasovani
        FROM schuze s WHERE s.id_organ = ?
        ORDER BY posledni_hlasovani DESC NULLS LAST, s.cislo DESC
        """,
        (aktualni_obdobi(conn),),
    ).fetchall()


def schuze_detail(conn: sqlite3.Connection, cislo: int) -> sqlite3.Row | None:
    """Vrátí schůzi aktuálního období podle čísla, nebo ``None``."""
    return conn.execute("SELECT * FROM schuze WHERE id_organ = ? AND cislo = ?",
                        (aktualni_obdobi(conn), cislo)).fetchone()


def body_s_hlasovanim(conn: sqlite3.Connection, cislo: int) -> list[dict]:
    """Vrátí pořad schůze: body s tiskem a jejich hlasování (bod 0 = procedurální mimo body).

    :return: ``[{bod: Row | None, hlasovani: [Row, …]}, …]`` v pořadí bodů; bod 0 na konci
    """
    obdobi = aktualni_obdobi(conn)
    body = conn.execute(
        """
        SELECT b.cislo, b.nazev, b.zkratka, t.ct FROM bod b
        JOIN schuze s ON s.id_schuze = b.id_schuze
        LEFT JOIN tisk t ON t.id_tisk = b.id_tisk
        WHERE s.id_organ = ? AND s.cislo = ? AND b.cislo > 0
        ORDER BY b.cislo
        """,
        (obdobi, cislo),
    ).fetchall()
    podle_bodu: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for h in conn.execute(
        f"SELECT * FROM ({HLASOVANI_S_BODEM}) WHERE id_organ = ? AND schuze = ? ORDER BY cislo",
        (obdobi, cislo),
    ):
        podle_bodu[h["bod"] or 0].append(h)
    vysledek = [{"bod": b, "hlasovani": podle_bodu.get(b["cislo"], [])} for b in body]
    if podle_bodu.get(0):
        vysledek.append({"bod": None, "hlasovani": podle_bodu[0]})
    return vysledek
