"""Test importu otevřených dat na miniaturním snímku."""

from politika.db.connection import get_connection
from politika.importer.opendata import TABULKY, importuj_vse

# Jeden až dva řádky na soubor ve formátu PSP (schůze a bod i s řádkem pozvánky).
SNIMEK = {
    "poslanci/osoby.unl": "6743|Mgr.|Stržínek|Robert||23.11.1968|M|||\n",
    "poslanci/poslanec.unl": "2095|6743|593|1104|174||||||||||1|\n",
    "poslanci/organy.unl": "1750|174|1|ANO2011|Poslanecký klub ANO 2011|x|08.10.2025||1||\n",
    "poslanci/zarazeni.unl": "6743|1750|0|2025-10-08 00||||\n6743|99|1|2025-10-08 00||||\n",
    "schuze/schuze.unl": "897|174|34|2026-10-13 09||2026-10-01 10|1|\n"
                         "897|174|34|2026-10-13 09|2026-10-23 23|2026-10-23 23||\n",
    "schuze/bod_schuze.unl": "59435|897|43353|1|34|Novela|/st 231/||1|1|0||0||ČT|\n"
                             "59435|897|43353|1|34|Novela|/st 231/||7||0||0||o ČT|\n",
    "tisky/tisky.unl": "43353|1|12|231|0|1||174||ministr|Novela|19.06.2026|19.06.2026|"
                       "23:59||Úplný název|||||||||\n",
    "hl-2025ps/hl2025s.unl": "88870|174|34|281|34|23.10.2026|23:28|148|0|7|4|159|80|N|A|"
                             "Novela||\n",
    "hl-2025ps/hl2025h1.unl": "2095|88870|A|\n",
    "hl-2025ps/hl2025h2.unl": "",
}


def test_import_je_idempotentni_a_bere_schvaleny_porad(tmp_path):
    for t in TABULKY:  # ostatní tabulky snímku prázdné
        if "*" not in t.soubor:
            (tmp_path / t.soubor).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / t.soubor).write_bytes(b"")
    for soubor, obsah in SNIMEK.items():
        cesta = tmp_path / soubor
        cesta.parent.mkdir(parents=True, exist_ok=True)
        cesta.write_bytes(obsah.encode("cp1250"))
    conn = get_connection(tmp_path / "t.db")

    prvni = importuj_vse(conn, tmp_path)
    druhy = importuj_vse(conn, tmp_path)

    assert prvni == druhy
    assert prvni["zarazeni"] == 1  # řádek funkce se neimportuje
    radek = conn.execute("SELECT do, zkratka FROM schuze JOIN bod USING (id_schuze)").fetchone()
    assert tuple(radek) == ("2026-10-23", "o ČT")
    h = conn.execute("SELECT datum, vysledek FROM hlasovani").fetchone()
    assert tuple(h) == ("2026-10-23", "A")
