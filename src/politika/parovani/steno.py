"""Předmět hlasování ze stenozáznamu.

PSP ve stenozáznamu odkazuje vyhlášení výsledku na hlasování (``<a href="/sqw/hlasy.sqw?G=ID">``).
Číslo zazní až po hlasování („Hlasování číslo 274, přihlášeno…“), předmět je v textu před ním:
úryvek je proto text od předchozího vyhlášeného hlasování po tento odkaz.

Automatické odkazy PSP občas chybují („pevné hlasování 18. 5.“ → hlasování č. 18 jiného dne),
proto se odkaz přijme jen tehdy, když datum hlasování sedí s dnem úseku, a bere se jen první
odkaz na dané hlasování (další jsou námitky typu „K hlasování 256 …“).
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

# Maximální délka úryvku – předmět bývá v posledních větách před hlasováním.
MAX_DELKA_URYVKU = 1500

_MESICE = {
    "ledna": 1, "února": 2, "března": 3, "dubna": 4, "května": 5, "června": 6, "července": 7,
    "srpna": 8, "září": 9, "října": 10, "listopadu": 11, "prosince": 12,
}
_ODKAZ_HLASOVANI = re.compile(r"hlasy\.sqw\?G=(\d+)", re.IGNORECASE)
_ZNACKA = "\x00H{}\x00"
_ZNACKA_RE = re.compile(r"\x00H(\d+)\x00")


@dataclass(frozen=True)
class Usek:
    """Úsek stenozáznamu převedený na text: datum jednání (ISO) a text se značkami hlasování.

    ``turn`` je číslo úseku ve schůzi; podle něj se pozná, že mezi úseky nic nechybí.
    """

    datum: str | None
    text: str
    turn: int | None = None


def usek_na_text(html: str) -> Usek:
    """Převede HTML úseku na čistý text projevů; odkazy na hlasování nahradí značkou ``\\0H<id>\\0``.

    Bere jen odstavce projevů (``<p align="justify">``); jméno řečníka zůstává na začátku
    odstavce („Předseda PSP Tomio Okamura: …“).
    """
    soup = BeautifulSoup(html, "html.parser")
    datum = None
    if (p_datum := soup.find("p", class_="date")) is not None:
        m = re.search(r"(\d{1,2})\.\s*(\w+)\s+(\d{4})", p_datum.get_text(" ").replace("\xa0", " "))
        if m and m.group(2) in _MESICE:
            datum = f"{m.group(3)}-{_MESICE[m.group(2)]:02d}-{int(m.group(1)):02d}"
    odstavce = []
    for p in soup.find_all("p", align="justify"):
        for a in p.find_all("a", href=_ODKAZ_HLASOVANI):
            a.insert_before(_ZNACKA.format(_ODKAZ_HLASOVANI.search(a["href"]).group(1)))
        text = " ".join(p.get_text(" ").replace("\xa0", " ").split())
        if text:
            odstavce.append(text)
    return Usek(datum, "\n".join(odstavce))


@dataclass(frozen=True)
class Uryvek:
    """Úryvek před vyhlášením hlasování a index úseku, ve kterém vyhlášení zaznělo."""

    text: str
    usek: int


def uryvky_schuze(useky: list[Usek], datum_hlasovani: dict[int, str]) -> dict[int, Uryvek]:
    """Najde pro každé hlasování schůze úryvek textu, který mu předchází.

    :param useky: úseky stenozáznamu schůze v pořadí jednání
    :param datum_hlasovani: ``{id_hlasovani: datum ISO}`` hlasování této schůze
    :return: ``{id_hlasovani: Uryvek}`` pro hlasování, jejichž vyhlášení se ve stenozáznamu našlo
    """
    uryvky: dict[int, Uryvek] = {}
    predchozi = ""  # text od posledního přijatého odkazu (přes hranice navazujících úseků)
    for index, usek in enumerate(useky):
        if index and None not in (usek.turn, useky[index - 1].turn)                 and usek.turn != useky[index - 1].turn + 1:
            predchozi = ""  # mezi úseky chybí jednání – starší text k hlasování nepatří
        casti = _ZNACKA_RE.split(usek.text)  # [text, id, text, id, text, …]
        predchozi += casti[0] + "\n"
        for i in range(1, len(casti), 2):
            id_h = int(casti[i])
            platny = id_h in datum_hlasovani and id_h not in uryvky and (
                usek.datum is None or datum_hlasovani[id_h] == usek.datum)
            if platny:
                veta, zbytek = _veta_vysledku(casti[i + 1])
                uryvky[id_h] = Uryvek(_zkrat(predchozi + veta), index)
                predchozi = zbytek + "\n"
            else:
                predchozi += casti[i + 1] + "\n"
    return uryvky


def _veta_vysledku(text: str) -> tuple[str, str]:
    """Rozdělí text za odkazem na větu s výsledkem („hlasování číslo 274, přihlášeno…“) a zbytek."""
    konec = re.search(r"[.!?](\s|$)", text)
    if konec is None:
        return text.strip(), ""
    return text[: konec.end()].strip(), text[konec.end():]


def _zkrat(text: str) -> str:
    """Ořízne úryvek na posledních ``MAX_DELKA_URYVKU`` znaků, začne na hranici věty."""
    text = text.strip()
    if len(text) <= MAX_DELKA_URYVKU:
        return text
    ocas = text[-MAX_DELKA_URYVKU:]
    zacatek = re.search(r"[.!?]\s+|\n", ocas)
    return "… " + (ocas[zacatek.end():] if zacatek else ocas)


@dataclass(frozen=True)
class Predmet:
    """Rozpoznaný předmět hlasování.

    :param druh: ``pozmenovaci`` | ``celek`` | ``proceduralni`` | ``jine``
    :param oznaceni: označení pozměňovacího návrhu (``B2``, ``A1.3``) nebo ``None``
    :param otazka: věta, kterou předsedající hlasování uvedl (z textu úryvku), nebo ``None``
    """

    druh: str
    oznaceni: str | None
    otazka: str | None


# Označení návrhu: B, B2, A1.3, i výčet „A3, A4 a A6 až A13“ (za slovem návrh / bod).
_OZNACENI = r"[A-Z](?:\d+(?:\.\d+)*)?"
_POZMENOVACI = re.compile(
    r"(?:pozměňovací\w*\s+návrh\w*|návrh\w*|bod\w*)\s+(?:pod\s+(?:písmenem\s+)?)?"
    rf"({_OZNACENI}(?:\s*(?:,|a|až|-|–)\s*{_OZNACENI})*)(?![\wÁ-ž])")
_CELEK = re.compile(r"jako\s+celk|o\s+celém\s+návrhu|závěrečn\w+\s+hlasován|ve\s+znění\s+schválených",
                    re.IGNORECASE)
_PROCEDURALNI = re.compile(
    r"procedurální|přestávk|pauz|přeruš|pevn\w+\s+hlasován|námitk|zpochybn|po\s+21\.|po\s+19\."
    r"|pořad\w*\s+schůze|zkrácen\w+\s+lhůt|vrácení|zamítnutí\s+návrhu|lhůt\w+\s+k\s+projednání",
    re.IGNORECASE)
_UVOD_HLASOVANI = re.compile(
    r"[^.!?\n]*(?:hlasujeme|budeme\s+hlasovat|nechám\s+hlasovat|hlasovat\s+o|"
    r"kdo\s+souhlasí\s+s|o\s+návrhu|o\s+tomto\s+návrhu)[^.!?\n]*[.!?]?", re.IGNORECASE)
# Formule řízení hlasování, které o předmětu nic neříkají (při náhradní uvozující větě se vynechají).
_FORMULE = re.compile(
    r"^(?:návrh\s+(?:ne)?byl|hlasování\s+číslo|kdo\s+(?:je|souhlasí|nesouhlasí)|zmáčkne|"
    r"zvedne|děkuji|děkuju|prosím|tak\b|dobře|zahajuji)", re.IGNORECASE)
_VETA = re.compile(r"[^.!?\n]+[.!?]?")


def _bez_recnika(veta: str) -> str:
    """Odstraní ze začátku věty jméno řečníka („Předseda PSP Tomio Okamura: …“) a úvodní interpunkci."""
    veta = veta.split(":", 1)[1] if ":" in veta[:80] else veta
    return veta.lstrip(" )–-,;").strip()


def _nahradni_otazka(jadro: str) -> str | None:
    """Poslední až dvě věcné věty před zahájením hlasování (bez formulí typu „Kdo je pro?“)."""
    vety = [" ".join(_bez_recnika(v).split()) for v in _VETA.findall(jadro)]
    vecne = [v for v in vety if len(v) > 15 and not _FORMULE.match(v)]
    return " ".join(vecne[-2:]) or None


def rozpoznej_predmet(uryvek: str) -> Predmet:
    """Rozpozná z úryvku druh hlasování, označení návrhu a uvozující větu předsedajícího.

    Rozhoduje poslední část úryvku (od posledního „Zahajuji hlasování“, jinak posledních
    600 znaků) – starší text patří k předchozí debatě.
    """
    pred_vysledkem = uryvek.rsplit("\n", 1)[0] if "\n" in uryvek else uryvek
    jadro = pred_vysledkem[-600:]
    if (z := pred_vysledkem.lower().rfind("zahajuji hlasování")) != -1:
        jadro = pred_vysledkem[max(0, z - 600): z]

    otazky = _UVOD_HLASOVANI.findall(jadro)
    otazka = _bez_recnika(" ".join(otazky[-1].split())) if otazky else _nahradni_otazka(jadro)

    if m := _POZMENOVACI.search(jadro):
        return Predmet("pozmenovaci", " ".join(m.group(1).split()), otazka)
    if _CELEK.search(jadro):
        return Predmet("celek", None, otazka)
    if _PROCEDURALNI.search(jadro):
        return Predmet("proceduralni", None, otazka)
    return Predmet("jine", None, otazka)
