"""Testy předpočtu a statistik na malé ručně sestavené databázi."""

import pytest

from politika.analyza.predpocet import prepocitej
from politika.analyza.statistiky import dochazka, jednota_klubu, pocet_proti_klubu, shoda_klubu
from politika.db.connection import get_connection

PS, KLUB_X, KLUB_Y = 174, 1, 2


@pytest.fixture
def conn(tmp_path):
    """Sněmovna se dvěma kluby; poslanec 3 přejde 1. 2. 2026 z klubu X do Y."""
    c = get_connection(tmp_path / "t.db")
    c.executemany("INSERT INTO organ (id_organ, id_nadrazeny, id_typ, zkratka, od) VALUES (?,?,?,?,?)",
                  [(PS, None, 11, "PSP10", "2025-10-04"), (KLUB_X, PS, 1, "X", "2025-10-05"),
                   (KLUB_Y, PS, 1, "Y", "2025-10-05")])
    for i in range(1, 6):
        c.execute("INSERT INTO osoba (id_osoba, prijmeni, jmeno) VALUES (?, ?, 'P')", (i, f"P{i}"))
        c.execute("INSERT INTO poslanec (id_poslanec, id_osoba, id_obdobi) VALUES (?, ?, ?)",
                  (i, i, PS))
    c.executemany("INSERT INTO zarazeni (id_osoba, id_organ, od, do) VALUES (?,?,?,?)", [
        (1, KLUB_X, "2025-10-05", None), (2, KLUB_X, "2025-10-05", None),
        (3, KLUB_X, "2025-10-05", "2026-01-31"), (3, KLUB_Y, "2026-02-01", None),
        (4, KLUB_Y, "2025-10-05", None), (5, KLUB_Y, "2025-10-05", None),
    ])
    hlasovani = {  # id: (datum, hlasy poslanců 1–5)
        1: ("2026-01-10", "AABBB"),   # X: A,A,B → 3 proti klubu; Y: B,B
        2: ("2026-03-10", "AAABA"),   # 3 už v Y: Y = A,B,A → 4 proti klubu
        3: ("2026-03-11", "AB@AB"),   # X remíza (nepočítá se); 3 nepřihlášen, ale omluven
        4: ("2026-03-12", "AA@BB"),   # 3 nepřihlášen bez omluvy
    }
    for id_h, (datum, hlasy) in hlasovani.items():
        c.execute("INSERT INTO hlasovani (id_hlasovani, id_organ, schuze, cislo, datum, cas) "
                  "VALUES (?, ?, 1, ?, ?, '10:00')", (id_h, PS, id_h, datum))
        c.executemany("INSERT INTO hlas VALUES (?, ?, ?)",
                      [(i + 1, id_h, h) for i, h in enumerate(hlasy)])
    c.execute("INSERT INTO omluva VALUES (?, 3, '2026-03-11', NULL, NULL)", (PS,))
    c.commit()
    prepocitej(c)
    return c


def test_proti_klubu_bere_klub_k_datu_a_ignoruje_remizu(conn):
    assert pocet_proti_klubu(conn, 3) == 1   # hlasování 1 v klubu X
    assert pocet_proti_klubu(conn, 4) == 1   # hlasování 2 v klubu Y
    assert pocet_proti_klubu(conn, 2) == 0   # v hlasování 3 je klub X nerozhodně


def test_dochazka_rozlisi_omluvene(conn):
    d = dochazka(conn, 3)
    assert (d.celkem, d.pritomen, d.omluven, d.neomluven) == (4, 2, 1, 1)
    assert d.procento == 50


def test_jednota_a_shoda_klubu(conn):
    jednota = {k["zkratka"]: k["jednota"] for k in jednota_klubu(conn)}
    # klub X: hlasování 1 (2 ze 3 s většinou), 2 (2/2), 3 remíza – vynechá se, 4 (2/2) → 6/7
    assert jednota["X"] == pytest.approx(100 * 6 / 7)
    kluby, shoda = shoda_klubu(conn)
    assert shoda[("X", "X")] == 100
