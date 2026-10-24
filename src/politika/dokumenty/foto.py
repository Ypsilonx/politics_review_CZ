"""Fotky poslanců z psp.cz – stahují se jednou do ``data/foto/{id_osoba}.jpg``."""

import sqlite3
from pathlib import Path

import httpx

from politika import config
from politika.db.dotazy.poslanci import hledej_poslance
from politika.dokumenty.stahovani import Stahovac

SLOZKA = config.DATA_DIR / "foto"


def url_fotky(id_osoba: int) -> str:
    """URL fotky poslance aktuálního období na psp.cz (podle ``id_osoba``)."""
    return f"/eknih/cdrom/{config.OBDOBI}/eknih/{config.OBDOBI}/poslanci/i{id_osoba}.jpg"


def cesta_fotky(id_osoba: int) -> Path:
    """Místní cesta k fotce (soubor nemusí existovat)."""
    return SLOZKA / f"{id_osoba}.jpg"


def stahni_fotky(conn: sqlite3.Connection, st: Stahovac) -> int:
    """Stáhne chybějící fotky poslanců s trvajícím mandátem; chybějící fotku (404) přeskočí.

    :return: počet nově stažených fotek
    """
    nove = 0
    for p in hledej_poslance(conn):
        cil = cesta_fotky(p["id_osoba"])
        if cil.exists():
            continue
        try:
            st.stahni(url_fotky(p["id_osoba"]), cil)
        except httpx.HTTPStatusError as chyba:
            if chyba.response.status_code != 404:
                raise
            continue
        nove += 1
    return nove
