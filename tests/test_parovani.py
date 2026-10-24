"""Testy předmětu hlasování na reálných úsecích stenozáznamu 34. schůze."""

from pathlib import Path

from politika.dokumenty.stahovani import precti_html
from politika.parovani.navrhy import verze_s_navrhy
from politika.parovani.steno import Usek, rozpoznej_predmet, usek_na_text, uryvky_schuze

DATA = Path(__file__).parent / "data"
# id_hlasovani → datum pro hlasování 34. schůze, která se v testovaných úsecích vyskytují.
DATUM = {88845: "2026-10-23", 88863: "2026-10-23", 88864: "2026-10-23",
         88868: "2026-10-23", 88602: "2026-10-13"}


def _uryvky(*soubory: str) -> dict[int, str]:
    useky = [usek_na_text(precti_html(DATA / s)) for s in soubory]
    return {k: u.text for k, u in uryvky_schuze(useky, DATUM).items()}


def test_datum_useku():
    assert usek_na_text(precti_html(DATA / "steno_s034426.htm")).datum == "2026-10-23"


def test_274_navrh_poslance_bendy():
    uryvek = _uryvky("steno_s034426.htm")[88863]
    assert "hlasujeme návrh pana poslance Bendy" in uryvek
    assert uryvek.endswith("proti 98.")  # končí větou s výsledkem, další text už ne
    predmet = rozpoznej_predmet(uryvek)
    assert predmet.druh == "proceduralni"
    assert predmet.otazka.startswith("Takže prosím vás, takže hlasujeme návrh pana poslance Bendy")


def test_chybny_odkaz_jineho_dne_se_ignoruje():
    # „pevné hlasování 18. 5. 2027“ psp.cz odkazuje na hlasování č. 18 z 13. 10. – nesmí se přijmout
    assert 88602 not in _uryvky("steno_s034426.htm")


def test_256_preruseni_schuze_a_pozdejsi_namitka_neprepise():
    uryvek = _uryvky("steno_s034402.htm")[88845]
    assert "přerušit schůzi do 3. listopadu do 14 hodin" in uryvek
    assert "Rázga" not in uryvek  # námitka „K hlasování 256“ přišla až po vyhlášení
    assert rozpoznej_predmet(uryvek).druh == "proceduralni"


def test_hlasovani_bez_odkazu_nema_uryvek():
    assert 88846 not in _uryvky("steno_s034402.htm", "steno_s034426.htm")


def test_rozpoznani_pozmenovaciho_navrhu_a_celku():
    assert rozpoznej_predmet(
        "Předsedající: Nyní budeme hlasovat o pozměňovacím návrhu B2 pana poslance X. "
        "Zahajuji hlasování.\nHlasování číslo 5, přihlášeno 180.").oznaceni == "B2"
    celek = rozpoznej_predmet(
        "Předsedající: Přistoupíme k hlasování o návrhu zákona jako celku. "
        "Zahajuji hlasování.\nHlasování číslo 9, přihlášeno 180.")
    assert celek.druh == "celek"


def test_verze_tisku_s_pozmenovacimi_navrhy():
    # 213/2 byl zrušen a návrhy znovu rozeslány jako 213/3 – platí poslední zmínka
    assert verze_s_navrhy(precti_html(DATA / "historie_213.html"), 213) == 3


def test_mezera_mezi_useky_nepreda_stary_text():
    znacka = "\x00H88845\x00"  # značka odkazu na hlasování, jak ji vkládá usek_na_text
    useky = [Usek("2026-10-23", "Dávný text o něčem jiném.", turn=400),
             Usek("2026-10-23", f"Hlasujeme o přestávce. {znacka}hlasování číslo 256, pro 65.",
                  turn=402)]
    uryvek = uryvky_schuze(useky, {88845: "2026-10-23"})[88845].text
    assert "Dávný" not in uryvek and "přestávce" in uryvek


def test_oznaceni_samotnym_pismenem_a_vyctem():
    assert rozpoznej_predmet("Nyní budeme hlasovat pozměňovací návrh B Marka Nováka. "
                             "Zahajuji hlasování.\nHlasování číslo 1.").oznaceni == "B"
    assert rozpoznej_predmet("Dále budeme hlasovat jedním hlasováním pozměňovací návrhy A3, A4 "
                             "a A6 až A13. Zahajuji hlasování.\nHlasování číslo 2."
                             ).oznaceni == "A3, A4 a A6 až A13"


def test_nahradni_otazka_bez_formuli():
    predmet = rozpoznej_predmet(
        "Návrh byl přijat. Posledním z těch tří nových bodů je sněmovní tisk 285, novela zákona "
        "o doplňkovém penzijním spoření, druhé čtení. Zahajuji hlasování. Kdo je pro? Kdo je proti?"
        "\nHlasování číslo 7, přihlášeno 171 poslanců, pro 97, proti 12.")
    assert predmet.otazka == ("Posledním z těch tří nových bodů je sněmovní tisk 285, novela "
                              "zákona o doplňkovém penzijním spoření, druhé čtení.")
