"""Příkazová řádka aplikace (``uv run politika <příkaz>``)."""

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from politika import config
from politika.analyza.predpocet import prepocitej
from politika.db.connection import get_connection
from politika.dokumenty.foto import stahni_fotky
from politika.dokumenty.kancelare import obnov_kancelare
from politika.dokumenty.stahovani import MimoNocniOkno, Stahovac, v_nocnim_okne
from politika.dokumenty.steno import cerstve_schuze, schuze_obdobi, stahni_steno_schuze
from politika.dokumenty.tisky import stahni_odkazy_tisku, tisky_obdobi, tisky_schuzi
from politika.importer.opendata import importuj_vse, stahni_opendata
from politika.parovani.sluzba import paruj_schuzi


class Prubeh:
    """Spouští dílčí kroky dlouhého běhu: chybu kroku vypíše a pokračuje dalším krokem.

    Volitelně zapisuje stav (fáze, krok X z N) do JSON souboru, ze kterého web kreslí průběh.
    """

    def __init__(self, soubor_stavu: Path | None = None, faze_celkem: int = 1) -> None:
        """:param soubor_stavu: kam zapisovat stav po každé změně; ``None`` = nikam
        :param faze_celkem: kolik fází (``faze()``) běh bude mít
        """
        self.chyb = 0
        self._soubor = soubor_stavu
        self._stav = {"faze": "", "faze_cislo": 0, "faze_celkem": faze_celkem,
                      "hotovo": 0, "celkem": 0, "krok": ""}

    def _zapis(self) -> None:
        """Zapíše stav do souboru (je-li zadán)."""
        if self._soubor is not None:
            self._soubor.write_text(json.dumps(self._stav, ensure_ascii=False), encoding="utf-8")

    def faze(self, nazev: str, kroku: int) -> None:
        """Začne další fázi běhu, která bude mít ``kroku`` kroků."""
        self._stav |= {"faze": nazev, "faze_cislo": self._stav["faze_cislo"] + 1,
                       "hotovo": 0, "celkem": kroku, "krok": ""}
        self._zapis()

    def krok(self, popis: str, funkce: Callable[[], object]) -> None:
        """Provede krok a vypíše ``popis: výsledek``; jakoukoli chybu kroku zapíše a pokračuje.

        Chytá se záměrně vše (i chyby parsování změněné stránky psp.cz) – jeden vadný tisk
        nebo schůze nesmí zastavit obnovu ostatních. Celý běh pak skončí s kódem 1.
        """
        # popis je psaný pro výpis výsledku („schůze 34, úseků: 12“) – do průběhu jen „schůze 34“
        self._stav["krok"] = popis.partition(",")[0]
        self._zapis()
        try:
            print(f"{popis}: {funkce()}", flush=True)
        except MimoNocniOkno:
            raise  # konec nočního okna ukončuje celé stahování, není to chyba kroku
        except Exception as chyba:  # noqa: BLE001 – viz docstring
            self.chyb += 1
            print(f"{popis}: CHYBA {type(chyba).__name__}: {chyba}", flush=True)
        self._stav["hotovo"] += 1
        self._zapis()


def _importuj(stahnout: bool) -> dict[str, int]:
    """Stáhne (volitelně) a naimportuje otevřená data a přepočítá statistiky."""
    if stahnout:
        stahni_opendata(config.OPENDATA_DIR, config.OPENDATA_SADY)
    conn = get_connection(config.DB_PATH)
    try:
        return importuj_vse(conn, config.OPENDATA_DIR) | prepocitej(conn)
    finally:
        conn.close()


