"""Párování celé schůze: úseky stenozáznamu → úryvky → předmět → dokument návrhu → DB."""

import sqlite3
from dataclasses import dataclass, replace

from politika import config
from politika.db.dotazy.spolecne import aktualni_obdobi
from politika.dokumenty.stahovani import precti_html
from politika.parovani.navrhy import dokument_navrhu
from politika.parovani.steno import rozpoznej_predmet, usek_na_text, uryvky_schuze


@dataclass
class VysledekParovani:
    """Souhrn párování jedné schůze."""

    hlasovani: int = 0
    s_uryvkem: int = 0
    s_dokumentem: int = 0


def paruj_schuzi(conn: sqlite3.Connection, schuze: int) -> VysledekParovani:
    """Najde předmět všech hlasování schůze ve stažených úsecích stenozáznamu a uloží ho.

    Párování se počítá vždy celé znovu (úseky se mohou doplnit nebo autorizovat).
    """
    hlasovani = conn.execute(
        """
        SELECT h.id_hlasovani, h.datum, h.bod, t.ct FROM hlasovani h
        LEFT JOIN schuze s ON s.id_organ = h.id_organ AND s.cislo = h.schuze
        LEFT JOIN bod b ON b.id_bod = (SELECT MIN(b2.id_bod) FROM bod b2
                                       WHERE b2.id_schuze = s.id_schuze AND b2.cislo = h.bod)
        LEFT JOIN tisk t ON t.id_tisk = b.id_tisk
        WHERE h.id_organ = ? AND h.schuze = ?
        """,
        (aktualni_obdobi(conn), schuze),
    ).fetchall()
    if not hlasovani:
        return VysledekParovani()
    useky = conn.execute(
        "SELECT url, cesta, autorizovano, poradi FROM dokument WHERE typ = 'steno_usek' AND schuze = ? "
        "ORDER BY poradi",
        (schuze,),
    ).fetchall()
    uryvky = uryvky_schuze(
        [replace(usek_na_text(precti_html(config.DATA_DIR / u["cesta"])), turn=u["poradi"])
         for u in useky],
        {h["id_hlasovani"]: h["datum"] for h in hlasovani},
    )

    vysledek = VysledekParovani(hlasovani=len(hlasovani))
    dokumenty: dict[int, str | None] = {}
    with conn:
        conn.execute(
            "DELETE FROM predmet_hlasovani WHERE id_hlasovani IN "
            f"({','.join('?' * len(hlasovani))})", [h["id_hlasovani"] for h in hlasovani])
        for h in hlasovani:
            uryvek = uryvky.get(h["id_hlasovani"])
            if uryvek is None:
                continue
            predmet = rozpoznej_predmet(uryvek.text)
            if predmet.druh == "celek" and not h["bod"]:
                # Bod 0 = pořad schůze: „jako celek“ je tu schválení pořadu, ne zákona.
                predmet = replace(predmet, druh="proceduralni")
            dokument = None
            if predmet.druh == "pozmenovaci" and h["ct"] is not None:
                if h["ct"] not in dokumenty:
                    dokumenty[h["ct"]] = dokument_navrhu(conn, h["ct"])
                dokument = dokumenty[h["ct"]]
            usek = useky[uryvek.usek]
            conn.execute(
                "INSERT INTO predmet_hlasovani VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (h["id_hlasovani"], uryvek.text, predmet.otazka, predmet.druh, predmet.oznaceni,
                 usek["url"], dokument, usek["autorizovano"]),
            )
            vysledek.s_uryvkem += 1
            vysledek.s_dokumentem += dokument is not None
    return vysledek
