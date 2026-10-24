"""Dotazy: poslanci – vyhledání, detail, souhrn hlasů."""

import sqlite3

from politika.db.dotazy.spolecne import aktualni_obdobi, bez_diakritiky, klub_sql


# Datum konce mandátu (členství v orgánu sněmovny daného období), NULL = mandát trvá.
_MANDAT_KONCI = """(SELECT z.do FROM zarazeni z
    WHERE z.id_osoba = p.id_osoba AND z.id_organ = p.id_obdobi
      AND z.do IS NOT NULL AND z.do < date('now') LIMIT 1)"""


def hledej_poslance(conn: sqlite3.Connection, text: str = "") -> list[dict]:
    """Najde poslance s trvajícím mandátem podle jména (bez ohledu na velikost písmen a diakritiku).

    :param text: část jména nebo příjmení; prázdný řetězec vrátí všechny
    :return: seznam ``{id_poslanec, id_osoba, jmeno, prijmeni, klub}`` seřazený podle příjmení
    """
    radky = conn.execute(
        f"""
        SELECT p.id_poslanec, p.id_osoba, o.jmeno, o.prijmeni,
               {klub_sql("p.id_osoba", "p.id_obdobi", "date('now')")} AS klub
        FROM poslanec p JOIN osoba o USING (id_osoba)
        WHERE p.id_obdobi = ? AND {_MANDAT_KONCI} IS NULL
        """,
        (aktualni_obdobi(conn),),
    ).fetchall()
    hledany = bez_diakritiky(text.strip())
    vysledek = [
        {"id_poslanec": r["id_poslanec"], "id_osoba": r["id_osoba"],
         "jmeno": f"{r['jmeno']} {r['prijmeni']}", "prijmeni": r["prijmeni"], "klub": r["klub"]}
        for r in radky
        if hledany in bez_diakritiky(f"{r['jmeno']} {r['prijmeni']}")
    ]
    return sorted(vysledek, key=lambda p: (bez_diakritiky(p["prijmeni"]), p["jmeno"]))


def poslanec_detail(conn: sqlite3.Connection, id_poslanec: int) -> sqlite3.Row | None:
    """Vrátí základní údaje poslance včetně aktuálního klubu a konce mandátu, nebo ``None``."""
    return conn.execute(
        f"""
        SELECT p.id_poslanec, p.id_osoba, p.id_obdobi, p.email, o.titul_pred, o.jmeno,
               o.prijmeni, o.titul_za, {_MANDAT_KONCI} AS mandat_do,
               {klub_sql("p.id_osoba", "p.id_obdobi", "date('now')")} AS klub
        FROM poslanec p JOIN osoba o USING (id_osoba)
        WHERE p.id_poslanec = ?
        """,
        (id_poslanec,),
    ).fetchone()


def souhrn_hlasu(conn: sqlite3.Connection, id_poslanec: int) -> dict[str, int]:
    """Vrátí počty hlasů poslance podle kódu (``{"A": 512, "B": 80, …}``)."""
    return dict(conn.execute(
        "SELECT vysledek, COUNT(*) FROM hlas WHERE id_poslanec = ? GROUP BY vysledek",
        (id_poslanec,),
    ).fetchall())