def _stahni_dokumenty(prubeh: Prubeh, schuze: list[int], tisky: list[int],
                      kancelare: bool, fotky: bool, ihned: bool,
                      cerstve_ihned: bool = False) -> None:
    """Stáhne stenozáznamy, stránky tisků, kanceláře a fotky; bez výběru vše pro celé období.

    Pořadí: nejdřív čerstvé schůze a jejich tisky, pak malé věci (kanceláře, fotky), pak
    starší schůze od nejnovější a aktivní tisky – aby čerstvá data byla k dispozici co nejdřív.

    :param ihned: stahovat i mimo noční okno (``config.NOCNI_OKNO``); jinak se na jeho konci
        stahování ukončí a zbytek dostáhne další běh
    :param cerstve_ihned: mimo okno stáhnout aspoň čerstvé schůze (``config.DNY_CERSTVYCH``)
        a jejich tisky – tlačítko „Aktualizovat“ ve webu
    """
    conn = get_connection(config.DB_PATH)
    vse = not (schuze or tisky or kancelare or fotky)
    vybrane_schuze = schuze or (sorted(schuze_obdobi(conn), reverse=True) if vse else [])
    vybrane_tisky = [(ct, True) for ct in tisky] if tisky else (
        sorted(tisky_obdobi(conn), key=lambda t: not t[1]) if vse else [])
    cerstve_s = cerstve_schuze(conn, config.DNY_CERSTVYCH) if cerstve_ihned else set()
    cerstve_t = tisky_schuzi(conn, cerstve_s)

    # (popis, funkce, čerstvé = smí i mimo noční okno); čerstvé napřed, protože konec okna
    # ukončí celý zbytek běhu
    kroky: list[tuple[str, Callable[[Stahovac], object], bool]] = []
    for s in vybrane_schuze:
        kroky.append((f"schůze {s}, úseků",
                      lambda st, s=s: stahni_steno_schuze(conn, st, s), s in cerstve_s))
    for ct, aktivni in vybrane_tisky:
        kroky.append((f"tisk {ct}, odkazů",
                      lambda st, ct=ct, a=aktivni: stahni_odkazy_tisku(conn, st, ct, a),
                      ct in cerstve_t))
    if vse or fotky:
        kroky.insert(0, ("nové fotky", lambda st: stahni_fotky(conn, st), False))
    if vse or kancelare:
        kroky.insert(0, ("kanceláře", lambda st: obnov_kancelare(conn, st), False))
    kroky.sort(key=lambda k: not k[2])  # stabilní řazení: jinak zůstává pořadí výše
    # Mimo noční okno by ostatní kroky skončily na prvním požadavku (MimoNocniOkno); vynechat
    # je předem, ať průběh ve webu ukazuje počet kroků, které opravdu poběží.
    if not (ihned or v_nocnim_okne()):
        odlozenych = sum(not k[2] for k in kroky)
        kroky = [k for k in kroky if k[2]]
        if odlozenych:
            od, do = config.NOCNI_OKNO
            print(f"mimo noční okno ({od}–{do} h): {odlozenych} kroků se stáhne příští noc "
                  "(hned: --ihned)", flush=True)
    prubeh.faze("Stahování z psp.cz", len(kroky))

    with Stahovac() as st:
        try:
            for popis, funkce, cerstvy in kroky:
                st.jen_v_noci = not (ihned or cerstvy)
                prubeh.krok(popis, lambda f=funkce: f(st))
        except MimoNocniOkno:
            od, do = config.NOCNI_OKNO
            print(f"mimo noční okno ({od}–{do} h): zbytek se stáhne příští noc "
                  "(hned: --ihned)", flush=True)
        print(f"požadavků na psp.cz: {st.pocet_pozadavku}")
    conn.close()


def _paruj(prubeh: Prubeh, schuze: list[int]) -> None:
    """Spáruje hlasování se stenozáznamem (bez výběru všechny schůze aktuálního období)."""
    conn = get_connection(config.DB_PATH)

    def jedna(s: int) -> str:
        """Spáruje jednu schůzi a vrátí souhrn pro výpis."""
        v = paruj_schuzi(conn, s)
        return (f"{v.s_uryvkem}/{v.hlasovani} hlasování s předmětem, "
                f"{v.s_dokumentem} s dokumentem návrhů")

    vybrane = schuze or schuze_obdobi(conn)
    prubeh.faze("Párování se stenozáznamy", len(vybrane))
    for s in vybrane:
        prubeh.krok(f"párování schůze {s}", lambda s=s: jedna(s))
    conn.close()


