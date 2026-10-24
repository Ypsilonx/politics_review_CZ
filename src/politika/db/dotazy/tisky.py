"""Dotazy: sněmovní tisky (zákony) – seznam, detail, historie, dokumenty, hlasování."""

import sqlite3

from politika import config
from politika.db.dotazy.hlasovani import HLASOVANI_S_BODEM
from politika.db.dotazy.spolecne import aktualni_obdobi, bez_diakritiky
from politika.dokumenty.stahovani import precti_html
from politika.parovani.navrhy import verze_s_navrhy

# Tisk se stavem a datem poslední události v legislativním procesu.
_TISK = """
    SELECT t.*, d.nazev AS druh, ts.popis AS stav,
           (SELECT MAX(datum) FROM hist_tisku h WHERE h.id_tisk = t.id_tisk) AS posledni_udalost,
           (SELECT COUNT(*) FROM bod b
              JOIN schuze s ON s.id_schuze = b.id_schuze
              JOIN hlasovani hl ON hl.id_organ = s.id_organ AND hl.schuze = s.cislo AND hl.bod = b.cislo
            WHERE b.id_tisk = t.id_tisk) AS pocet_hlasovani
    FROM tisk t
    LEFT JOIN druh_tisku d ON d.id_druh = t.id_druh
    LEFT JOIN stav_tisku st ON st.id_stav = t.id_stav
    LEFT JOIN typ_stavu ts ON ts.id_typ = st.id_typ
"""


