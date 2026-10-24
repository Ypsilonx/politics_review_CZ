"""Statistiky poslanců a klubů nad předpočítanými tabulkami (``hlas_klub``, ``klub_hlasovani``).

Pravidla:
- **Docházka** se počítá z hlasování po složení slibu (kód W se nezapočítává). Nepřítomen =
  nepřihlášen (@) nebo omluven (M); nepřihlášení v době omluvy (tabulka ``omluva``) je omluvené.
- **Proti klubu** = poslanec hlasoval Ano/Ne a většina jeho klubu (k datu) hlasovala opačně.
  Remíza v klubu se nepočítá, zdržení a nepřítomnost také ne.
- **Vystoupení** = projevy v roli řečníka (druh 3 a 5 v ``vystoupeni``), ne řízení schůze.
"""

import sqlite3
from dataclasses import dataclass

from politika.db.dotazy.hlasovani import HLASOVANI_S_BODEM
from politika.db.dotazy.poslanci import hledej_poslance
from politika.db.dotazy.spolecne import aktualni_obdobi

DRUH_RECNIK = (3, 5)
_NEPRITOMEN = ("@", "M")

# Omluva pokrývá hlasování: stejný den a čas v intervalu od–do (chybí-li, platí celý den).
_OMLUVENO = """EXISTS (SELECT 1 FROM omluva o WHERE o.id_poslanec = hk.id_poslanec
    AND o.den = h.datum AND (o.od IS NULL OR o.od <= h.cas) AND (o.do IS NULL OR o.do >= h.cas))"""


@dataclass(frozen=True)
class Dochazka:
    """Docházka poslance na hlasování: celkem po slibu, přítomen, omluven, neomluven."""

    celkem: int
    pritomen: int
    omluven: int
    neomluven: int

    @property
    def procento(self) -> float:
        """Podíl hlasování, u kterých byl přítomen (0–100)."""
        return 100 * self.pritomen / self.celkem if self.celkem else 0.0


def dochazka(conn: sqlite3.Connection, id_poslanec: int) -> Dochazka:
    """Spočítá docházku poslance na hlasování v aktuálním období."""
    r = conn.execute(
        f"""
        SELECT COUNT(*) AS celkem,
               SUM(hk.vysledek NOT IN {_NEPRITOMEN}) AS pritomen,
               SUM(hk.vysledek = 'M' OR (hk.vysledek = '@' AND {_OMLUVENO})) AS omluven
        FROM hlas_klub hk JOIN hlasovani h ON h.id_hlasovani = hk.id_hlasovani
        WHERE hk.id_poslanec = ? AND hk.vysledek != 'W'
        """,
        (id_poslanec,),
    ).fetchone()
    celkem, pritomen, omluven = r["celkem"], r["pritomen"] or 0, r["omluven"] or 0
    return Dochazka(celkem, pritomen, omluven, celkem - pritomen - omluven)


_PROTI_KLUBU = """
    hk.vysledek IN ('A', 'B') AND kh.vetsina IS NOT NULL AND hk.vysledek != kh.vetsina
"""


def proti_klubu(conn: sqlite3.Connection, id_poslanec: int, limit: int = 100) -> list[sqlite3.Row]:
    """Vrátí hlasování, kde poslanec hlasoval proti většině svého klubu (od nejnovějšího).

    Řádek má navíc ``hlas`` (poslanec), ``vetsina`` (klub), ``klub_ano`` a ``klub_ne``.
    """
    return conn.execute(
        f"""
        SELECT x.*, hk.vysledek AS hlas, kh.vetsina, kh.ano AS klub_ano, kh.ne AS klub_ne
        FROM hlas_klub hk
        JOIN klub_hlasovani kh ON kh.id_hlasovani = hk.id_hlasovani AND kh.id_klub = hk.id_klub
        JOIN ({HLASOVANI_S_BODEM}) x ON x.id_hlasovani = hk.id_hlasovani
        WHERE hk.id_poslanec = ? AND {_PROTI_KLUBU}
        ORDER BY x.datum DESC, x.cas DESC LIMIT ?
        """,
        (id_poslanec, limit),
    ).fetchall()


