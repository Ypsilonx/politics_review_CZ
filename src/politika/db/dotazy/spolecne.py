"""Sdílené pomůcky pro dotazy: období, klub k datu, normalizace textu."""

import sqlite3
import unicodedata

ID_TYP_SNEMOVNA = 11
ID_TYP_KLUB = 1


def bez_diakritiky(text: str) -> str:
    """Vrátí text malými písmeny bez diakritiky (pro vyhledávání „strzinek“ = „Stržínek“)."""
    rozlozeny = unicodedata.normalize("NFKD", text.casefold())
    return "".join(z for z in rozlozeny if not unicodedata.combining(z))


def aktualni_obdobi(conn: sqlite3.Connection) -> int:
    """Vrátí ``id_organ`` posledního volebního období Poslanecké sněmovny."""
    return conn.execute(
        "SELECT id_organ FROM organ WHERE id_typ = ? ORDER BY od DESC LIMIT 1", (ID_TYP_SNEMOVNA,)
    ).fetchone()[0]


def klub_sql(osoba: str, obdobi: str, datum: str) -> str:
    """Poddotaz na zkratku klubu, jehož byla osoba členem k datu (v den přestupu ten nový).

    Parametry jsou výrazy SQL z nadřazeného dotazu (např. ``p.id_osoba``, ``h.datum``).
    """
    return f"""(SELECT o.zkratka FROM zarazeni z JOIN organ o ON o.id_organ = z.id_organ
        WHERE z.id_osoba = {osoba} AND o.id_typ = {ID_TYP_KLUB} AND o.id_nadrazeny = {obdobi}
          AND z.od <= {datum} AND (z.do IS NULL OR z.do >= {datum})
        ORDER BY z.od DESC LIMIT 1)"""
