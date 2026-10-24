"""Routy: schůze – seznam a pořad schůze s hlasováními po bodech."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from politika.db.dotazy import schuze as dotazy
from politika.web.app import get_db, templates

router = APIRouter()


@router.get("/schuze", response_class=HTMLResponse)
def seznam(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    """Seznam schůzí aktuálního období od nejnovější."""
    return templates.TemplateResponse(request, "schuze_seznam.html",
                                      {"schuze": dotazy.seznam_schuzi(conn)})


@router.get("/schuze/{cislo}", response_class=HTMLResponse)
def detail(request: Request, cislo: int, conn: sqlite3.Connection = Depends(get_db)):
    """Pořad schůze: body (s tiskem) a jejich hlasování."""
    schuze = dotazy.schuze_detail(conn, cislo)
    if schuze is None:
        raise HTTPException(404, "Schůze nenalezena")
    return templates.TemplateResponse(request, "schuze.html", {
        "s": schuze, "body": dotazy.body_s_hlasovanim(conn, cislo),
        "psp_url": f"https://www.psp.cz/sqw/ischuze.sqw?o=10&s={cislo}",
    })
