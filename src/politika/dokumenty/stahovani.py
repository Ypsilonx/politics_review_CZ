"""Šetrné stahování z psp.cz: noční okno, pauza mezi požadavky, opakování připojení, cache na disku."""

import time
from datetime import datetime
from pathlib import Path

import httpx

from politika import config

PSP_URL = "https://www.psp.cz"
KODOVANI_PSP = "cp1250"
# Čekání (s) před dalšími pokusy, když psp.cz dočasně nepřijímá spojení.
CEKANI_PRI_VYPADKU = (15, 60, 180)


class MimoNocniOkno(Exception):
    """Stahování došlo na konec nočního okna (``config.NOCNI_OKNO``) – zbytek příští noc."""


def v_nocnim_okne(ted: datetime | None = None) -> bool:
    """Zda je čas ``ted`` (výchozí teď) uvnitř nočního okna; okno může přecházet přes půlnoc."""
    od, do = config.NOCNI_OKNO
    hodina = (ted or datetime.now()).hour
    return od <= hodina < do if od < do else hodina >= od or hodina < do


class Stahovac:
    """HTTP klient pro psp.cz, který mezi požadavky drží pauzu ``config.PAUZA_MEZI_POZADAVKY``.

    Používá se jako context manager (``with Stahovac() as s: …``).
    """

    def __init__(self, client: httpx.Client | None = None, jen_v_noci: bool = False) -> None:
        """:param client: vlastní klient (pro testy); jinak se vytvoří s User-Agentem a retries.
        :param jen_v_noci: mimo noční okno požadavek nepošle a vyhodí ``MimoNocniOkno``
            (atribut ``jen_v_noci`` jde měnit mezi kroky jednoho běhu)
        """
        self.jen_v_noci = jen_v_noci
        # psp.cz občas nedokončí TLS handshake nového spojení; krátký connect timeout + retries
        # takové spojení rychle zahodí a zkusí znovu (jinak se čeká ~20 s na limit OS).
        self._client = client or httpx.Client(
            headers={"User-Agent": config.USER_AGENT}, follow_redirects=True,
            timeout=httpx.Timeout(60, connect=5),
            transport=httpx.HTTPTransport(retries=3),
        )
        self._posledni = 0.0
        self.pocet_pozadavku = 0

    def __enter__(self) -> "Stahovac":
        return self

    def __exit__(self, *_: object) -> None:
        self._client.close()

    def _get(self, url: str) -> httpx.Response:
        """Stáhne URL (relativní k psp.cz) po dodržení pauzy; při HTTP chybě vyhodí výjimku.

        Když server nepřijímá spojení ani po opakování v transportu (omezuje nová spojení),
        počká postupně ``CEKANI_PRI_VYPADKU`` sekund a zkusí to znovu; pak výjimku propustí.
        """
        if self.jen_v_noci and not v_nocnim_okne():
            raise MimoNocniOkno
        for cekani in (*CEKANI_PRI_VYPADKU, None):
            cekat = self._posledni + config.PAUZA_MEZI_POZADAVKY - time.monotonic()
            if cekat > 0:
                time.sleep(cekat)
            try:
                odpoved = self._client.get(url if url.startswith("http") else PSP_URL + url)
                break
            except httpx.TransportError:
                if cekani is None:
                    raise
                time.sleep(cekani)
            finally:
                self._posledni = time.monotonic()
                self.pocet_pozadavku += 1
        odpoved.raise_for_status()
        return odpoved

    def stahni(self, url: str, cil: Path, prepsat: bool = False) -> Path:
        """Stáhne soubor do ``cil``; existující soubor bez ``prepsat`` se znovu nestahuje.

        Zapisuje přes dočasný soubor, aby přerušené stažení nenechalo poloviční soubor.
        """
        if cil.exists() and not prepsat:
            return cil
        cil.parent.mkdir(parents=True, exist_ok=True)
        docasny = cil.with_name(cil.name + ".part")
        docasny.write_bytes(self._get(url).content)
        docasny.replace(cil)
        return cil


def precti_html(cesta: Path) -> str:
    """Přečte uloženou HTML stránku psp.cz (kódování Windows-1250)."""
    return cesta.read_bytes().decode(KODOVANI_PSP, errors="replace")
