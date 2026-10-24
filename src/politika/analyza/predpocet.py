"""Předpočet tabulek pro statistiky – spouští se po každém importu otevřených dat."""

import sqlite3

from politika.db.dotazy.spolecne import ID_TYP_KLUB


def prepocitej(conn: sqlite3.Connection) -> dict[str, int]:
    """Naplní ``hlas_klub`` (hlas + klub k datu hlasování) a ``klub_hlasovani`` (většina klubu).

    Klub se určuje k datu hlasování, takže poslanec, který klub změnil, se počítá ke správnému.
    Hlas ``N`` (starší kód pro „ne“) se sjednocuje na ``B``.

    :return: počty řádků obou tabulek
    """
    with conn:
        conn.execute("DELETE FROM hlas_klub")
        conn.execute(
            f"""
            INSERT INTO hlas_klub (id_hlasovani, id_poslanec, vysledek, id_klub)
            SELECT hl.id_hlasovani, hl.id_poslanec,
                   CASE hl.vysledek WHEN 'N' THEN 'B' ELSE hl.vysledek END,
                   (SELECT z.id_organ FROM zarazeni z JOIN organ o ON o.id_organ = z.id_organ
                     WHERE z.id_osoba = p.id_osoba AND o.id_typ = {ID_TYP_KLUB}
                       AND o.id_nadrazeny = h.id_organ
                       AND z.od <= h.datum AND (z.do IS NULL OR z.do >= h.datum)
                     ORDER BY z.od DESC LIMIT 1)
            FROM hlas hl
            JOIN hlasovani h ON h.id_hlasovani = hl.id_hlasovani
            JOIN poslanec p ON p.id_poslanec = hl.id_poslanec
            """
        )
        conn.execute("DELETE FROM klub_hlasovani")
        conn.execute(
            """
            INSERT INTO klub_hlasovani (id_hlasovani, id_klub, ano, ne, vetsina)
            SELECT id_hlasovani, id_klub, ano, ne,
                   CASE WHEN ano > ne THEN 'A' WHEN ne > ano THEN 'B' END
            FROM (SELECT id_hlasovani, id_klub,
                         SUM(vysledek = 'A') AS ano, SUM(vysledek = 'B') AS ne
                  FROM hlas_klub WHERE id_klub IS NOT NULL
                  GROUP BY id_hlasovani, id_klub)
            """
        )
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("hlas_klub", "klub_hlasovani")}
