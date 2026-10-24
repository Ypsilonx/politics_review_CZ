"""Routy: zobrazení stažených dokumentů (PDF tisků, DOCX pozměňovacích návrhů jako HTML).

Soubor se vždy hledá podle id záznamu v tabulce ``dokument`` – cesta nikdy nepochází z URL.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from politika import config
from politika.dokumenty.prevod import docx_na_html
from politika.web.app import get_db, templates

router = APIRouter()


def _dokument(conn: sqlite3.Connection, id_dokument: int) -> sqlite3.Row:
    """Vrátí záznam dokumentu (PDF nebo DOCX), jinak 404."""
    radek = conn.execute(
        "SELECT rowid AS id, * FROM dokument WHERE rowid = ? AND typ IN ('tisk_pdf', 'sd_docx')",
        (id_dokument,),
    ).fetchone()
    if radek is None or not (config.DATA_DIR / radek["cesta"]).is_file():
        raise HTTPException(404, "Dokument nenalezen")
    return radek


@router.get("/dokumenty/{id_dokument}/soubor")
def soubor(id_dokument: int, conn: sqlite3.Connection = Depends(get_db)) -> FileResponse:
    """Originál souboru – PDF se otevře přímo v prohlížeči, DOCX se stáhne."""
    d = _dokument(conn, id_dokument)
    cesta = config.DATA_DIR / d["cesta"]
    inline = cesta.suffix.lower() == ".pdf"
    return FileResponse(cesta, filename=cesta.name,
                        content_disposition_type="inline" if inline else "attachment")


@router.get("/dokumenty/{id_dokument}", response_class=HTMLResponse)
def zobrazit(request: Request, id_dokument: int, conn: sqlite3.Connection = Depends(get_db)):
    """Stránka dokumentu: PDF ve vloženém prohlížeči, DOCX převedený na HTML."""
    d = _dokument(conn, id_dokument)
    cesta = config.DATA_DIR / d["cesta"]
    obsah_html = None
    if cesta.suffix.lower() == ".docx":
        obsah_html = docx_na_html(cesta).read_text(encoding="utf-8")
    autor = conn.execute("SELECT jmeno || ' ' || prijmeni FROM osoba WHERE id_osoba = ?",
                         (d["id_osoba"],)).fetchone() if d["id_osoba"] else None
    if d["cislo_sd"]:
        nadpis = f"Pozměňovací návrh SD {d['cislo_sd']}" + (f", {autor[0]}" if autor else "")
    else:
        nadpis = f"Sněmovní tisk {d['ct']}/{d['ct1']}"
    return templates.TemplateResponse(request, "dokument.html", {
        "d": d, "nadpis": nadpis, "pdf": cesta.suffix.lower() == ".pdf", "obsah_html": obsah_html,
        "psp_url": f"https://www.psp.cz{d['url']}" if d["url"].startswith("/") else d["url"],
    })
