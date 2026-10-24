"""Výpočty pro grafy vykreslované v šablonách jako SVG (bez JS knihovny)."""

import math
from dataclasses import dataclass

# Rozměry půlkruhu v jednotkách SVG viewBoxu (šířka 2 × POLOMER, výška POLOMER).
POLOMER = 100.0
VNITRNI_POMER = 0.5  # vnitřní poloměr jako podíl vnějšího – prázdný střed půlkruhu
RADY = 8


@dataclass
class Sedadlo:
    """Jedno sedadlo v půlkruhu: střed (x, y) a poloměr tečky v jednotkách viewBoxu."""

    x: float
    y: float
    r: float


def rozlozeni_sedadel(pocet: int, rady: int = RADY) -> list[Sedadlo]:
    """Rozmístí ``pocet`` sedadel do soustředných oblouků jako ve sněmovním sále.

    Počet sedadel v řadě je úměrný délce oblouku. Sedadla jsou seřazená podle úhlu
    zleva doprava, takže když se po sobě přiřadí poslanci jednoho klubu, vytvoří klín.

    :param pocet: počet sedadel (poslanců v hlasování)
    :param rady: počet řad oblouků
    :return: seznam sedadel seřazený zleva doprava
    """
    if pocet == 0:
        return []
    polomery = [POLOMER * (VNITRNI_POMER + (1 - VNITRNI_POMER) * (i + 0.5) / rady)
                for i in range(rady)]
    celkem = sum(polomery)
    v_rade = [round(pocet * p / celkem) for p in polomery]
    v_rade[-1] += pocet - sum(v_rade)  # zaokrouhlovací rozdíl do vnější (nejdelší) řady
    r_tecky = POLOMER * (1 - VNITRNI_POMER) / rady * 0.42

    sedadla: list[tuple[float, Sedadlo]] = []
    for p, n in zip(polomery, v_rade):
        for j in range(n):
            uhel = math.pi * (1 - (j + 0.5) / n)  # π (vlevo) → 0 (vpravo)
            sedadla.append((uhel, Sedadlo(POLOMER + p * math.cos(uhel),
                                          POLOMER - p * math.sin(uhel), r_tecky)))
    sedadla.sort(key=lambda s: -s[0])
    return [s for _, s in sedadla]
