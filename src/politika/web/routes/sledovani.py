"""Routy: sledovaní poslanci a kluby (správa skupin, rozbalovací hlasování) a Přehled s proudem."""

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from politika.db.dotazy import schuze as dotazy_schuze
from politika.db.dotazy import sledovani as dotazy
from politika.db.dotazy.hlasovani import hlasovani_poslance, seznam_hlasovani
from politika.db.dotazy.poslanci import hledej_poslance
from politika.web.app import get_db, templates, z_teto_aplikace

router = APIRouter()

# Počet hlasování v proudu na jednu stránku.
DELKA_PROUDU = 25
# Kolik hlasování ukázat po rozbalení člena a na jedno načtení srovnání skupiny.
POSLEDNICH_CLENA = 10
DELKA_SROVNANI = 10


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
def sledovani(request: Request, skupina: str = "", q: str = "",
              conn: sqlite3.Connection = Depends(get_db)):
    """Správa sledovaných (skupiny, přidání poslance / klubu); hlasování se načítají rozbalením."""
    return templates.TemplateResponse(request, "sledovani.html", {
        "skupiny": dotazy.skupiny(conn),
        "skupina": skupina,
        "polozky": dotazy.polozky(conn),
        "kluby": dotazy.kluby_obdobi(conn),
        "q": q,
        "nalezeni": hledej_poslance(conn, q)[:12] if q.strip() else [],
    })


@router.get("/sledovani/hlasy/{typ}/{id_}", response_class=HTMLResponse)
def hlasy_clena(request: Request, typ: str, id_: int, conn: sqlite3.Connection = Depends(get_db)):
    """Fragment s posledními hlasováními sledovaného poslance / klubu (rozbalení řádku)."""
    if typ == "poslanec":
        hlasovani = hlasovani_poslance(conn, id_, POSLEDNICH_CLENA)
    elif typ == "klub":
        hlasovani = dotazy.hlasovani_klubu(conn, id_, POSLEDNICH_CLENA)
    else:
        raise HTTPException(404, "Neznámý typ sledovaného")
    return templates.TemplateResponse(request, "_hlasy_clena.html", {
        "typ": typ, "id": id_, "hlasovani": hlasovani})


@router.get("/sledovani/srovnani", response_class=HTMLResponse)
def srovnani(request: Request, skupina: str, strana: int = 1,
             conn: sqlite3.Connection = Depends(get_db)):
    """Fragment se srovnáním hlasování celé skupiny (rozbalení skupiny), po stránkách."""
    strana = max(strana, 1)
    proud = dotazy.proud(conn, skupina, DELKA_SROVNANI + 1, (strana - 1) * DELKA_SROVNANI)
    return templates.TemplateResponse(request, "_srovnani.html", {
        "proud": proud[:DELKA_SROVNANI], "dalsi": len(proud) > DELKA_SROVNANI,
        "skupina": skupina, "strana": strana})


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
