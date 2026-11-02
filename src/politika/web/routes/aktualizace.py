"""Routy: tlačítko „Aktualizovat“ – spustí ``politika obnova`` na pozadí a ukazuje průběh.

Obnova běží jako samostatný proces (``python -m politika obnova --cerstve-ihned``): přes den
stáhne otevřená data a čerstvé schůze, v nočním okně i zbytek. Web drží nejvýš jeden běh, aby
se na psp.cz nikdy nestahovalo souběžně, a pustí ho jen jednou za den
(``config.ZACATEK_DNE_AKTUALIZACE``). Výstup jde do ``data/aktualizace.log``.
Po skončení běhu se stránka sama obnoví (``HX-Refresh``) a panel ukáže, co v datech přibylo.
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from politika import config
from politika.web.app import get_db, templates, z_teto_aplikace

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
    pred: dict | None = None  # souhrn dat před během (pro „co přibylo“)


def souhrn_dat(conn: sqlite3.Connection) -> dict:
    """Počty, podle kterých se po běhu pozná, co přibylo: hlasování, nejnovější datum, předměty."""
    pocet, posledni = conn.execute("SELECT COUNT(*), MAX(datum) FROM hlasovani").fetchone()
    predmetu = conn.execute("SELECT COUNT(*) FROM predmet_hlasovani").fetchone()[0]
    return {"hlasovani": pocet, "posledni": posledni, "predmetu": predmetu}


def pribylo(pred: dict, po: dict) -> dict:
    """Rozdíl dvou souhrnů dat: kolik hlasování a zjištěných předmětů přibylo, nejnovější datum."""
    return {"hlasovani": po["hlasovani"] - pred["hlasovani"],
            "predmetu": po["predmetu"] - pred["predmetu"], "posledni": po["posledni"]}


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


def _prubeh() -> dict | None:
    """Stav běžící obnovy ze ``config.STAV_OBNOVY`` (fáze, krok X z N); ``None``, když není.

    Obnova soubor přepisuje během čtení, takže rozepsaný JSON se bere jako „zatím nic“ –
    panel se za 3 s načte znovu.
    """
    try:
        return json.loads(config.STAV_OBNOVY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _stav(request: Request, conn: sqlite3.Connection) -> HTMLResponse:
    """Panel s tlačítkem a stavem: běží (průběh a poslední řádky výpisu) / skončilo / nic."""
    radky = []
    if _Beh.proces is not None and LOG.exists():
        radky = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-RADKU_VYPISU:]
    bezi = _bezi()
    kod = _Beh.proces.returncode if _Beh.proces is not None and not bezi else None
    return templates.TemplateResponse(request, "_aktualizace.html", {
        "bezi": bezi,
        "prubeh": _prubeh() if bezi else None,
        "minut": int((datetime.now() - _Beh.spusteno).total_seconds() // 60) if bezi else 0,
        "blokovano_do": _blokovano_do(),
        "spusteno": _Beh.spusteno,
        "kod": kod,
        "pribylo": pribylo(_Beh.pred, souhrn_dat(conn)) if kod is not None and _Beh.pred else None,
        "radky": radky,
        "okno": config.NOCNI_OKNO,
    })


@router.get("/aktualizace", response_class=HTMLResponse)
def stav(request: Request, sleduji: bool = False, conn: sqlite3.Connection = Depends(get_db)):
    """Aktuální stav panelu (HTMX ho během běhu načítá opakovaně).

    :param sleduji: dotaz z panelu, který ukazoval běžící obnovu – když mezitím skončila,
        obnoví se celá stránka, aby ukazovala nová data
    """
    if sleduji and not _bezi():
        return HTMLResponse("", headers={"HX-Refresh": "true"})
    return _stav(request, conn)


@router.post("/aktualizace", response_class=HTMLResponse)
def spustit(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    """Spustí obnovu na pozadí, pokud už neběží a dnes ještě neběžela; vrátí panel se stavem."""
    z_teto_aplikace(request)
    if not _bezi() and _blokovano_do() is None:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        config.STAV_OBNOVY.unlink(missing_ok=True)  # ať se neukáže průběh minulého běhu
        with LOG.open("w", encoding="utf-8") as vystup:
            _Beh.proces = subprocess.Popen(
                [sys.executable, "-m", "politika", "obnova", "--cerstve-ihned"],
                stdout=vystup, stderr=subprocess.STDOUT, cwd=config.PROJEKT_DIR,
                env=os.environ | {"PYTHONUTF8": "1"},
            )
        _Beh.pred = souhrn_dat(conn)
        _Beh.spusteno = datetime.now()
        POSLEDNI.write_text(_Beh.spusteno.isoformat(timespec="seconds"))
    return _stav(request, conn)
