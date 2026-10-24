"""FastAPI aplikace – sestavení, šablony a sdílené závislosti."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import FastAPI
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


templates = Jinja2Templates(directory=WEB_DIR / "templates")
templates.env.globals.update(HLAS_TEXT=HLAS_TEXT, VYSLEDEK_TEXT=VYSLEDEK_TEXT,
                             DRUH_TEXT=DRUH_TEXT, MENU=MENU, PSP_URL="https://www.psp.cz")
templates.env.filters["datum"] = datum_cz


def get_db() -> Iterator[sqlite3.Connection]:
    """Závislost FastAPI: připojení k DB na dobu jednoho požadavku."""
    conn = get_connection(config.DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def create_app() -> FastAPI:
    """Sestaví aplikaci s routami a statickými soubory."""
    from politika.web.routes import (
        dokumenty, hlasovani, mapa, poslanci, schuze, sledovani, statistiky, tisky,
    )

    app = FastAPI(title="Sledování poslanců")
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(poslanci.router)
    app.include_router(hlasovani.router)
    app.include_router(tisky.router)
    app.include_router(schuze.router)
    app.include_router(dokumenty.router)
    app.include_router(statistiky.router)
    app.include_router(mapa.router)
    app.include_router(sledovani.router)

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        """Úvodní stránka = Přehled."""
        return RedirectResponse("/prehled")

    return app
