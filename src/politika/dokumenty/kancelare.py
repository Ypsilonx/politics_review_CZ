"""Regionální kanceláře poslanců z mapy na psp.cz (``/sqw/pk.sqw``).

Stránka má souřadnice přímo ve skriptu jako pole záznamů
``['Jméno', lat, lng, 'adresa<br>obec<br>PSČ', …, '<a href=…detail.sqw?id=…>…</a> (klub)', id_osoba]``
uložená v proměnných ``var addressPoints… = [ … ];``. Načítá se celá jedna stránka, ne po poslancích.
"""

import re
import sqlite3
from dataclasses import dataclass
from datetime import timedelta

from politika import config
from politika.dokumenty.evidence import je_starsi_nez, zaeviduj
from politika.dokumenty.stahovani import Stahovac, precti_html

URL_MAPY = "/sqw/pk.sqw"
OBNOVA = timedelta(days=7)

_PROMENNA = re.compile(r"var\s+(addressPoints\w*)\s*=\s*\[(.*?)\];", re.DOTALL)
_ZAZNAM = re.compile(
    r"\[\s*'(?P<jmeno>[^']*)'\s*,\s*(?P<lat>-?[\d.]+)\s*,\s*(?P<lng>-?[\d.]+)\s*,\s*"
    r"'(?P<adresa>[^']*)'.*?,\s*(?P<id_osoba>\d+)\s*\]", re.DOTALL)


@dataclass(frozen=True)
class Kancelar:
    """Regionální kancelář: osoba, souřadnice, adresa (řádky oddělené čárkou) a skupina z mapy."""

    id_osoba: int
    lat: float
    lng: float
    adresa: str
    skupina: str


def kancelare_z_mapy(html: str) -> list[Kancelar]:
    """Vytáhne kanceláře ze skriptu stránky mapy (všechna pole ``addressPoints…``)."""
    vysledek = []
    for promenna in _PROMENNA.finditer(html):
        for z in _ZAZNAM.finditer(promenna.group(2)):
            adresa = ", ".join(c.strip() for c in re.split(r"<br\s*/?>", z["adresa"]) if c.strip())
            vysledek.append(Kancelar(int(z["id_osoba"]), float(z["lat"]), float(z["lng"]),
                                     adresa, promenna.group(1)))
    return vysledek


def obnov_kancelare(conn: sqlite3.Connection, st: Stahovac, vynutit: bool = False) -> int:
    """Stáhne mapu kanceláří (nejvýš jednou za ``OBNOVA``) a uloží ji do tabulky ``kancelar``.

    :return: počet uložených kanceláří
    """
    cesta = config.DATA_DIR / "dokumenty" / "kancelare.html"
    obnovit = vynutit or je_starsi_nez(conn, URL_MAPY, OBNOVA)
    st.stahni(URL_MAPY, cesta, prepsat=obnovit)
    if obnovit:
        zaeviduj(conn, URL_MAPY, "kancelare", cesta)
    kancelare = kancelare_z_mapy(precti_html(cesta))
    with conn:
        conn.execute("DELETE FROM kancelar")
        conn.executemany("INSERT INTO kancelar VALUES (?, ?, ?, ?, ?)",
                         [(k.id_osoba, k.lat, k.lng, k.adresa, k.skupina) for k in kancelare])
    return len(kancelare)
