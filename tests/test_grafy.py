"""Testy rozmístění sedadel v půlkruhu sněmovny."""

from politika.web.grafy import POLOMER, rozlozeni_sedadel


def test_pocet_sedadel_sedi_i_pro_neokrouhla_cisla():
    for n in (0, 1, 7, 157, 200):
        assert len(rozlozeni_sedadel(n)) == n


def test_sedadla_jsou_zleva_doprava_a_uvnitr_puklkruhu():
    sedadla = rozlozeni_sedadel(200)
    assert sedadla[0].x < POLOMER < sedadla[-1].x
    assert all(0 <= s.x <= 2 * POLOMER and 0 <= s.y <= POLOMER for s in sedadla)
