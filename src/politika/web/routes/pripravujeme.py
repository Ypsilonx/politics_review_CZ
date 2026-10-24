"""Zástupné stránky sekcí, které ještě nejsou hotové (nahradí je tasky T6–T9)."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from politika.web.app import MENU, templates

router = APIRouter()

# Co v sekci bude – zobrazí se na zástupné stránce, ať je jasné, kam aplikace míří.
_POPIS = {
    "/prehled": "Novinky u sledovaných poslanců, rychlé statistiky a nejbližší schůze.",
    "/sledovani": "Vybraní poslanci, kluby a vlastní skupiny a jejich hlasování na jednom místě.",
    "/hlasovani": "Všechna hlasování s filtry podle schůze, tisku a výsledku.",
    "/zakony": "Sněmovní tisky: stav projednávání, znění, pozměňovací návrhy a hlasování.",
    "/schuze": "Schůze, jejich pořad a hlasování po jednotlivých bodech.",
    "/statistiky": "Účast, vystoupení, hlasování proti klubu a shoda mezi kluby.",
    "/mapa": "Regionální kanceláře poslanců na mapě.",
}


def _zastupna_stranka(cesta: str, nazev: str):
    """Vytvoří handler zástupné stránky pro jednu sekci menu."""

    def handler(request: Request):
        """Zástupná stránka sekce, která se připravuje."""
        return templates.TemplateResponse(request, "pripravujeme.html",
                                          {"nazev": nazev, "popis": _POPIS[cesta]})

    return handler


for _cesta, _nazev in MENU:
    if _cesta in _POPIS:
        router.add_api_route(_cesta, _zastupna_stranka(_cesta, _nazev),
                             response_class=HTMLResponse, include_in_schema=False)
