"""Routy: vyhledání poslance a jeho profil s historií hlasování."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from politika.db.dotazy import hlasovani as dotazy_hlasovani
from politika.db.dotazy import poslanci as dotazy
from politika.web.app import get_db, templates

router = APIRouter()

NA_STRANKU = 50

# Skupiny hlasů pro pruh v profilu: (třída CSS, text, kódy hlasů).
_SKUPINY_HLASU = [
    ("A", "Ano", {"A"}),
    ("B", "Ne", {"B", "N"}),
    ("K", "Zdržel se", {"C", "K"}),
    ("X", "Nepřítomen / nehlasoval", {"F", "@", "M", "W"}),
]


def _slozeni(souhrn: dict[str, int]) -> list[tuple[str, str, int]]:
    """Sečte počty hlasů do čtyř skupin pro pruh v profilu: ``[(třída, text, počet), …]``."""
    return [(trida, text, sum(souhrn.get(k, 0) for k in kody))
            for trida, text, kody in _SKUPINY_HLASU]


@router.get("/poslanci", response_class=HTMLResponse)
def seznam(request: Request, q: str = "", conn: sqlite3.Connection = Depends(get_db)):
    """Seznam poslanců s vyhledáváním. Požadavek z HTMX dostane jen fragment s kartami."""
    poslanci = dotazy.hledej_poslance(conn, q)
    sablona = "_poslanci_seznam.html" if request.headers.get("HX-Request") else "poslanci.html"
    return templates.TemplateResponse(request, sablona, {"poslanci": poslanci, "q": q})


@router.get("/poslanec/{id_poslanec}", response_class=HTMLResponse)
def profil(request: Request, id_poslanec: int, strana: int = 1,
           conn: sqlite3.Connection = Depends(get_db)):
    """Profil poslance: souhrn hlasů a hlasování od nejnovějšího, po stránkách."""
    poslanec = dotazy.poslanec_detail(conn, id_poslanec)
    if poslanec is None:
        raise HTTPException(404, "Poslanec nenalezen")
    strana = max(strana, 1)
    hlasovani = dotazy_hlasovani.hlasovani_poslance(conn, id_poslanec, NA_STRANKU + 1,
                                                    (strana - 1) * NA_STRANKU)
    souhrn = dotazy.souhrn_hlasu(conn, id_poslanec)
    return templates.TemplateResponse(request, "poslanec.html", {
        "poslanec": poslanec,
        "slozeni": _slozeni(souhrn),
        "celkem": sum(souhrn.values()),
        "hlasovani": hlasovani[:NA_STRANKU],
        "strana": strana,
        "dalsi": len(hlasovani) > NA_STRANKU,
    })
