"""Routy: tlačítko „Aktualizovat“ – spustí ``politika obnova`` na pozadí a ukazuje průběh.

Obnova běží jako samostatný proces (``python -m politika obnova --cerstve-ihned``): přes den
stáhne otevřená data a čerstvé schůze, v nočním okně i zbytek. Web drží nejvýš jeden běh, aby
se na psp.cz nikdy nestahovalo souběžně, a pustí ho jen jednou za den
(``config.ZACATEK_DNE_AKTUALIZACE``). Výstup jde do ``data/aktualizace.log``.
"""

import os
import subprocess
import sys
from datetime import datetime, time, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from politika import config
from politika.web.app import templates, z_teto_aplikace

router = APIRouter()

LOG = config.DATA_DIR / "aktualizace.log"
# Čas posledního spuštění z webu (ISO); v souboru, aby denní limit přežil restart serveru.
POSLEDNI = config.DATA_DIR / "aktualizace_posledni.txt"
# Kolik posledních řádků výpisu obnovy ukázat na stránce.
RADKU_VYPISU = 6


class _Beh:
    """Stav posledního běhu obnovy spuštěného z webu (v paměti procesu webu)."""

    proces: subprocess.Popen | None = None
    spusteno: datetime | None = None


def _bezi() -> bool:
    """Zda běh obnovy spuštěný z webu ještě neskončil."""
    return _Beh.proces is not None and _Beh.proces.poll() is None


def dalsi_mozna(posledni: datetime, zacatek_dne: int) -> datetime:
    """Od kdy jde aktualizaci znovu spustit: začátek dne následujícího po běhu ``posledni``.

    Den začíná v hodinu ``zacatek_dne`` – běh v 1:00 při začátku ve 2 h patří ještě
    k předchozímu dni, takže tlačítko se uvolní už ve 2:00 téhož rána.
    """
    den = (posledni - timedelta(hours=zacatek_dne)).date()
    return datetime.combine(den + timedelta(days=1), time(zacatek_dne))


def _blokovano_do() -> datetime | None:
    """Do kdy je tlačítko zablokované po dnešním běhu; ``None`` = jde spustit."""
    if not POSLEDNI.exists():
        return None
    od = dalsi_mozna(datetime.fromisoformat(POSLEDNI.read_text().strip()),
                     config.ZACATEK_DNE_AKTUALIZACE)
    return od if datetime.now() < od else None


def _stav(request: Request) -> HTMLResponse:
    """Panel s tlačítkem a stavem: běží (s posledními řádky výpisu) / skončilo / nic."""
    radky = []
    if _Beh.proces is not None and LOG.exists():
        radky = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-RADKU_VYPISU:]
    return templates.TemplateResponse(request, "_aktualizace.html", {
        "bezi": _bezi(),
        "blokovano_do": _blokovano_do(),
        "spusteno": _Beh.spusteno,
        "kod": _Beh.proces.returncode if _Beh.proces is not None and not _bezi() else None,
        "radky": radky,
        "okno": config.NOCNI_OKNO,
    })


@router.get("/aktualizace", response_class=HTMLResponse)
def stav(request: Request):
    """Aktuální stav panelu (HTMX ho během běhu načítá opakovaně)."""
    return _stav(request)


@router.post("/aktualizace", response_class=HTMLResponse)
def spustit(request: Request):
    """Spustí obnovu na pozadí, pokud už neběží a dnes ještě neběžela; vrátí panel se stavem."""
    z_teto_aplikace(request)
    if not _bezi() and _blokovano_do() is None:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("w", encoding="utf-8") as vystup:
            _Beh.proces = subprocess.Popen(
                [sys.executable, "-m", "politika", "obnova", "--cerstve-ihned"],
                stdout=vystup, stderr=subprocess.STDOUT, cwd=config.PROJEKT_DIR,
                env=os.environ | {"PYTHONUTF8": "1"},
            )
        _Beh.spusteno = datetime.now()
        POSLEDNI.write_text(_Beh.spusteno.isoformat(timespec="seconds"))
    return _stav(request)
