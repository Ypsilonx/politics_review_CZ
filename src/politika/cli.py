"""Příkazová řádka aplikace (``uv run politika <příkaz>``)."""

import argparse

from politika import config
from politika.db.connection import get_connection
from politika.importer.opendata import importuj_vse, stahni_opendata


def cmd_import(args: argparse.Namespace) -> None:
    """Stáhne otevřená data (pokud není ``--bez-stazeni``) a naimportuje je do DB."""
    if not args.bez_stazeni:
        stahni_opendata(config.OPENDATA_DIR, config.OPENDATA_SADY)
    from politika.analyza.predpocet import prepocitej

    conn = get_connection(config.DB_PATH)
    pocty = importuj_vse(conn, config.OPENDATA_DIR) | prepocitej(conn)
    for tabulka, pocet in pocty.items():
        print(f"{tabulka:<16} {pocet:>8}")
    conn.close()


def cmd_stahni_dokumenty(args: argparse.Namespace) -> None:
    """Stáhne stenozáznamy, soubory tisků, kanceláře a fotky (bez parametrů vše pro celé období).

    Pořadí: nejdřív malé věci (kanceláře, fotky), pak schůze od nejnovější – aby čerstvá
    data byla k dispozici co nejdřív i při prvním dlouhém běhu.
    """
    from politika.dokumenty.foto import stahni_fotky
    from politika.dokumenty.kancelare import obnov_kancelare
    from politika.dokumenty.stahovani import Stahovac
    from politika.dokumenty.steno import schuze_obdobi, stahni_steno_schuze
    from politika.dokumenty.tisky import stahni_soubory_tisku, tisky_obdobi

    conn = get_connection(config.DB_PATH)
    vse = not (args.schuze or args.tisk or args.kancelare or args.fotky)
    schuze = args.schuze or (sorted(schuze_obdobi(conn), reverse=True) if vse else [])
    tisky = [(ct, True) for ct in args.tisk] if args.tisk else (
        sorted(tisky_obdobi(conn), key=lambda t: not t[1]) if vse else [])
    with Stahovac() as st:
        if vse or args.kancelare:
            print(f"kanceláře: {obnov_kancelare(conn, st)}", flush=True)
        if vse or args.fotky:
            print(f"fotky: {stahni_fotky(conn, st)} nových", flush=True)
        for s in schuze:
            print(f"schůze {s}: {stahni_steno_schuze(conn, st, s)} úseků", flush=True)
        for ct, aktivni in tisky:
            print(f"tisk {ct}: {stahni_soubory_tisku(conn, st, ct, aktivni)} souborů", flush=True)
        print(f"požadavků na psp.cz: {st.pocet_pozadavku}")
    conn.close()


def cmd_paruj(args: argparse.Namespace) -> None:
    """Spáruje hlasování se stenozáznamem (bez parametrů všechny schůze aktuálního období)."""
    from politika.dokumenty.steno import schuze_obdobi
    from politika.parovani.sluzba import paruj_schuzi

    conn = get_connection(config.DB_PATH)
    for s in args.schuze or schuze_obdobi(conn):
        v = paruj_schuzi(conn, s)
        print(f"schůze {s}: {v.s_uryvkem}/{v.hlasovani} hlasování s předmětem, "
              f"{v.s_dokumentem} s dokumentem návrhů")
    conn.close()


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
    p = sub.add_parser("stahni-dokumenty", help="stáhnout stenozáznamy a soubory tisků z psp.cz")
    p.add_argument("--schuze", type=int, nargs="*", default=[], help="jen tyto schůze")
    p.add_argument("--tisk", type=int, nargs="*", default=[], help="jen tyto tisky (čísla)")
    p.add_argument("--kancelare", action="store_true", help="jen mapa regionálních kanceláří")
    p.add_argument("--fotky", action="store_true", help="jen fotky poslanců")
    p.set_defaults(func=cmd_stahni_dokumenty)
    p = sub.add_parser("paruj", help="najít předmět hlasování ve stenozáznamech")
    p.add_argument("--schuze", type=int, nargs="*", default=[], help="jen tyto schůze")
    p.set_defaults(func=cmd_paruj)
    p = sub.add_parser("web", help="spustit webové rozhraní")
    # 127.0.0.1 = jen tento počítač; na domácím serveru --host 0.0.0.0 (celá domácí síť).
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true", help="restart při změně kódu (vývoj)")
    p.set_defaults(func=cmd_web)
    args = parser.parse_args()
    args.func(args)
