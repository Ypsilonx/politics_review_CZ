"""Test denního limitu tlačítka „Aktualizovat“ (hranice dne v nastavitelnou hodinu)."""

from datetime import datetime

from politika.web.routes.aktualizace import dalsi_mozna


def test_odpoledni_beh_uvolni_rano_dalsiho_dne():
    assert dalsi_mozna(datetime(2026, 10, 25, 15, 0), 2) == datetime(2026, 10, 26, 2, 0)


def test_beh_po_pulnoci_pred_zacatkem_dne_patri_k_predchozimu_dni():
    assert dalsi_mozna(datetime(2026, 10, 26, 1, 0), 2) == datetime(2026, 10, 26, 2, 0)


def test_zacatek_dne_o_pulnoci():
    assert dalsi_mozna(datetime(2026, 10, 25, 23, 59), 0) == datetime(2026, 10, 26, 0, 0)