def druhy_tisku(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Vrátí druhy tisků, které se v aktuálním období vyskytují (pro filtr), s počty."""
    return conn.execute(
        "SELECT d.id_druh, d.nazev, COUNT(*) AS pocet FROM tisk t JOIN druh_tisku d USING (id_druh) "
        "WHERE t.id_obdobi = ? GROUP BY d.id_druh ORDER BY pocet DESC",
        (aktualni_obdobi(conn),),
    ).fetchall()


def seznam_tisku(conn: sqlite3.Connection, text: str = "", id_druh: int | None = None,
                 jen_hlasovane: bool = False) -> list[sqlite3.Row]:
    """Vrátí tisky aktuálního období od poslední události, s volitelným filtrem.

    :param text: číslo tisku nebo část názvu (bez ohledu na diakritiku)
    :param id_druh: jen tisky daného druhu
    :param jen_hlasovane: jen tisky, o kterých se ve sněmovně hlasovalo
    """
    radky = conn.execute(
        f"SELECT * FROM ({_TISK}) WHERE id_obdobi = ? AND (? IS NULL OR id_druh = ?) "
        "ORDER BY posledni_udalost DESC, ct DESC",
        (aktualni_obdobi(conn), id_druh, id_druh),
    ).fetchall()
    hledany = bez_diakritiky(text.strip())
    if hledany.isdigit():
        radky = [r for r in radky if str(r["ct"]) == hledany]
    elif hledany:
        radky = [r for r in radky
                 if hledany in bez_diakritiky(f"{r['nazev'] or ''} {r['uplny_nazev'] or ''}")]
    if jen_hlasovane:
        radky = [r for r in radky if r["pocet_hlasovani"]]
    return radky


def tisk_detail(conn: sqlite3.Connection, ct: int) -> sqlite3.Row | None:
    """Vrátí tisk aktuálního období podle čísla, nebo ``None``."""
    return conn.execute(f"SELECT * FROM ({_TISK}) WHERE id_obdobi = ? AND ct = ?",
                        (aktualni_obdobi(conn), ct)).fetchone()


def historie_tisku(conn: sqlite3.Connection, id_tisk: int) -> list[sqlite3.Row]:
    """Vrátí události legislativního procesu tisku od nejstarší (popis akce, nový stav, hlasování)."""
    return conn.execute(
        """
        SELECT h.datum, h.schuze, h.id_hlas, ta.popis AS akce, ts.popis AS stav
        FROM hist_tisku h
        LEFT JOIN prechod p ON p.id_prechod = h.id_prechod
        LEFT JOIN typ_akce ta ON ta.id_akce = p.id_akce
        LEFT JOIN stav_tisku st ON st.id_stav = p.kam
        LEFT JOIN typ_stavu ts ON ts.id_typ = st.id_typ
        WHERE h.id_tisk = ?
        ORDER BY h.datum, h.id_hist
        """,
        (id_tisk,),
    ).fetchall()


def predkladatele(conn: sqlite3.Connection, id_tisk: int) -> list[sqlite3.Row]:
    """Vrátí předkladatele tisku – osoby, u poslanců i s ``id_poslanec`` (pro odkaz na profil)."""
    return conn.execute(
        """
        SELECT o.id_osoba, o.jmeno, o.prijmeni,
               (SELECT p.id_poslanec FROM poslanec p
                 WHERE p.id_osoba = o.id_osoba AND p.id_obdobi = ?) AS id_poslanec
        FROM predkladatel pr JOIN osoba o ON o.id_osoba = pr.id_osoba
        WHERE pr.id_tisk = ? ORDER BY pr.poradi
        """,
        (aktualni_obdobi(conn), id_tisk),
    ).fetchall()


def sbirka_tisku(conn: sqlite3.Connection, id_tisk: int) -> sqlite3.Row | None:
    """Vrátí předpis ve Sbírce zákonů, který z tisku vznikl, nebo ``None``."""
    return conn.execute(
        "SELECT cislo, rok, datum FROM sbirka WHERE id_tisk = ? ORDER BY rok DESC LIMIT 1",
        (id_tisk,),
    ).fetchone()


def dokumenty_tisku(conn: sqlite3.Connection, ct: int) -> list[dict]:
    """Vrátí stažená PDF verzí tisku s popisem, seřazená podle verze.

    Popis: 213/0 = původní návrh, verze se souhrnem pozměňovacích návrhů podle historie tisku,
    ostatní „Tisk 213/n“; soubory s písmenem za číslem tisku (t0213a0.pdf) jsou přílohy.
    """
    historie = conn.execute(
        "SELECT cesta FROM dokument WHERE typ = 'tisk_historie' AND ct = ?", (ct,)).fetchone()
    ct1_navrhu = (verze_s_navrhy(precti_html(config.DATA_DIR / historie[0]), ct)
                  if historie else None)
    vysledek = []
    for r in conn.execute(
        "SELECT rowid AS id, ct1, nazev FROM dokument WHERE typ = 'tisk_pdf' AND ct = ? "
        "ORDER BY ct1, nazev",
        (ct,),
    ):
        priloha = r["nazev"][len(f"t{ct:04d}"):][:1].isalpha()
        if r["ct1"] == 0:
            popis = "Původní návrh"
        elif r["ct1"] == ct1_navrhu:
            popis = "Souhrn pozměňovacích návrhů"
        else:
            popis = f"Tisk {ct}/{r['ct1']}"
        vysledek.append({"id": r["id"], "ct1": r["ct1"], "nazev": r["nazev"],
                         "popis": f"{popis} – příloha" if priloha else popis})
    return vysledek


def pozmenovaci_navrhy(conn: sqlite3.Connection, ct: int) -> list[sqlite3.Row]:
    """Vrátí písemné pozměňovací návrhy k tisku (z otevřených dat) a stažený soubor, je-li.

    Autor se páruje na poslance aktuálního období kvůli odkazu na profil.
    """
    obdobi = aktualni_obdobi(conn)
    return conn.execute(
        """
        SELECT sd.cislo, sd.datum, sd.id_osoba, o.jmeno, o.prijmeni,
               (SELECT p.id_poslanec FROM poslanec p
                 WHERE p.id_osoba = sd.id_osoba AND p.id_obdobi = :obdobi) AS id_poslanec,
               d.rowid AS id_souboru, d.popis
        FROM sd
        LEFT JOIN osoba o ON o.id_osoba = sd.id_osoba
        LEFT JOIN dokument d ON d.typ = 'sd_docx' AND d.cislo_sd = sd.cislo AND d.ct = sd.ct
        WHERE sd.id_organ = :obdobi AND sd.typ = 13 AND sd.ct = :ct
        ORDER BY sd.datum
        """,
        {"obdobi": obdobi, "ct": ct},
    ).fetchall()


def hlasovani_tisku(conn: sqlite3.Connection, id_tisk: int) -> list[sqlite3.Row]:
    """Vrátí všechna hlasování k bodům schůzí, které projednávaly tisk, od nejnovějšího."""
    return conn.execute(
        f"""
        SELECT x.* FROM ({HLASOVANI_S_BODEM}) x
        WHERE x.id_hlasovani IN (
            SELECT h.id_hlasovani FROM bod b
            JOIN schuze s ON s.id_schuze = b.id_schuze
            JOIN hlasovani h ON h.id_organ = s.id_organ AND h.schuze = s.cislo AND h.bod = b.cislo
            WHERE b.id_tisk = ?)
        ORDER BY x.datum DESC, x.cas DESC, x.cislo DESC
        """,
        (id_tisk,),
    ).fetchall()
