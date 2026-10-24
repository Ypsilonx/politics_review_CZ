"""Dotazy: sledovaní poslanci a kluby (skupiny) a proud jejich hlasování."""

import sqlite3

from politika.db.dotazy.hlasovani import HLASOVANI_S_BODEM
from politika.db.dotazy.spolecne import ID_TYP_KLUB, aktualni_obdobi

VYCHOZI_SKUPINA = "Moji sledovaní"


def skupiny(conn: sqlite3.Connection) -> list[str]:
    """Vrátí názvy skupin (výchozí první, i když je prázdná)."""
    nazvy = [r[0] for r in conn.execute("SELECT DISTINCT skupina FROM sledovany ORDER BY skupina")]
    return [VYCHOZI_SKUPINA] + [n for n in nazvy if n != VYCHOZI_SKUPINA]


def polozky(conn: sqlite3.Connection, skupina: str | None = None) -> list[dict]:
    """Vrátí sledované položky (s názvem pro zobrazení), volitelně jen jedné skupiny.

    :return: ``[{typ, id, skupina, nazev, klub, id_osoba}, …]`` – u klubu ``klub`` = zkratka
    """
    radky = conn.execute(
        f"""
        SELECT s.typ, s.id, s.skupina,
               CASE s.typ WHEN 'poslanec' THEN o.jmeno || ' ' || o.prijmeni ELSE org.zkratka END AS nazev,
               p.id_osoba, org.zkratka AS klub
        FROM sledovany s
        LEFT JOIN poslanec p ON s.typ = 'poslanec' AND p.id_poslanec = s.id
        LEFT JOIN osoba o ON o.id_osoba = p.id_osoba
        LEFT JOIN organ org ON s.typ = 'klub' AND org.id_organ = s.id AND org.id_typ = {ID_TYP_KLUB}
        WHERE ? IS NULL OR s.skupina = ?
        ORDER BY s.skupina, s.typ DESC, o.prijmeni, org.zkratka
        """,
        (skupina, skupina),
    ).fetchall()
    return [dict(r) for r in radky]


def je_sledovany(conn: sqlite3.Connection, typ: str, id_: int) -> bool:
    """Zda je poslanec / klub v některé skupině."""
    return conn.execute("SELECT 1 FROM sledovany WHERE typ = ? AND id = ?", (typ, id_)).fetchone() \
        is not None


def pridej(conn: sqlite3.Connection, typ: str, id_: int, skupina: str = VYCHOZI_SKUPINA) -> None:
    """Přidá poslance / klub do skupiny (opakované přidání nic nezmění)."""
    with conn:
        conn.execute("INSERT OR IGNORE INTO sledovany (typ, id, skupina) VALUES (?, ?, ?)",
                     (typ, id_, skupina.strip() or VYCHOZI_SKUPINA))


def odeber(conn: sqlite3.Connection, typ: str, id_: int, skupina: str | None = None) -> None:
    """Odebere poslance / klub ze skupiny, bez skupiny ze všech."""
    with conn:
        conn.execute("DELETE FROM sledovany WHERE typ = ? AND id = ? AND (? IS NULL OR skupina = ?)",
                     (typ, id_, skupina, skupina))


