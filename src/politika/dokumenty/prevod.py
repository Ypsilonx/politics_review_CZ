"""Převod DOCX pozměňovacích návrhů na HTML pro zobrazení v aplikaci (rozhodnutí 2A)."""

from pathlib import Path

import mammoth
from bs4 import BeautifulSoup

# Povolené značky a atributy převedeného HTML; vše ostatní se odstraní (obsah značky zůstane).
_ZNACKY = {"p", "br", "strong", "em", "u", "s", "sub", "sup", "h1", "h2", "h3", "h4", "h5", "h6",
           "ul", "ol", "li", "table", "thead", "tbody", "tr", "td", "th", "a", "img", "span"}
_ATRIBUTY = {"a": {"href"}, "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"},
             "img": {"src", "alt"}}
_BEZPECNE_ODKAZY = ("http://", "https://", "#", "mailto:")


def vycisti_html(html: str) -> str:
    """Ponechá jen povolené značky a atributy; odkazy jen http(s)/mailto/kotvy, obrázky jen data:."""
    soup = BeautifulSoup(html, "html.parser")
    for znacka in soup.find_all(["script", "style"]):
        znacka.decompose()  # i s obsahem – text skriptu nemá na stránce co dělat
    for znacka in soup.find_all(True):
        if znacka.name not in _ZNACKY:
            znacka.unwrap()
            continue
        povolene = _ATRIBUTY.get(znacka.name, set())
        for atribut in list(znacka.attrs):
            if atribut not in povolene:
                del znacka[atribut]
        if znacka.name == "a" and not znacka.get("href", "").startswith(_BEZPECNE_ODKAZY):
            znacka.attrs.pop("href", None)
        if znacka.name == "img" and not znacka.get("src", "").startswith("data:image/"):
            znacka.decompose()
    return str(soup)


def docx_na_html(cesta: Path) -> Path:
    """Převede DOCX na vyčištěný HTML fragment a uloží ho vedle originálu (``soubor.docx.html``).

    Už existující převod se nepřepisuje.

    :return: cesta k HTML souboru
    """
    cil = cesta.with_name(cesta.name + ".html")
    if not cil.exists():
        with cesta.open("rb") as f:
            vysledek = mammoth.convert_to_html(f)
        cil.write_text(vycisti_html(vysledek.value), encoding="utf-8")
    return cil
