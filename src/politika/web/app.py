"""FastAPI aplikace – sestavení, šablony a sdílené závislosti."""

import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from politika import config
from politika.db.connection import get_connection

WEB_DIR = Path(__file__).parent

# Texty kódů z otevřených dat PSP. Pořadí určuje i pořadí štítků a teček v půlkruhu.
HLAS_TEXT = {
    "A": "Ano", "B": "Ne", "N": "Ne", "C": "Zdržel se", "K": "Zdržel se",
    "F": "Nehlasoval", "@": "Nepřihlášen", "M": "Omluven", "W": "Před slibem",
}
VYSLEDEK_TEXT = {"A": "Přijato", "R": "Zamítnuto"}
# Druh předmětu hlasování zjištěný ze stenozáznamu (parovani.steno.Predmet.druh).
DRUH_TEXT = {
    "pozmenovaci": "Pozměňovací návrh",
    "legislativne_technicke": "Legislativně technické úpravy",
    "celek": "Návrh jako celek",
    "proceduralni": "Procedurální hlasování",
    "jine": "Hlasování",
}

# Horní menu: (cesta, název). Úprava pořadí nebo názvů sekcí zde.
MENU = [
    ("/prehled", "Přehled"),
    ("/sledovani", "Sledovaní"),
    ("/poslanci", "Poslanci"),
    ("/hlasovani", "Hlasování"),
    ("/zakony", "Zákony"),
    ("/schuze", "Schůze"),
    ("/statistiky", "Statistiky"),
    ("/mapa", "Mapa"),
]

def datum_cz(iso: str | None) -> str:
    """Filtr šablon: ISO datum ``2026-10-23`` → ``23. 10. 2026`` (prázdný vstup → ``""``)."""
    if not iso:
        return ""
    r, m, d = iso[:10].split("-")
    return f"{int(d)}. {int(m)}. {r}"


def stav_dat() -> str:
    """Datum zpracování otevřených dat (poslední stažení ZIPu hlasování) – podmínka užití dat PSP."""
    zip_hlasovani = config.OPENDATA_DIR / f"hl-{config.OBDOBI}.zip"
    if not zip_hlasovani.exists():
        return ""
    return datum_cz(datetime.fromtimestamp(zip_hlasovani.stat().st_mtime).date().isoformat())


templates = Jinja2Templates(directory=WEB_DIR / "templates")
templates.env.globals.update(HLAS_TEXT=HLAS_TEXT, VYSLEDEK_TEXT=VYSLEDEK_TEXT,
                             DRUH_TEXT=DRUH_TEXT, MENU=MENU, PSP_URL="https://www.psp.cz")
templates.env.filters["datum"] = datum_cz
templates.env.globals["stav_dat"] = stav_dat


def get_db() -> Iterator[sqlite3.Connection]:
    """Závislost FastAPI: připojení k DB na dobu jednoho požadavku."""
    conn = get_connection(config.DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def z_teto_aplikace(request: Request) -> None:
    """Ochrana proti CSRF: změnu přijme jen z vlastní stránky (Origin, případně Referer).

    Prohlížeč posílá u POST formuláře hlavičku Origin; cizí stránka v domácí síti tak nemůže
    nic měnit ani spouštět. Požadavek bez obou hlaviček (např. curl) se nepovažuje za útok
    z prohlížeče.
    """
    zdroj = request.headers.get("origin") or request.headers.get("referer")
    if zdroj and urlsplit(zdroj).netloc != request.url.netloc:
        raise HTTPException(403, "Změna je povolená jen ze stránek této aplikace.")


def create_app() -> FastAPI:
    """Sestaví aplikaci s routami a statickými soubory."""
    from politika.web.routes import (
        aktualizace, hlasovani, hledani, mapa, poslanci, schuze, sledovani, statistiky, tisky,
    )

    app = FastAPI(title="Sledování poslanců")
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(poslanci.router)
    app.include_router(hlasovani.router)
    app.include_router(tisky.router)
    app.include_router(schuze.router)
    app.include_router(statistiky.router)
    app.include_router(mapa.router)
    app.include_router(sledovani.router)
    app.include_router(hledani.router)
    app.include_router(aktualizace.router)

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        """Úvodní stránka = Přehled."""
        return RedirectResponse("/prehled")

    return app
