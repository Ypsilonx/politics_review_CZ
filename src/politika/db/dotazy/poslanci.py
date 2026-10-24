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
        SELECT p.id_poslanec, p.id_osoba, p.id_obdobi, p.id_kraj, p.email, o.titul_pred, o.jmeno,
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


def kraj(conn: sqlite3.Connection, id_kraj: int | None) -> str | None:
    """Vrátí název volebního kraje poslance v běžném tvaru („Zlínský kraj“, „Kraj Vysočina“).

    PSP eviduje kraje přídavným jménem („Zlínský“), Prahu a Vysočinu jinak.
    """
    if id_kraj is None:
        return None
    radek = conn.execute("SELECT nazev FROM organ WHERE id_organ = ?", (id_kraj,)).fetchone()
    if radek is None:
        return None
    nazev = radek[0]
    if nazev == "Vysočina":
        return "Kraj Vysočina"
    return nazev if "Praha" in nazev or "kraj" in nazev.lower() else f"{nazev} kraj"


def clenstvi(conn: sqlite3.Connection, id_osoba: int) -> list[dict]:
    """Vrátí aktuální členství v orgánech sněmovny (výbory, komise, delegace) i s funkcí.

    Klub a samotná sněmovna se vynechávají (jsou v hlavičce profilu).
    :return: ``[{nazev, typ, funkce}, …]`` seřazené podle typu orgánu a názvu
    """
    obdobi = aktualni_obdobi(conn)
    funkce = {r["id_organ"]: r["nazev"] for r in conn.execute(
        """SELECT f.id_organ, f.nazev FROM zarazeni_funkce zf JOIN funkce f ON f.id_funkce = zf.id_funkce
        WHERE zf.id_osoba = ? AND (zf.do IS NULL OR zf.do >= date('now'))""",
        (id_osoba,),
    )}
    radky = conn.execute(
        """
        SELECT o.id_organ, o.nazev, t.nazev AS typ FROM zarazeni z
        JOIN organ o ON o.id_organ = z.id_organ
        LEFT JOIN typ_organu t ON t.id_typ = o.id_typ
        WHERE z.id_osoba = ? AND (z.do IS NULL OR z.do >= date('now'))
          AND o.id_nadrazeny = ? AND o.id_typ != 1
        ORDER BY t.nazev, o.nazev
        """,
        (id_osoba, obdobi),
    ).fetchall()
    return [{"nazev": r["nazev"], "typ": r["typ"], "funkce": funkce.get(r["id_organ"])}
            for r in radky]


def navrhy_zakonu(conn: sqlite3.Connection, id_osoba: int) -> list[sqlite3.Row]:
    """Vrátí tisky aktuálního období, které osoba předložila nebo spolupředložila."""
    return conn.execute(
        """
        SELECT t.ct, t.nazev, t.predlozeno, ts.popis AS stav FROM predkladatel p
        JOIN tisk t ON t.id_tisk = p.id_tisk
        LEFT JOIN stav_tisku st ON st.id_stav = t.id_stav
        LEFT JOIN typ_stavu ts ON ts.id_typ = st.id_typ
        WHERE p.id_osoba = ? AND t.id_obdobi = ?
        ORDER BY t.predlozeno DESC
        """,
        (id_osoba, aktualni_obdobi(conn)),
    ).fetchall()


def pozmenovaci_navrhy(conn: sqlite3.Connection, id_osoba: int) -> list[sqlite3.Row]:
    """Vrátí písemné pozměňovací návrhy osoby v aktuálním období (s tiskem a odkazem na soubor, je-li znám)."""
    obdobi = aktualni_obdobi(conn)
    return conn.execute(
        """
        SELECT sd.cislo, sd.ct, sd.datum, t.nazev AS tisk_nazev, d.url AS url_souboru, d.popis
        FROM sd
        LEFT JOIN tisk t ON t.ct = sd.ct AND t.id_obdobi = sd.id_organ
        LEFT JOIN dokument d ON d.typ = 'sd_docx' AND d.cislo_sd = sd.cislo AND d.ct = sd.ct
        WHERE sd.id_osoba = ? AND sd.id_organ = ? AND sd.typ = 13
        ORDER BY sd.datum DESC
        """,
        (id_osoba, obdobi),
    ).fetchall()
