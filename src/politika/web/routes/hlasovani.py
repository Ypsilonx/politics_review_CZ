"""Routy: detail jednoho hlasování."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from politika.db import dotazy
from politika.web.app import get_db, templates

router = APIRouter()


@router.get("/hlasovani/{id_hlasovani}", response_class=HTMLResponse)
def detail(request: Request, id_hlasovani: int, conn: sqlite3.Connection = Depends(get_db)):
    """Výsledek hlasování a hlasy poslanců po klubech, s odkazem na zdroj na psp.cz."""
    hlasovani = dotazy.hlasovani_detail(conn, id_hlasovani)
    if hlasovani is None:
        raise HTTPException(404, "Hlasování nenalezeno")
    return templates.TemplateResponse(request, "hlasovani.html", {
        "h": hlasovani,
        "kluby": dotazy.hlasy_po_klubech(conn, id_hlasovani),
        "psp_url": f"https://www.psp.cz/sqw/hlasy.sqw?g={id_hlasovani}&l=cz",
    })
