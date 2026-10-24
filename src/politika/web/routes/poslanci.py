"""Routy: vyhledání poslance a jeho profil s historií hlasování."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from politika import config
from politika.analyza import statistiky
from politika.db.dotazy import hlasovani as dotazy_hlasovani
from politika.db.dotazy import poslanci as dotazy
from politika.db.dotazy.sledovani import je_sledovany
from politika.dokumenty.foto import cesta_fotky
from politika.web.app import get_db, templates
from politika.web.export import HLAVICKA_HLASOVANI, csv_odpoved, radek_hlasovani, text_hlasu

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
    poslanci = [{**p, "foto": cesta_fotky(p["id_osoba"]).exists()}
                for p in dotazy.hledej_poslance(conn, q)]
    sablona = "_poslanci_seznam.html" if request.headers.get("HX-Request") else "poslanci.html"
    return templates.TemplateResponse(request, sablona, {"poslanci": poslanci, "q": q})


# Záložky profilu: (klíč v URL, název).
ZALOZKY = [
    ("hlasovani", "Hlasování"),
    ("proti-klubu", "Proti klubu"),
    ("vystoupeni", "Vystoupení"),
    ("navrhy", "Návrhy zákonů a pozměňovací návrhy"),
]


@router.get("/poslanec/{id_poslanec}", response_class=HTMLResponse)
def profil(request: Request, id_poslanec: int, zalozka: str = "hlasovani", strana: int = 1,
           conn: sqlite3.Connection = Depends(get_db)):
    """Profil poslance: přehled (docházka, proti klubu, vystoupení, členství) a záložky s detaily."""
    poslanec = dotazy.poslanec_detail(conn, id_poslanec)
    if poslanec is None:
        raise HTTPException(404, "Poslanec nenalezen")
    if zalozka not in dict(ZALOZKY):
        zalozka = "hlasovani"
    strana = max(strana, 1)
    souhrn = dotazy.souhrn_hlasu(conn, id_poslanec)
    vystoupeni = statistiky.vystoupeni(conn, poslanec["id_osoba"])
    navrhy = dotazy.navrhy_zakonu(conn, poslanec["id_osoba"])
    pozmenovaci = dotazy.pozmenovaci_navrhy(conn, poslanec["id_osoba"])
    kontext = {
        "poslanec": poslanec,
        "foto": f"/foto/{poslanec['id_osoba']}" if cesta_fotky(poslanec["id_osoba"]).exists() else None,
        "kancelar": conn.execute("SELECT adresa FROM kancelar WHERE id_osoba = ? LIMIT 1",
                                 (poslanec["id_osoba"],)).fetchone(),
        "kraj": dotazy.kraj(conn, poslanec["id_kraj"]),
        "sledovany": je_sledovany(conn, "poslanec", id_poslanec),
        "clenstvi": dotazy.clenstvi(conn, poslanec["id_osoba"]),
        "slozeni": _slozeni(souhrn),
        "celkem": sum(souhrn.values()),
        "dochazka": statistiky.dochazka(conn, id_poslanec),
        "pocet_proti_klubu": statistiky.pocet_proti_klubu(conn, id_poslanec),
        "vystoupeni": vystoupeni,
        "navrhy": navrhy,
        "pozmenovaci": pozmenovaci,
        "zalozky": ZALOZKY,
        "zalozka": zalozka,
        "strana": strana,
        "obdobi_url": config.OBDOBI,
    }
    if zalozka == "hlasovani":
        hlasovani = dotazy_hlasovani.hlasovani_poslance(conn, id_poslanec, NA_STRANKU + 1,
                                                        (strana - 1) * NA_STRANKU)
        kontext.update(hlasovani=hlasovani[:NA_STRANKU], dalsi=len(hlasovani) > NA_STRANKU)
    elif zalozka == "proti-klubu":
        kontext["proti_klubu"] = statistiky.proti_klubu(conn, id_poslanec)
    return templates.TemplateResponse(request, "poslanec.html", kontext)


@router.get("/foto/{id_osoba}")
def foto(id_osoba: int) -> FileResponse:
    """Fotka poslance ze složky ``data/foto`` (cesta se skládá jen z čísla osoby)."""
    cesta = cesta_fotky(id_osoba)
    if not cesta.is_file():
        raise HTTPException(404, "Fotka není k dispozici")
    return FileResponse(cesta, media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=604800"})


@router.get("/poslanec/{id_poslanec}/hlasovani.csv")
def export_hlasovani(id_poslanec: int, conn: sqlite3.Connection = Depends(get_db)):
    """Všechna hlasování poslance s jeho hlasem jako CSV."""
    poslanec = dotazy.poslanec_detail(conn, id_poslanec)
    if poslanec is None:
        raise HTTPException(404, "Poslanec nenalezen")
    radky = dotazy_hlasovani.hlasovani_poslance(conn, id_poslanec, limit=-1)
    nazev = f"hlasovani-{poslanec['prijmeni']}-{poslanec['jmeno']}.csv"
    return csv_odpoved(nazev, [*HLAVICKA_HLASOVANI, "hlasoval"],
                       ([*radek_hlasovani(h), text_hlasu(h["hlas"])] for h in radky))