def kluby_obdobi(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Vrátí kluby aktuálního období (pro výběr ke sledování)."""
    return conn.execute(
        "SELECT id_organ, zkratka, nazev FROM organ WHERE id_typ = ? AND id_nadrazeny = ? "
        "AND (do IS NULL OR do >= date('now')) ORDER BY zkratka",
        (ID_TYP_KLUB, aktualni_obdobi(conn)),
    ).fetchall()


def proud(conn: sqlite3.Connection, skupina: str | None = None, limit: int = 30,
          offset: int = 0) -> list[dict]:
    """Proud hlasování, kterých se účastnili sledovaní (od nejnovějšího).

    Každá položka: ``{"h": hlasování, "poslanci": [...], "kluby": [...]}``. U poslance je hlas,
    klub a příznaky ``proti_klubu`` a ``chybel_u_celku`` (nepřítomen u hlasování o návrhu
    jako celku); u klubu je jeho většinový hlas a počty Ano/Ne.
    """
    sledovani = polozky(conn, skupina)
    poslanci = sorted({p["id"] for p in sledovani if p["typ"] == "poslanec"})
    kluby = sorted({p["id"] for p in sledovani if p["typ"] == "klub"})
    if not poslanci and not kluby:
        return []
    znacky_p = ",".join("?" * len(poslanci)) or "NULL"
    znacky_k = ",".join("?" * len(kluby)) or "NULL"
    id_hlasovani = [r[0] for r in conn.execute(
        f"""
        SELECT h.id_hlasovani FROM hlasovani h
        WHERE h.id_organ = ? AND (
            EXISTS (SELECT 1 FROM hlas_klub hk WHERE hk.id_hlasovani = h.id_hlasovani
                    AND hk.id_poslanec IN ({znacky_p}))
         OR EXISTS (SELECT 1 FROM klub_hlasovani kh WHERE kh.id_hlasovani = h.id_hlasovani
                    AND kh.id_klub IN ({znacky_k})))
        ORDER BY h.datum DESC, h.cas DESC, h.cislo DESC LIMIT ? OFFSET ?
        """,
        [aktualni_obdobi(conn), *poslanci, *kluby, limit, offset],
    )]
    if not id_hlasovani:
        return []
    znacky_h = ",".join("?" * len(id_hlasovani))
    hlasovani = {r["id_hlasovani"]: r for r in conn.execute(
        f"SELECT * FROM ({HLASOVANI_S_BODEM}) WHERE id_hlasovani IN ({znacky_h})", id_hlasovani)}
    polozky_proudu = {i: {"h": hlasovani[i], "poslanci": [], "kluby": []} for i in id_hlasovani}
    for r in conn.execute(
        f"""
        SELECT hk.id_hlasovani, hk.id_poslanec, hk.vysledek, o.jmeno, o.prijmeni,
               org.zkratka AS klub, kh.vetsina
        FROM hlas_klub hk
        JOIN poslanec p ON p.id_poslanec = hk.id_poslanec JOIN osoba o ON o.id_osoba = p.id_osoba
        LEFT JOIN organ org ON org.id_organ = hk.id_klub
        LEFT JOIN klub_hlasovani kh ON kh.id_hlasovani = hk.id_hlasovani AND kh.id_klub = hk.id_klub
        WHERE hk.id_hlasovani IN ({znacky_h}) AND hk.id_poslanec IN ({znacky_p})
        ORDER BY o.prijmeni
        """,
        [*id_hlasovani, *poslanci],
    ):
        h = hlasovani[r["id_hlasovani"]]
        polozky_proudu[r["id_hlasovani"]]["poslanci"].append({
            "id_poslanec": r["id_poslanec"], "jmeno": f"{r['jmeno']} {r['prijmeni']}",
            "hlas": r["vysledek"], "klub": r["klub"],
            "proti_klubu": r["vysledek"] in ("A", "B") and r["vetsina"] not in (None, r["vysledek"]),
            "chybel_u_celku": r["vysledek"] in ("@", "M") and h["predmet_druh"] == "celek",
        })
    for r in conn.execute(
        f"""SELECT kh.id_hlasovani, org.zkratka, kh.vetsina, kh.ano, kh.ne FROM klub_hlasovani kh
        JOIN organ org ON org.id_organ = kh.id_klub
        WHERE kh.id_hlasovani IN ({znacky_h}) AND kh.id_klub IN ({znacky_k})
        ORDER BY org.zkratka""",
        [*id_hlasovani, *kluby],
    ):
        polozky_proudu[r["id_hlasovani"]]["kluby"].append(dict(r))
    return [polozky_proudu[i] for i in id_hlasovani]