def cmd_import(args: argparse.Namespace) -> None:
    """Stáhne otevřená data (pokud není ``--bez-stazeni``) a naimportuje je do DB."""
    for tabulka, pocet in _importuj(not args.bez_stazeni).items():
        print(f"{tabulka:<16} {pocet:>8}")


def cmd_stahni_dokumenty(args: argparse.Namespace) -> None:
    """Stáhne dokumenty z psp.cz; při chybách skončí s kódem 1."""
    prubeh = Prubeh()
    _stahni_dokumenty(prubeh, args.schuze, args.tisk, args.kancelare, args.fotky, args.ihned)
    sys.exit(1 if prubeh.chyb else 0)


def cmd_paruj(args: argparse.Namespace) -> None:
    """Spáruje hlasování se stenozáznamem."""
    prubeh = Prubeh()
    _paruj(prubeh, args.schuze)
    sys.exit(1 if prubeh.chyb else 0)


def cmd_obnova(args: argparse.Namespace) -> None:
    """Denní obnova: import otevřených dat → stažení nových dokumentů → párování.

    Skončí s kódem 1, pokud některý krok selhal (Plánovač úloh / cron to zaznamená).
    """
    prubeh = Prubeh(config.STAV_OBNOVY, faze_celkem=3)
    prubeh.faze("Otevřená data (stažení a import)", 1)
    prubeh.krok("import otevřených dat", lambda: sum(_importuj(stahnout=True).values()))
    _stahni_dokumenty(prubeh, [], [], kancelare=False, fotky=False, ihned=args.ihned,
                      cerstve_ihned=args.cerstve_ihned)
    _paruj(prubeh, [])
    sys.exit(1 if prubeh.chyb else 0)


def cmd_web(args: argparse.Namespace) -> None:
    """Spustí webové rozhraní (uvicorn)."""
    import uvicorn

    uvicorn.run("politika.web.app:create_app", factory=True, host=args.host, port=args.port,
                reload=args.reload)


IHNED_HELP = "stahovat z psp.cz i mimo noční okno (config.NOCNI_OKNO)"


def main() -> None:
    """Vstupní bod CLI."""
    parser = argparse.ArgumentParser(prog="politika")
    sub = parser.add_subparsers(required=True)
    p = sub.add_parser("import", help="stáhnout a naimportovat otevřená data PSP")
    p.add_argument("--bez-stazeni", action="store_true", help="použít už stažená data")
    p.set_defaults(func=cmd_import)
    p = sub.add_parser("stahni-dokumenty",
                       help="stáhnout stenozáznamy, stránky tisků, kanceláře a fotky z psp.cz")
    p.add_argument("--schuze", type=int, nargs="*", default=[], help="jen tyto schůze")
    p.add_argument("--tisk", type=int, nargs="*", default=[], help="jen tyto tisky (čísla)")
    p.add_argument("--kancelare", action="store_true", help="jen mapa regionálních kanceláří")
    p.add_argument("--fotky", action="store_true", help="jen fotky poslanců")
    p.add_argument("--ihned", action="store_true", help=IHNED_HELP)
    p.set_defaults(func=cmd_stahni_dokumenty)
    p = sub.add_parser("paruj", help="najít předmět hlasování ve stenozáznamech")
    p.add_argument("--schuze", type=int, nargs="*", default=[], help="jen tyto schůze")
    p.set_defaults(func=cmd_paruj)
    p = sub.add_parser("obnova", help="denní obnova: import, dokumenty, párování")
    p.add_argument("--ihned", action="store_true", help=IHNED_HELP)
    p.add_argument("--cerstve-ihned", action="store_true",
                   help="mimo noční okno stáhnout aspoň schůze z posledních dní (config.DNY_CERSTVYCH)")
    p.set_defaults(func=cmd_obnova)
    p = sub.add_parser("web", help="spustit webové rozhraní")
    # 127.0.0.1 = jen tento počítač; na domácím serveru --host 0.0.0.0 (celá domácí síť).
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true", help="restart při změně kódu (vývoj)")
    p.set_defaults(func=cmd_web)
    args = parser.parse_args()
    args.func(args)
