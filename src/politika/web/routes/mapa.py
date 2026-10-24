"""Routy: mapa regionálních kanceláří poslanců (Leaflet + OpenStreetMap)."""

import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from politika.db.dotazy.poslanci import hledej_poslance
from politika.web.app import get_db, templates

router = APIRouter()


def _kancelare(conn: sqlite3.Connection) -> list[dict]:
    """Kanceláře poslanců s trvajícím mandátem spojené s jejich jménem a klubem."""
    poslanci = {p["id_osoba"]: p for p in hledej_poslance(conn)}
    return [
        {"lat": k["lat"], "lng": k["lng"], "adresa": k["adresa"], "id_osoba": k["id_osoba"],
         "jmeno": poslanci[k["id_osoba"]]["jmeno"], "klub": poslanci[k["id_osoba"]]["klub"] or "nezařazení",
         "id_poslanec": poslanci[k["id_osoba"]]["id_poslanec"]}
        for k in conn.execute("SELECT id_osoba, lat, lng, adresa FROM kancelar")
        if k["id_osoba"] in poslanci
    ]


@router.get("/mapa", response_class=HTMLResponse)
def mapa(request: Request, osoba: int | None = None, conn: sqlite3.Connection = Depends(get_db)):
    """Stránka mapy; ``osoba`` přiblíží kancelář jednoho poslance."""
    kancelare = _kancelare(conn)
    return templates.TemplateResponse(request, "mapa.html", {
        "kancelare": kancelare,
        "kluby": sorted({k["klub"] for k in kancelare}),
        "osoba": osoba,
    })
