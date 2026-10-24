"""Export tabulek do CSV pro Excel (UTF-8 s BOM, oddělovač středník – český Excel)."""

import csv
import io
from collections.abc import Iterable
from urllib.parse import quote

from fastapi.responses import Response

from politika.web.app import DRUH_TEXT, HLAS_TEXT, VYSLEDEK_TEXT


def csv_odpoved(nazev_souboru: str, hlavicka: list[str], radky: Iterable[Iterable[object]]) -> Response:
    """Vrátí CSV jako soubor ke stažení."""
    vystup = io.StringIO()
    zapis = csv.writer(vystup, delimiter=";")
    zapis.writerow(hlavicka)
    zapis.writerows(radky)
    return Response(
        "﻿" + vystup.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nazev_souboru)}"},
    )


HLAVICKA_HLASOVANI = ["datum", "čas", "schůze", "číslo", "o čem", "tisk", "druh předmětu",
                      "označení návrhu", "uvozující věta", "výsledek", "pro", "proti", "zdrželo se"]


def radek_hlasovani(h) -> list[object]:
    """Sloupce hlasování pro CSV (odpovídá ``HLAVICKA_HLASOVANI``)."""
    return [h["datum"], h["cas"], h["schuze"], h["cislo"], h["popis"], h["tisk_ct"],
            DRUH_TEXT.get(h["predmet_druh"], ""), h["predmet_oznaceni"], h["predmet_otazka"],
            VYSLEDEK_TEXT.get(h["vysledek"], h["vysledek"]), h["pro"], h["proti"], h["zdrzel"]]


def text_hlasu(kod: str) -> str:
    """Text hlasu poslance pro CSV."""
    return HLAS_TEXT.get(kod, kod)
