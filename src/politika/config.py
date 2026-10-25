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
OPENDATA_SADY = ["poslanci", f"hl-{OBDOBI}", "schuze", "tisky", "steno", "sd", "sbirka"]

# Identifikace klienta vůči psp.cz. Kontakt (e-mail) se bere jen z proměnné prostředí
# POLITIKA_KONTAKT, aby se osobní údaj nedostal do repozitáře; správce serveru pak ví, komu napsat.
KONTAKT = os.environ.get("POLITIKA_KONTAKT", "").strip()
USER_AGENT = "politika-osobni-prehled/0.1" + (f" (+mailto:{KONTAKT})" if KONTAKT else "")
# Pauza mezi požadavky na psp.cz v sekundách – šetrnost k serveru.
PAUZA_MEZI_POZADAVKY = 1.0
# Dokumenty z psp.cz se stahují jen v noci (hodina od, hodina do; přes půlnoc), mimo okno
# jen s --ihned. Šetří server ve špičce; nedokončené stažení pokračuje další noc.
NOCNI_OKNO = (22, 6)
# Tlačítko „Aktualizovat“ stahuje i přes den schůze s hlasováním za posledních tolik dní.
DNY_CERSTVYCH = 7
# Tlačítko „Aktualizovat“ jde použít jednou za den; nový den začíná v tuto hodinu
# (0 = o půlnoci, 2 = ve 2:00). Chrání psp.cz před opakovaným klikáním.
ZACATEK_DNE_AKTUALIZACE = 2