def pocet_proti_klubu(conn: sqlite3.Connection, id_poslanec: int) -> int:
    """Počet hlasování, kde poslanec hlasoval proti většině svého klubu."""
    return conn.execute(
        f"""SELECT COUNT(*) FROM hlas_klub hk
        JOIN klub_hlasovani kh ON kh.id_hlasovani = hk.id_hlasovani AND kh.id_klub = hk.id_klub
        WHERE hk.id_poslanec = ? AND {_PROTI_KLUBU}""",
        (id_poslanec,),
    ).fetchone()[0]


def vystoupeni(conn: sqlite3.Connection, id_osoba: int) -> list[sqlite3.Row]:
    """Vrátí projevy osoby (jako řečník) v aktuálním období po úsecích: schůze, den, bod, odkaz.

    Řádek: ``schuze, turn, datum, od_t, aname, bod_nazev, tisk_ct`` – od nejnovějšího.
    """
    return conn.execute(
        f"""
        SELECT s.schuze, s.turn, s.datum, s.od_t, v.aname, b.nazev AS bod_nazev, t.ct AS tisk_ct
        FROM vystoupeni v
        JOIN steno s ON s.id_steno = v.id_steno
        LEFT JOIN bod b ON b.id_bod = v.id_bod
        LEFT JOIN tisk t ON t.id_tisk = b.id_tisk
        WHERE v.id_osoba = ? AND s.id_organ = ? AND v.druh IN {DRUH_RECNIK}
        ORDER BY s.datum DESC, s.turn DESC, v.aname DESC
        """,
        (id_osoba, aktualni_obdobi(conn)),
    ).fetchall()


# --- Žebříčky a klubové statistiky (sekce Statistiky) ---

def zebricek_poslancu(conn: sqlite3.Connection) -> list[dict]:
    """Vrátí pro každého poslance s trvajícím mandátem docházku, proti klubu a počet vystoupení.

    Klíče: ``id_poslanec, jmeno, klub, celkem, pritomen, omluven, neomluven, ucast,
    proti_klubu, vystoupeni``.
    """
    obdobi = aktualni_obdobi(conn)
    hlasy = {r["id_poslanec"]: r for r in conn.execute(
        f"""
        SELECT hk.id_poslanec, COUNT(*) AS celkem,
               SUM(hk.vysledek NOT IN {_NEPRITOMEN}) AS pritomen,
               SUM(hk.vysledek = 'M' OR (hk.vysledek = '@' AND {_OMLUVENO})) AS omluven,
               SUM(kh.vetsina IS NOT NULL AND hk.vysledek IN ('A', 'B') AND hk.vysledek != kh.vetsina)
                 AS proti_klubu
        FROM hlas_klub hk
        JOIN hlasovani h ON h.id_hlasovani = hk.id_hlasovani
        LEFT JOIN klub_hlasovani kh ON kh.id_hlasovani = hk.id_hlasovani AND kh.id_klub = hk.id_klub
        WHERE hk.vysledek != 'W' AND h.id_organ = ?
        GROUP BY hk.id_poslanec
        """,
        (obdobi,),
    )}
    projevy = dict(conn.execute(
        f"""SELECT v.id_osoba, COUNT(*) FROM vystoupeni v JOIN steno s ON s.id_steno = v.id_steno
        WHERE s.id_organ = ? AND v.druh IN {DRUH_RECNIK} GROUP BY v.id_osoba""",
        (obdobi,),
    ).fetchall())
    vysledek = []
    for p in hledej_poslance(conn):
        h = hlasy.get(p["id_poslanec"])
        celkem = h["celkem"] if h else 0
        pritomen, omluven = (h["pritomen"] or 0, h["omluven"] or 0) if h else (0, 0)
        vysledek.append({
            **p, "celkem": celkem, "pritomen": pritomen, "omluven": omluven,
            "neomluven": celkem - pritomen - omluven,
            "ucast": 100 * pritomen / celkem if celkem else 0.0,
            "proti_klubu": (h["proti_klubu"] or 0) if h else 0,
            "vystoupeni": projevy.get(p["id_osoba"], 0),
        })
    return vysledek


