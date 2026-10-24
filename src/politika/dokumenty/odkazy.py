"""Vytažení odkazů na dokumenty ze stránek psp.cz (čisté funkce nad HTML, bez sítě)."""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

_NEAUTORIZOVANO = "neautorizováno"


def je_autorizovano(html: str) -> bool:
    """Zda úsek stenozáznamu už prošel autorizací (neautorizovaný nese poznámku na stránce)."""
    return _NEAUTORIZOVANO not in html.casefold()


def verze_tisku(html: str, ct: int) -> list[int]:
    """Vrátí čísla verzí tisku (``ct1``) odkazovaných ze stránky historie tisku (213/0, 213/3 …)."""
    vzor = re.compile(rf"tiskt\.sqw\?o=10&ct={ct}&ct1=(\d+)", re.IGNORECASE)
    return sorted({int(m.group(1)) for m in vzor.finditer(html)})


@dataclass(frozen=True)
class PozmenovaciNavrh:
    """Písemný pozměňovací návrh (sněmovní dokument) z tabulky na stránce historie tisku."""

    cislo_sd: int
    id_osoba: int | None
    url: str
    soubor: str
    popis: str | None
    datum: str | None


def pozmenovaci_navrhy(html: str) -> list[PozmenovaciNavrh]:
    """Načte tabulku „Písemné pozměňovací návrhy“ ze stránky historie tisku.

    Řádek tabulky: číslo SD | autor (odkaz detail.sqw?id=) | soubor (orig2.sqw) | popis | datum.
    """
    navrhy = []
    for tr in BeautifulSoup(html, "html.parser").find_all("tr"):
        bunky = tr.find_all("td", recursive=False)
        soubor = tr.find("a", href=re.compile(r"orig2\.sqw\?idd="))
        if len(bunky) != 5 or soubor is None or not bunky[0].get_text(strip=True).isdigit():
            continue
        autor = bunky[1].find("a", href=re.compile(r"detail\.sqw\?id=\d+"))
        id_osoba = int(re.search(r"id=(\d+)", autor["href"]).group(1)) if autor else None
        popis = bunky[3].get_text(" ", strip=True) or None
        navrhy.append(PozmenovaciNavrh(
            cislo_sd=int(bunky[0].get_text(strip=True)),
            id_osoba=id_osoba,
            url=soubor["href"],
            soubor=soubor.get_text(strip=True),
            popis=popis,
            datum=bunky[4].get_text(" ", strip=True).replace("\xa0", " ") or None,
        ))
    return navrhy


def pdf_tisku(html: str) -> list[tuple[str, str]]:
    """Vrátí PDF soubory ze stránky verze tisku jako ``[(url, název souboru), …]``."""
    return [
        (a["href"], a.get_text(strip=True))
        for a in BeautifulSoup(html, "html.parser").find_all("a", href=re.compile(r"orig2\.sqw"))
        if a.get("title") == "Dokument PDF"
    ]
