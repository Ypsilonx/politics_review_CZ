"""Evidence stažených dokumentů v tabulce ``dokument``."""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from politika import config


def ted() -> str:
    """Aktuální čas v UTC jako ISO řetězec."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def zaeviduj(conn: sqlite3.Connection, url: str, typ: str, cesta: Path | None,
             **udaje: object) -> None:
    """Zapíše nebo aktualizuje záznam dokumentu (cesta se ukládá relativně k ``DATA_DIR``).

    :param cesta: stažený soubor; ``None`` = jen odkaz na psp.cz, soubor se nestahuje

    :param udaje: další sloupce tabulky ``dokument`` (schuze, poradi, ct, ct1, cislo_sd …)
    """
    hodnoty = {"url": url, "typ": typ, "cesta": cesta.relative_to(config.DATA_DIR).as_posix() if cesta else None,
               "stazeno": ted(), **udaje}
    sloupce = ", ".join(hodnoty)
    zmena = ", ".join(f"{k} = excluded.{k}" for k in hodnoty if k != "url")
    conn.execute(
        f"INSERT INTO dokument ({sloupce}) VALUES ({', '.join('?' * len(hodnoty))}) "
        f"ON CONFLICT (url) DO UPDATE SET {zmena}",
        list(hodnoty.values()),
    )


def je_starsi_nez(conn: sqlite3.Connection, url: str, stari: timedelta) -> bool:
    """Zda dokument není evidovaný, nebo byl naposledy stažen před více než ``stari``."""
    radek = conn.execute("SELECT stazeno FROM dokument WHERE url = ?", (url,)).fetchone()
    return radek is None or datetime.fromisoformat(radek[0]) < datetime.now(UTC) - stari
