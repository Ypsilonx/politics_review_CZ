"""Test výběru úseků stenozáznamu podle času hlasování (včetně hlasování po půlnoci)."""

from politika.db.connection import get_connection
from politika.dokumenty.steno import potrebne_useky


def test_useky_kolem_hlasovani_i_po_pulnoci(tmp_path):
    conn = get_connection(tmp_path / "t.db")
    conn.execute("INSERT INTO organ (id_organ, id_typ, od) VALUES (174, 11, '2025-10-04')")
    conn.executemany(  # (turn, datum začátku, od_t, do_t) – úsek 13 přes půlnoc
        "INSERT INTO steno (id_steno, id_organ, schuze, turn, datum, od_t, do_t) "
        "VALUES (?, 174, 34, ?, ?, ?, ?)",
        [(i, t, d, od, do) for i, (t, d, od, do) in enumerate([
            (1, "2026-10-23", 540, 550), (2, "2026-10-23", 550, 560), (3, "2026-10-23", 560, 570),
            (10, "2026-10-23", 1400, 1410), (11, "2026-10-23", 1410, 1420),
            (12, "2026-10-23", 1420, 1430), (13, "2026-10-23", 1430, 5),
            (14, "2026-10-24", 5, 15), (20, "2026-10-24", 600, 610)])],
    )
    conn.executemany(
        "INSERT INTO hlasovani (id_hlasovani, id_organ, schuze, cislo, datum, cas) "
        "VALUES (?, 174, 34, ?, ?, ?)",
        [(1, 1, "2026-10-23", "09:15"), (2, 2, "2026-10-24", "00:02")],
    )
    # 09:15 → úsek 2 a sousedé; 00:02 dalšího dne → úsek 13 (začal 23:50) a sousedé
    assert potrebne_useky(conn, 34) == [1, 2, 3, 12, 13, 14]
