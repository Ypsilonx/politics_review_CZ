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

# Texty kódů z otevřených dat PSP.
HLAS_TEXT = {
    "A": "Ano", "B": "Ne", "N": "Ne", "C": "Zdržel se", "K": "Zdržel se",
    "F": "Nehlasoval", "@": "Nepřihlášen", "M": "Omluven", "W": "Před slibem",
}
VYSLEDEK_TEXT = {"A": "Přijato", "R": "Zamítnuto"}

templates = Jinja2Templates(directory=WEB_DIR / "templates")
templates.env.globals.update(HLAS_TEXT=HLAS_TEXT, VYSLEDEK_TEXT=VYSLEDEK_TEXT)


def get_db() -> Iterator[sqlite3.Connection]:
    """Závislost FastAPI: připojení k DB na dobu jednoho požadavku."""
    conn = get_connection(config.DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def create_app() -> FastAPI:
    """Sestaví aplikaci s routami a statickými soubory."""
    from politika.web.routes import hlasovani, poslanci

    app = FastAPI(title="Sledování poslanců")
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(poslanci.router)
    app.include_router(hlasovani.router)

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        """Úvodní stránka – do T5 (proud novinek) přesměruje na seznam poslanců."""
        return RedirectResponse("/poslanci")

    return app
