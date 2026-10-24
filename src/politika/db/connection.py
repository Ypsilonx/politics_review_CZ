"""Připojení k SQLite a inicializace schématu."""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# Zvýšit při změně sloupců tabulek z otevřených dat. Při nesouladu se tyto tabulky
# zahodí a vytvoří znovu (data doplní příští `politika import`); tabulky aplikace
# (dokumenty, předměty hlasování, sledovaní) zůstanou.
SCHEMA_VERZE = 3
TABULKY_OPENDATA = [
    "osoba", "poslanec", "organ", "zarazeni", "schuze", "bod", "tisk", "hlasovani", "hlas",
    "druh_tisku", "stav_tisku", "typ_stavu", "hist_tisku", "prechod", "typ_akce", "predkladatel",
    "sbirka", "sd", "steno", "vystoupeni", "omluva", "funkce", "typ_funkce", "zarazeni_funkce",
    "typ_organu", "hlas_klub", "klub_hlasovani",
]


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Otevře databázi (vytvoří ji i se složkou, pokud chybí) a zajistí aktuální schéma.

    Řádky vrací jako ``sqlite3.Row`` (přístup podle názvu sloupce).
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # FastAPI volá otevření, endpoint i zavření závislosti v různých vláknech threadpoolu;
    # spojení přitom patří vždy jen jednomu požadavku, takže sdílení mezi vlákny nehrozí.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERZE:
        with conn:
            for tabulka in TABULKY_OPENDATA:
                conn.execute(f"DROP TABLE IF EXISTS {tabulka}")
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERZE}")
    _povol_odkazy_bez_souboru(conn)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def _povol_odkazy_bez_souboru(conn: sqlite3.Connection) -> None:
    """Migrace tabulky aplikace ``dokument``: sloupec ``cesta`` smí být NULL (odkaz bez souboru).

    SQLite neumí změnit omezení sloupce, proto se tabulka přejmenuje, vytvoří znovu podle
    schématu a data se přelijí. Tabulka ``dokument`` se při změně verze schématu nemaže.
    """
    sloupce = {r["name"]: r["notnull"] for r in conn.execute("PRAGMA table_info(dokument)")}
    if not sloupce.get("cesta"):
        return  # tabulka ještě není, nebo už je převedená
    with conn:
        conn.execute("ALTER TABLE dokument RENAME TO dokument_stara")
        conn.execute("DROP INDEX IF EXISTS ix_dokument_schuze")
        conn.execute("DROP INDEX IF EXISTS ix_dokument_tisk")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    with conn:
        conn.execute(f"INSERT INTO dokument ({', '.join(sloupce)}) "
                     f"SELECT {', '.join(sloupce)} FROM dokument_stara")
        conn.execute("DROP TABLE dokument_stara")
