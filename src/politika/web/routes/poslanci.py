"""Routy: vyhledání poslance a jeho profil s historií hlasování."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from politika.db import dotazy
from politika.web.app import get_db, templates

router = APIRouter()

NA_STRANKU = 50


@router.get("/poslanci", response_class=HTMLResponse)
def seznam(request: Request, q: str = "", conn: sqlite3.Connection = Depends(get_db)):
    """Seznam poslanců s vyhledáváním. Požadavek z HTMX dostane jen fragment se seznamem."""
    poslanci = dotazy.hledej_poslance(conn, q)
    sablona = "_poslanci_seznam.html" if request.headers.get("HX-Request") else "poslanci.html"
    return templates.TemplateResponse(request, sablona, {"poslanci": poslanci, "q": q})


@router.get("/poslanec/{id_poslanec}", response_class=HTMLResponse)
def profil(request: Request, id_poslanec: int, strana: int = 1,
           conn: sqlite3.Connection = Depends(get_db)):
    """Profil poslance a jeho hlasování od nejnovějšího, po stránkách."""
    poslanec = dotazy.poslanec_detail(conn, id_poslanec)
    if poslanec is None:
        raise HTTPException(404, "Poslanec nenalezen")
    strana = max(strana, 1)
    hlasovani = dotazy.hlasovani_poslance(conn, id_poslanec, NA_STRANKU + 1,
                                          (strana - 1) * NA_STRANKU)
    return templates.TemplateResponse(request, "poslanec.html", {
        "poslanec": poslanec,
        "hlasovani": hlasovani[:NA_STRANKU],
        "strana": strana,
        "dalsi": len(hlasovani) > NA_STRANKU,
    })
