"""Routy: globální hledání (poslanci, tisky, hlasování podle čísla „34/288“)."""

import re
import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from politika.db.dotazy.poslanci import hledej_poslance
from politika.db.dotazy.spolecne import aktualni_obdobi
from politika.db.dotazy.tisky import seznam_tisku
from politika.dokumenty.foto import cesta_fotky
from politika.web.app import get_db, templates

router = APIRouter()

# „34/288“, „34 288“ nebo „schůze 34 hlasování 288“ → hlasování 288 na 34. schůzi.
_HLASOVANI = re.compile(r"^\D*(\d{1,3})\D+(\d{1,4})\D*$")
MAX_VYSLEDKU = 20


@router.get("/hledat", response_class=HTMLResponse)
def hledat(request: Request, q: str = "", conn: sqlite3.Connection = Depends(get_db)):
    """Najde poslance, tisky a hlasování; jediný jednoznačný výsledek rovnou otevře."""
    q = q.strip()
    if m := _HLASOVANI.match(q):
        hlasovani = conn.execute(
            "SELECT id_hlasovani FROM hlasovani WHERE id_organ = ? AND schuze = ? AND cislo = ?",
            (aktualni_obdobi(conn), int(m.group(1)), int(m.group(2))),
        ).fetchone()
        if hlasovani:
            return RedirectResponse(f"/hlasovani/{hlasovani[0]}", status_code=303)
    poslanci = [{**p, "foto": cesta_fotky(p["id_osoba"]).exists()}
                for p in hledej_poslance(conn, q)[:MAX_VYSLEDKU]] if q else []
    tisky = seznam_tisku(conn, q)[:MAX_VYSLEDKU] if q else []
    if len(poslanci) == 1 and not tisky:
        return RedirectResponse(f"/poslanec/{poslanci[0]['id_poslanec']}", status_code=303)
    if len(tisky) == 1 and not poslanci and q.isdigit():
        return RedirectResponse(f"/zakony/{tisky[0]['ct']}", status_code=303)
    return templates.TemplateResponse(request, "hledani.html",
                                      {"q": q, "poslanci": poslanci, "tisky": tisky})
