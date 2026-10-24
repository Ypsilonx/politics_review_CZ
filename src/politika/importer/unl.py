"""Parsování souborů UNL z otevřených dat PSP.

Formát: jeden záznam na řádek, pole oddělená ``|``, každý řádek končí ``|``,
kódování Windows-1250. Prázdné pole znamená chybějící hodnotu.
"""

from collections.abc import Iterator
from pathlib import Path


def parse_unl(path: Path, columns: list[str]) -> Iterator[dict[str, str | None]]:
    """Načte UNL soubor a vrací záznamy jako slovníky podle zadaných názvů sloupců.

    :param path: cesta k souboru ``.unl``
    :param columns: názvy sloupců v pořadí, v jakém jsou v souboru
    :return: iterátor slovníků ``{sloupec: hodnota}``, prázdné pole je ``None``
    :raises ValueError: když počet polí na řádku neodpovídá ``columns``
    """
    with path.open(encoding="cp1250", newline="") as f:
        for cislo_radku, radek in enumerate(f, start=1):
            radek = radek.rstrip("\r\n")
            if not radek:
                continue
            pole = radek.split("|")
            if pole[-1] == "":
                pole.pop()  # koncový oddělovač
            if len(pole) != len(columns):
                raise ValueError(
                    f"{path.name}:{cislo_radku}: čekáno {len(columns)} polí, nalezeno {len(pole)}"
                )
            yield {k: (v if v != "" else None) for k, v in zip(columns, pole)}
