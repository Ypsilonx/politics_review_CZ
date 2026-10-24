"""Routy: seznam hlasování s filtry a detail jednoho hlasování."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from politika.db.dotazy import hlasovani as dotazy
from politika.web.app import HLAS_TEXT, get_db, templates
from politika.web.grafy import rozlozeni_sedadel

router = APIRouter()

# Pořadí hlasů uvnitř klubu v půlkruhu (podle pořadí v HLAS_TEXT: Ano, Ne, Zdržel se, …).
_PORADI_HLASU = {kod: i for i, kod in enumerate(HLAS_TEXT)}


def _sedadla(kluby: list[dotazy.Klub]) -> list[dict]:
    """Přiřadí poslance sedadlům půlkruhu: kluby jako klíny, uvnitř klubu podle hlasu."""
    poradi = [
        (k.zkratka, p)
        for k in kluby
        for p in sorted(k.poslanci, key=lambda p: _PORADI_HLASU.get(p["hlas"], 99))
    ]
    return [
        {"x": s.x, "y": s.y, "r": s.r, "klub": klub, **p}
        for s, (klub, p) in zip(rozlozeni_sedadel(len(poradi)), poradi)
    ]


NA_STRANKU = 50


@router.get("/hlasovani", response_class=HTMLResponse)
def seznam(request: Request, schuze: int | None = None, vysledek: str = "", tesna: bool = False,
           druh: str = "", strana: int = 1, conn: sqlite3.Connection = Depends(get_db)):
    """Všechna hlasování od nejnovějšího; filtry schůze, výsledek, těsná, druh předmětu."""
    strana = max(strana, 1)
    radky = dotazy.seznam_hlasovani(conn, schuze, vysledek or None, tesna, druh or None,
                                    NA_STRANKU + 1, (strana - 1) * NA_STRANKU)
    filtry = {"schuze": schuze or "", "vysledek": vysledek, "tesna": tesna, "druh": druh}
    return templates.TemplateResponse(request, "hlasovani_seznam.html", {
        "hlasovani": radky[:NA_STRANKU], "strana": strana, "dalsi": len(radky) > NA_STRANKU,
        "filtry": filtry, "tesne_rozpeti": dotazy.TESNE_ROZPETI,
    })


@router.get("/hlasovani/{id_hlasovani}", response_class=HTMLResponse)
def detail(request: Request, id_hlasovani: int, conn: sqlite3.Connection = Depends(get_db)):
    """Výsledek hlasování, půlkruh sněmovny a hlasy po klubech, s odkazem na zdroj na psp.cz."""
    hlasovani = dotazy.hlasovani_detail(conn, id_hlasovani)
    if hlasovani is None:
        raise HTTPException(404, "Hlasování nenalezeno")
    kluby = dotazy.hlasy_po_klubech(conn, id_hlasovani)
    return templates.TemplateResponse(request, "hlasovani.html", {
        "h": hlasovani,
        "kluby": kluby,
        "sedadla": _sedadla(kluby),
        "psp_url": f"https://www.psp.cz/sqw/hlasy.sqw?g={id_hlasovani}&l=cz",
    })
