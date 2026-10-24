"""Konfigurace aplikace – cesty k datům a zdroje otevřených dat.

Cesty jdou přepsat proměnnými prostředí (např. na domácím serveru):
- ``POLITIKA_DATA`` – kořenová složka dat (výchozí ``<projekt>/data``),
- ``POLITIKA_DB`` – soubor databáze (výchozí ``<data>/politika.db``).
"""

import os
from pathlib import Path

PROJEKT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("POLITIKA_DATA", PROJEKT_DIR / "data"))
OPENDATA_DIR = DATA_DIR / "opendata"
DB_PATH = Path(os.environ.get("POLITIKA_DB", DATA_DIR / "politika.db"))

OPENDATA_URL = "https://www.psp.cz/eknih/cdrom/opendata/"
# Volební období, jehož hlasování se importují (název ZIPu hl-{OBDOBI}.zip).
OBDOBI = "2025ps"
OPENDATA_SADY = ["poslanci", f"hl-{OBDOBI}", "schuze", "tisky", "steno", "sd"]

# Identifikace klienta vůči psp.cz (bez osobních údajů).
USER_AGENT = "politika-osobni-prehled/0.1"
# Pauza mezi požadavky na psp.cz v sekundách – šetrnost k serveru.
PAUZA_MEZI_POZADAVKY = 1.0
