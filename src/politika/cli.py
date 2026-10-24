"""Příkazová řádka aplikace (``uv run politika <příkaz>``)."""

import argparse

from politika import config
from politika.db.connection import get_connection
from politika.importer.opendata import importuj_vse, stahni_opendata


def cmd_import(args: argparse.Namespace) -> None:
    """Stáhne otevřená data (pokud není ``--bez-stazeni``) a naimportuje je do DB."""
    if not args.bez_stazeni:
        stahni_opendata(config.OPENDATA_DIR, config.OPENDATA_SADY)
    conn = get_connection(config.DB_PATH)
    for tabulka, pocet in importuj_vse(conn, config.OPENDATA_DIR).items():
        print(f"{tabulka:<10} {pocet:>8}")
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
    p = sub.add_parser("web", help="spustit webové rozhraní")
    # 127.0.0.1 = jen tento počítač; na domácím serveru --host 0.0.0.0 (celá domácí síť).
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true", help="restart při změně kódu (vývoj)")
    p.set_defaults(func=cmd_web)
    args = parser.parse_args()
    args.func(args)
