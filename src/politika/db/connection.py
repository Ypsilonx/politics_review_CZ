"""Připojení k SQLite a inicializace schématu."""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Otevře databázi (vytvoří ji i se složkou, pokud chybí) a zajistí schéma.

    Řádky vrací jako ``sqlite3.Row`` (přístup podle názvu sloupce).
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn
