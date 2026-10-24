"""Test nočního okna stahování (okno přes půlnoc)."""

from datetime import datetime

from politika.dokumenty.stahovani import v_nocnim_okne


def test_okno_pres_pulnoc():
    den = datetime(2026, 10, 24)
    assert [h for h in range(24) if v_nocnim_okne(den.replace(hour=h))] == [0, 1, 2, 3, 4, 5, 22, 23]
