"""Testy parseru UNL."""

import pytest

from politika.importer.unl import parse_unl


def _zapis(tmp_path, text: str):
    """Zapíše text v kódování Windows-1250 (jako PSP) a vrátí cestu."""
    p = tmp_path / "t.unl"
    p.write_bytes(text.encode("cp1250"))
    return p


def test_diakritika_koncovy_oddelovac_a_prazdne_pole(tmp_path):
    p = _zapis(tmp_path, "6743|Mgr.|Stržínek|Robert||\r\n7114||Jíra|Jakub||\r\n")
    radky = list(parse_unl(p, ["id", "pred", "prijmeni", "jmeno", "za"]))
    assert radky[0] == {"id": "6743", "pred": "Mgr.", "prijmeni": "Stržínek",
                        "jmeno": "Robert", "za": None}
    assert radky[1]["pred"] is None


def test_spatny_pocet_poli(tmp_path):
    p = _zapis(tmp_path, "1|2|3|\n")
    with pytest.raises(ValueError, match="t.unl:1"):
        list(parse_unl(p, ["a", "b"]))