def jednota_klubu(conn: sqlite3.Connection) -> list[dict]:
    """Vrátí pro každý klub podíl hlasů Ano/Ne jeho členů, které šly s většinou klubu (0–100).

    Hlasování, kde byl klub nerozhodně (remíza), se nezapočítávají.

    Klíče: ``id_klub, zkratka, hlasu, s_vetsinou, jednota``; seřazeno od nejjednotnějšího.
    """
    return [dict(r) for r in conn.execute(
        """
        SELECT kh.id_klub, o.zkratka, SUM(kh.ano + kh.ne) AS hlasu,
               SUM(CASE kh.vetsina WHEN 'A' THEN kh.ano WHEN 'B' THEN kh.ne ELSE 0 END) AS s_vetsinou,
               100.0 * SUM(CASE kh.vetsina WHEN 'A' THEN kh.ano WHEN 'B' THEN kh.ne ELSE 0 END)
                 / SUM(kh.ano + kh.ne) AS jednota
        FROM klub_hlasovani kh JOIN organ o ON o.id_organ = kh.id_klub
        JOIN hlasovani h ON h.id_hlasovani = kh.id_hlasovani
        WHERE h.id_organ = ? AND kh.vetsina IS NOT NULL
        GROUP BY kh.id_klub HAVING hlasu > 0
        ORDER BY jednota DESC
        """,
        (aktualni_obdobi(conn),),
    )]


def shoda_klubu(conn: sqlite3.Connection) -> tuple[list[str], dict[tuple[str, str], float]]:
    """Matice shody klubů: v kolika % hlasování, kde měly oba kluby většinu, hlasovaly stejně.

    :return: ``(zkratky klubů seřazené podle velikosti, {(klub1, klub2): procento})``
    """
    obdobi = aktualni_obdobi(conn)
    radky = conn.execute(
        """
        SELECT o1.zkratka AS k1, o2.zkratka AS k2,
               100.0 * SUM(a.vetsina = b.vetsina) / COUNT(*) AS shoda
        FROM klub_hlasovani a
        JOIN klub_hlasovani b ON b.id_hlasovani = a.id_hlasovani
        JOIN organ o1 ON o1.id_organ = a.id_klub
        JOIN organ o2 ON o2.id_organ = b.id_klub
        JOIN hlasovani h ON h.id_hlasovani = a.id_hlasovani
        WHERE a.vetsina IS NOT NULL AND b.vetsina IS NOT NULL AND h.id_organ = ?
        GROUP BY a.id_klub, b.id_klub
        """,
        (obdobi,),
    ).fetchall()
    velikost = dict(conn.execute(
        """SELECT o.zkratka, COUNT(*) FROM zarazeni z JOIN organ o ON o.id_organ = z.id_organ
        WHERE o.id_typ = 1 AND o.id_nadrazeny = ? AND (z.do IS NULL OR z.do >= date('now'))
        GROUP BY o.zkratka""",
        (obdobi,),
    ).fetchall())
    kluby = sorted({r["k1"] for r in radky}, key=lambda k: -velikost.get(k, 0))
    return kluby, {(r["k1"], r["k2"]): r["shoda"] for r in radky}


def nejtesnejsi_hlasovani(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    """Vrátí hlasování, kde rozhodlo nejméně hlasů (rozdíl pro a potřebného kvóra)."""
    return conn.execute(
        f"SELECT * FROM ({HLASOVANI_S_BODEM}) WHERE id_organ = ? AND kvorum > 0 "
        "ORDER BY ABS(pro - kvorum), datum DESC LIMIT ?",
        (aktualni_obdobi(conn), limit),
    ).fetchall()
