"""Routy: statistiky – žebříčky poslanců, jednota a shoda klubů, nejtěsnější hlasování."""

import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from politika.analyza import statistiky
from politika.web.app import get_db, templates
from politika.web.export import csv_odpoved

router = APIRouter()

# Kolik poslanců ukázat v každém žebříčku.
DELKA_ZEBRICKU = 10


@router.get("/statistiky", response_class=HTMLResponse)
def prehled(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    """Žebříčky (účast, neomluvené absence, vystoupení, rebelové), kluby a těsná hlasování."""
    poslanci = statistiky.zebricek_poslancu(conn)
    s_hlasovanim = [p for p in poslanci if p["celkem"]]
    kluby, shoda = statistiky.shoda_klubu(conn)
    return templates.TemplateResponse(request, "statistiky.html", {
        "nejnizsi_ucast": sorted(s_hlasovanim, key=lambda p: p["ucast"])[:DELKA_ZEBRICKU],
        "neomluveni": sorted(s_hlasovanim, key=lambda p: -p["neomluven"])[:DELKA_ZEBRICKU],
        "nejvic_vystoupeni": sorted(poslanci, key=lambda p: -p["vystoupeni"])[:DELKA_ZEBRICKU],
        "nepromluvili": sorted((p for p in poslanci if not p["vystoupeni"]),
                               key=lambda p: p["prijmeni"]),
        "rebelove": sorted(s_hlasovanim, key=lambda p: -p["proti_klubu"])[:DELKA_ZEBRICKU],
        "jednota": statistiky.jednota_klubu(conn),
        "kluby": kluby,
        "shoda": shoda,
        "tesna": statistiky.nejtesnejsi_hlasovani(conn, DELKA_ZEBRICKU),
    })


@router.get("/statistiky/poslanci.csv")
def export_poslanci(conn: sqlite3.Connection = Depends(get_db)):
    """Statistiky všech poslanců (účast, absence, proti klubu, vystoupení) jako CSV."""
    return csv_odpoved(
        "statistiky-poslancu.csv",
        ["poslanec", "klub", "hlasování", "přítomen", "omluven", "neomluven", "účast %",
         "proti klubu", "vystoupení"],
        ([p["jmeno"], p["klub"], p["celkem"], p["pritomen"], p["omluven"], p["neomluven"],
          round(p["ucast"], 1), p["proti_klubu"], p["vystoupeni"]]
         for p in statistiky.zebricek_poslancu(conn)),
    )
