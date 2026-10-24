"""Routy: sledovaní poslanci a kluby (správa skupin) a Přehled s proudem jejich hlasování."""

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from politika.db.dotazy import schuze as dotazy_schuze
from politika.db.dotazy import sledovani as dotazy
from politika.db.dotazy.hlasovani import seznam_hlasovani
from politika.db.dotazy.poslanci import hledej_poslance
from politika.web.app import get_db, templates, z_teto_aplikace

router = APIRouter()

# Počet hlasování v proudu na jednu stránku.
DELKA_PROUDU = 25


@router.get("/prehled", response_class=HTMLResponse)
def prehled(request: Request, strana: int = 1, conn: sqlite3.Connection = Depends(get_db)):
    """Úvodní přehled: proud hlasování sledovaných, poslední schůze a nejnovější závěrečná hlasování."""
    strana = max(strana, 1)
    proud = dotazy.proud(conn, None, DELKA_PROUDU + 1, (strana - 1) * DELKA_PROUDU)
    schuze = dotazy_schuze.seznam_schuzi(conn)
    return templates.TemplateResponse(request, "prehled.html", {
        "proud": proud[:DELKA_PROUDU],
        "dalsi": len(proud) > DELKA_PROUDU,
        "strana": strana,
        "sledovanych": len(dotazy.polozky(conn)),
        "posledni_schuze": next((s for s in schuze if s["hlasovani"]), None),
        "zaverecna": seznam_hlasovani(conn, druh="celek", limit=6),
        "posledni_data": conn.execute("SELECT MAX(datum) FROM hlasovani").fetchone()[0],
    })


@router.get("/sledovani", response_class=HTMLResponse)
def sledovani(request: Request, skupina: str = "", q: str = "", strana: int = 1,
              conn: sqlite3.Connection = Depends(get_db)):
    """Správa sledovaných (skupiny, přidání poslance / klubu) a proud hlasování vybrané skupiny."""
    strana = max(strana, 1)
    proud = dotazy.proud(conn, skupina or None, DELKA_PROUDU + 1, (strana - 1) * DELKA_PROUDU)
    return templates.TemplateResponse(request, "sledovani.html", {
        "skupiny": dotazy.skupiny(conn),
        "skupina": skupina,
        "polozky": dotazy.polozky(conn),
        "kluby": dotazy.kluby_obdobi(conn),
        "q": q,
        "nalezeni": hledej_poslance(conn, q)[:12] if q.strip() else [],
        "proud": proud[:DELKA_PROUDU],
        "dalsi": len(proud) > DELKA_PROUDU,
        "strana": strana,
    })


@router.post("/sledovani/pridat")
def pridat(request: Request, typ: str = Form(...), id: int = Form(...),
           skupina: str = Form(dotazy.VYCHOZI_SKUPINA), zpet: str = Form("/sledovani"),
           conn: sqlite3.Connection = Depends(get_db)):
    """Přidá poslance / klub do skupiny. HTMX dostane nové tlačítko, jinak přesměrování zpět."""
    z_teto_aplikace(request)
    if typ in ("poslanec", "klub"):
        dotazy.pridej(conn, typ, id, skupina)
    return _odpoved(request, typ, id, zpet, conn)


@router.post("/sledovani/odebrat")
def odebrat(request: Request, typ: str = Form(...), id: int = Form(...),
            skupina: str = Form(""), zpet: str = Form("/sledovani"),
            conn: sqlite3.Connection = Depends(get_db)):
    """Odebere poslance / klub ze skupiny (bez skupiny ze všech)."""
    z_teto_aplikace(request)
    dotazy.odeber(conn, typ, id, skupina or None)
    return _odpoved(request, typ, id, zpet, conn)


def _odpoved(request: Request, typ: str, id_: int, zpet: str, conn: sqlite3.Connection):
    """Po změně: HTMX dostane aktualizované tlačítko „Sledovat“, běžný formulář přesměrování."""
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "_tlacitko_sledovat.html", {
            "typ": typ, "id": id_, "sledovany": dotazy.je_sledovany(conn, typ, id_), "zpet": zpet})
    # Návrat jen na vlastní stránky aplikace (relativní cesta), nikdy jinam.
    return RedirectResponse(zpet if zpet.startswith("/") and not zpet.startswith("//")
                            else "/sledovani", status_code=303)
