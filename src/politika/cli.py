"""Příkazová řádka aplikace (``uv run politika <příkaz>``)."""

import argparse
import sqlite3
import sys
from collections.abc import Callable

import httpx

from politika import config
from politika.analyza.predpocet import prepocitej
from politika.db.connection import get_connection
from politika.dokumenty.foto import stahni_fotky
from politika.dokumenty.kancelare import obnov_kancelare
from politika.dokumenty.stahovani import Stahovac
from politika.dokumenty.steno import schuze_obdobi, stahni_steno_schuze
from politika.dokumenty.tisky import stahni_soubory_tisku, tisky_obdobi
from politika.importer.opendata import importuj_vse, stahni_opendata
from politika.parovani.sluzba import paruj_schuzi


class Prubeh:
    """Spouští dílčí kroky dlouhého běhu: chybu kroku vypíše a pokračuje dalším krokem."""

    def __init__(self) -> None:
        self.chyb = 0

    def krok(self, popis: str, funkce: Callable[[], object]) -> None:
        """Provede krok a vypíše ``popis: výsledek``; síťová chyba nebo chyba souboru se jen zapíše."""
        try:
            print(f"{popis}: {funkce()}", flush=True)
        except (httpx.HTTPError, OSError, sqlite3.OperationalError) as chyba:
            self.chyb += 1
            print(f"{popis}: CHYBA {type(chyba).__name__}: {chyba}", flush=True)


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
                      kancelare: bool, fotky: bool) -> None:
    """Stáhne stenozáznamy, soubory tisků, kanceláře a fotky; bez výběru vše pro celé období.

    Pořadí: nejdřív malé věci (kanceláře, fotky), pak schůze od nejnovější a aktivní tisky –
    aby čerstvá data byla k dispozici co nejdřív i při prvním dlouhém běhu.
    """
    conn = get_connection(config.DB_PATH)
    vse = not (schuze or tisky or kancelare or fotky)
    vybrane_schuze = schuze or (sorted(schuze_obdobi(conn), reverse=True) if vse else [])
    vybrane_tisky = [(ct, True) for ct in tisky] if tisky else (
        sorted(tisky_obdobi(conn), key=lambda t: not t[1]) if vse else [])
    with Stahovac() as st:
        if vse or kancelare:
            prubeh.krok("kanceláře", lambda: obnov_kancelare(conn, st))
        if vse or fotky:
            prubeh.krok("nové fotky", lambda: stahni_fotky(conn, st))
        for s in vybrane_schuze:
            prubeh.krok(f"schůze {s}, úseků", lambda s=s: stahni_steno_schuze(conn, st, s))
        for ct, aktivni in vybrane_tisky:
            prubeh.krok(f"tisk {ct}, souborů",
                        lambda ct=ct, aktivni=aktivni: stahni_soubory_tisku(conn, st, ct, aktivni))
        print(f"požadavků na psp.cz: {st.pocet_pozadavku}")
    conn.close()


def _paruj(schuze: list[int]) -> None:
    """Spáruje hlasování se stenozáznamem (bez výběru všechny schůze aktuálního období)."""
    conn = get_connection(config.DB_PATH)
    for s in schuze or schuze_obdobi(conn):
        v = paruj_schuzi(conn, s)
        print(f"schůze {s}: {v.s_uryvkem}/{v.hlasovani} hlasování s předmětem, "
              f"{v.s_dokumentem} s dokumentem návrhů")
    conn.close()


def cmd_import(args: argparse.Namespace) -> None:
    """Stáhne otevřená data (pokud není ``--bez-stazeni``) a naimportuje je do DB."""
    for tabulka, pocet in _importuj(not args.bez_stazeni).items():
        print(f"{tabulka:<16} {pocet:>8}")


def cmd_stahni_dokumenty(args: argparse.Namespace) -> None:
    """Stáhne dokumenty z psp.cz; při chybách skončí s kódem 1."""
    prubeh = Prubeh()
    _stahni_dokumenty(prubeh, args.schuze, args.tisk, args.kancelare, args.fotky)
    sys.exit(1 if prubeh.chyb else 0)


def cmd_paruj(args: argparse.Namespace) -> None:
    """Spáruje hlasování se stenozáznamem."""
    _paruj(args.schuze)


def cmd_obnova(args: argparse.Namespace) -> None:
    """Denní obnova: import otevřených dat → stažení nových dokumentů → párování.

    Skončí s kódem 1, pokud některý krok selhal (Plánovač úloh / cron to zaznamená).
    """
    prubeh = Prubeh()
    prubeh.krok("import otevřených dat", lambda: sum(_importuj(stahnout=True).values()))
    _stahni_dokumenty(prubeh, [], [], kancelare=False, fotky=False)
    _paruj([])
    sys.exit(1 if prubeh.chyb else 0)


def cmd_web(args: argparse.Namespace) -> None:
    """Spustí webové rozhraní (uvicorn)."""
    import uvicorn

    uvicorn.run("politika.web.app:create_app", factory=True, host=args.host, port=args.port,
                reload=args.reload)


def main() -> None:
    """Vstupní bod CLI."""
    parser = argparse.ArgumentParser(prog="politika")
    sub = parser.add_subparsers(required=True)
    p = sub.add_parser("import", help="stáhnout a naimportovat otevřená data PSP")
    p.add_argument("--bez-stazeni", action="store_true", help="použít už stažená data")
    p.set_defaults(func=cmd_import)
    p = sub.add_parser("stahni-dokumenty",
                       help="stáhnout stenozáznamy, soubory tisků, kanceláře a fotky z psp.cz")
    p.add_argument("--schuze", type=int, nargs="*", default=[], help="jen tyto schůze")
    p.add_argument("--tisk", type=int, nargs="*", default=[], help="jen tyto tisky (čísla)")
    p.add_argument("--kancelare", action="store_true", help="jen mapa regionálních kanceláří")
    p.add_argument("--fotky", action="store_true", help="jen fotky poslanců")
    p.set_defaults(func=cmd_stahni_dokumenty)
    p = sub.add_parser("paruj", help="najít předmět hlasování ve stenozáznamech")
    p.add_argument("--schuze", type=int, nargs="*", default=[], help="jen tyto schůze")
    p.set_defaults(func=cmd_paruj)
    p = sub.add_parser("obnova", help="denní obnova: import, dokumenty, párování")
    p.set_defaults(func=cmd_obnova)
    p = sub.add_parser("web", help="spustit webové rozhraní")
    # 127.0.0.1 = jen tento počítač; na domácím serveru --host 0.0.0.0 (celá domácí síť).
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true", help="restart při změně kódu (vývoj)")
    p.set_defaults(func=cmd_web)
    args = parser.parse_args()
    args.func(args)
