"""Vazba hlasování o pozměňovacím návrhu na tisk se souhrnem pozměňovacích návrhů.

Po druhém čtení PSP zpracuje podané návrhy do jedné verze tisku („Podané pozměňovací návrhy
zpracovány jako tisk 213/3“). V ní jsou návrhy označené písmeny (A1, B2 …), na která se
předsedající při hlasování ve třetím čtení odkazuje.
"""

import re
import sqlite3

from politika import config
from politika.dokumenty.stahovani import precti_html

def verze_s_navrhy(historie_html: str, ct: int) -> int | None:
    """Najde ve stránce historie číslo verze tisku se zpracovanými pozměňovacími návrhy.

    Bere poslední zmínku („Podané <B>pozměňovací návrhy</B> zpracovány jako tisk 213/3“),
    protože opravený tisk se rozesílá znovu pod vyšším číslem.
    """
    vzor = re.compile(
        rf"pozměňovací\s+návrhy\s*</b>\s*zpracovány\s+jako\s+tisk\s*<b>\s*"
        rf"<a[^>]*ct={ct}&(?:amp;)?ct1=(\d+)", re.IGNORECASE)
    nalezy = vzor.findall(historie_html)
    return int(nalezy[-1]) if nalezy else None


def dokument_navrhu(conn: sqlite3.Connection, ct: int) -> str | None:
    """Vrátí URL PDF verze tisku se souhrnem pozměňovacích návrhů, je-li v evidenci."""
    historie = conn.execute(
        "SELECT cesta FROM dokument WHERE typ = 'tisk_historie' AND ct = ?", (ct,)
    ).fetchone()
    if historie is None:
        return None
    ct1 = verze_s_navrhy(precti_html(config.DATA_DIR / historie[0]), ct)
    if ct1 is None:
        return None
    pdf = conn.execute(
        "SELECT url FROM dokument WHERE typ = 'tisk_pdf' AND ct = ? AND ct1 = ? ORDER BY nazev LIMIT 1",
        (ct, ct1),
    ).fetchone()
    return pdf[0] if pdf else None
