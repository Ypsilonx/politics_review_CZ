"""Testy vytažení odkazů z reálných stránek psp.cz (uložených v tests/data)."""

from pathlib import Path

from politika.dokumenty.odkazy import (
    je_autorizovano, pdf_tisku, pozmenovaci_navrhy, verze_tisku,
)
from politika.dokumenty.stahovani import precti_html

DATA = Path(__file__).parent / "data"


def test_neautorizovany_usek():
    assert not je_autorizovano(precti_html(DATA / "steno_s034426.htm"))


def test_historie_213_verze_a_pozmenovaci_navrhy():
    html = precti_html(DATA / "historie_213.html")
    assert verze_tisku(html, 213) == [0, 1, 2, 3]
    navrhy = pozmenovaci_navrhy(html)
    assert [n.cislo_sd for n in navrhy][:2] == [1316, 1729]
    prvni = navrhy[0]
    assert prvni.id_osoba == 6524
    assert prvni.soubor == "30316-46031.docx"
    assert prvni.url.endswith("orig2.sqw?idd=271374")
    assert prvni.popis is None
    assert any(n.popis and "soudního řádu" in n.popis for n in navrhy)


def test_pdf_verze_tisku():
    assert pdf_tisku(precti_html(DATA / "tiskt_213_3.html")) == [
        ("/sqw/text/orig2.sqw?idd=281676", "t021303.pdf")
    ]
