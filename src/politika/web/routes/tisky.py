"""Routy: sněmovní tisky (sekce Zákony) – seznam s filtry a detail tisku."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from politika.db.dotazy import tisky as dotazy
from politika.web.app import get_db, templates

router = APIRouter()


@router.get("/zakony", response_class=HTMLResponse)
def seznam(request: Request, q: str = "", druh: int | None = None, hlasovane: bool = False,
           conn: sqlite3.Connection = Depends(get_db)):
    """Seznam tisků od poslední události. Požadavek z HTMX dostane jen fragment se seznamem."""
    tisky = dotazy.seznam_tisku(conn, q, druh, hlasovane)
    sablona = "_zakony_seznam.html" if request.headers.get("HX-Request") else "zakony.html"
    return templates.TemplateResponse(request, sablona, {
        "tisky": tisky, "q": q, "druh": druh, "hlasovane": hlasovane,
        "druhy": dotazy.druhy_tisku(conn),
    })


@router.get("/zakony/{ct}", response_class=HTMLResponse)
def detail(request: Request, ct: int, conn: sqlite3.Connection = Depends(get_db)):
    """Detail tisku: stav, předkladatelé, průběh, znění, pozměňovací návrhy a hlasování."""
    tisk = dotazy.tisk_detail(conn, ct)
    if tisk is None:
        raise HTTPException(404, "Tisk nenalezen")
    return templates.TemplateResponse(request, "zakon.html", {
        "t": tisk,
        "predkladatele": dotazy.predkladatele(conn, tisk["id_tisk"]),
        "historie": dotazy.historie_tisku(conn, tisk["id_tisk"]),
        "sbirka": dotazy.sbirka_tisku(conn, tisk["id_tisk"]),
        "dokumenty": dotazy.dokumenty_tisku(conn, ct),
        "navrhy": dotazy.pozmenovaci_navrhy(conn, ct),
        "hlasovani": dotazy.hlasovani_tisku(conn, tisk["id_tisk"]),
        "psp_url": f"https://www.psp.cz/sqw/historie.sqw?T={ct}&O=10",
    })
