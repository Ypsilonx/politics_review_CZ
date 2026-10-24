# Sledování poslanců v1 – implementační plán

**Spec:** `docs/specs/2026-10-24-sledovani-poslancu-design.md`
**Cíl:** vyberu politika a u jeho hlasování vidím, o čem bylo, a otevřu příslušné PDF.
**Stack:** Python 3.14 (uv), FastAPI + Jinja2 + HTMX, SQLite (`sqlite3` ze stdlib), httpx, pytest.
**Provádění:** po jednom tasku v hlavní session, po každém tasku zastávka.

## Struktura

```
src/politika/
  config.py            # cesty (DATA_DIR, DB_PATH), URL otevřených dat – nastavitelné env proměnnými
  db/schema.sql        # tabulky
  db/connection.py     # připojení, inicializace schématu
  importer/unl.py      # parsování UNL souborů
  importer/opendata.py # stažení ZIPů + import tabulek do DB
  dokumenty/stahovani.py  # stahování souborů s cache a pauzou
  parovani/steno.py    # hlasování → úryvek ze stenozáznamu → označení návrhu
  parovani/navrhy.py   # označení návrhu → dokument (PDF)
  analyza/statistiky.py
  web/app.py, web/routes/*.py, web/templates/, web/static/
  cli.py               # příkazy: import, stahni-dokumenty, paruj, obnova
data/                  # mimo git: opendata/, steno/, dokumenty/, politika.db
tests/
```

## Body napojení

**Otevřená data PSP** (`https://www.psp.cz/eknih/cdrom/opendata/`)
- Vstup: ZIPy `poslanci.zip`, `hl-2025ps.zip`, `schuze.zip`, `tisky.zip`, `steno.zip`, `sd.zip`.
  Popis struktury tabulek je na psp.cz v sekci Otevřená data (stránky dokumentace jednotlivých sad).
- Formát: UNL. Oddělovač `|`, **každý řádek končí `|`** (poslední prázdné pole zahodit), kódování
  **Windows-1250**, data ve tvaru `dd.mm.yyyy`. Text v polích může obsahovat zalomení řádku → ověřit v T0.
- Hlasování (podle paměti, **ověřit proti dokumentaci v T0**): `hl_hlasovani` (id_hlasovani, id_organ,
  schuze, cislo, bod, datum, cas, pro, proti, …, vysledek, nazev_dlouhy, nazev_kratky),
  `hl_poslanec` (id_poslanec, id_hlasovani, vysledek), kde kódy A = ano, B/N = ne, C = zdržel se,
  F = nehlasoval, @ = nepřihlášen, M = omluven, W = před slibem, K = zdržel se / nehlasoval.
  Hlasy jednoho období bývají rozdělené do několika souborů (`…h1.unl`, `…h2.unl`).
- Pozor: vždy **kompletní snímek** (bez přírůstků), aktualizace 1× denně → import nahrazuje data
  v transakci (idempotentně). `id_poslanec` ≠ `id_osoba`; klubová příslušnost se bere z `zarazeni`
  + `organy` (časově omezená, poslanec mohl klub změnit). Pro ověření nikdy nedělat dotazy
  na HTML stránky psp.cz v cyklu.

**Dokumenty (stenozáznamy, PDF tisků)**
- Vstup: URL dohledané v T0. Stahovat přes `httpx`, User-Agent s kontaktem, pauza ≥ 1 s mezi
  požadavky, soubor, který už je v `data/`, se znovu nestahuje.
- Pozor: stenozáznam vychází nejdřív v neautorizované verzi a teprve za několik dní v autorizované →
  evidovat verzi a umět ho znovu stáhnout.

**FastAPI / prohlížeč PDF**
- PDF se servíruje z `data/dokumenty/` přes vlastní endpoint s `Content-Disposition: inline`
  (prohlížeč ho zobrazí sám, bez knihovny). Cesta souboru se bere z DB, nikdy z parametru URL
  (path traversal).

---

### Task 0: Průzkum dat a založení projektu (zastávka s nálezy)
- **Soubory:** `pyproject.toml`, `.python-version` (3.14), `.gitignore` (`data/`, `.venv/`),
  `.vscode/settings.json`, `docs/specs/2026-10-24-pruzkum-dat.md`.
- **Co:** stáhnout všech 6 ZIPů do `data/opendata/`. Zjistit: strukturu tabulek hlasování, schůzí,
  bodů a tisků; **co obsahuje `steno.zip`** (texty, nebo rejstřík); kde jsou plné texty stenozáznamů
  a jak je stáhnout; **jak se dostat od tisku 231 k souboru s pozměňovacími návrhy (PDF)**.
  Ručně projít celou cestu pro 34. schůzi, hlasování 288, až k PDF a zapsat ji do poznámek.
- **Ověření:** v poznámkách je popsaná ověřená cesta „hlasování 288 → věta ve stenozáznamu → PDF“
  s konkrétními soubory a URL. Podle nálezů se případně upraví T3–T4.

### Task 1: Databáze a import otevřených dat
- **Soubory:** `config.py`, `db/schema.sql`, `db/connection.py`, `importer/unl.py`,
  `importer/opendata.py`, `cli.py`, `tests/test_unl.py`, `tests/test_import.py`.
- **Rozhraní:**
  - `parse_unl(path: Path, columns: list[str]) -> Iterator[dict[str, str | None]]`
  - `stahni_opendata(cil: Path, sady: list[str]) -> list[Path]`
  - `importuj_vse(conn: sqlite3.Connection, adresar: Path) -> dict[str, int]` (tabulka → počet řádků)
  - `get_connection(db_path: Path) -> sqlite3.Connection`
  - CLI: `uv run politika import`
- **Tabulky:** `osoba`, `poslanec`, `organ`, `zarazeni`, `hlasovani`, `hlas`, `schuze`, `bod`, `tisk`.
- **Testy:** parser (cp1250 → správná diakritika, koncové `|`, prázdné pole → `None`);
  dvojí import téhož snímku dá stejné počty řádků.
- **Ověření:** po importu dotaz na 34. schůzi, hlasování 288, vrátí výsledek „přijato“, 171 hlasů pro
  a hlas Stržínka „A“.

### Task 2: Web – profil poslance a detail hlasování (bez popisu předmětu)
- **Soubory:** `web/app.py`, `web/routes/poslanci.py`, `web/routes/hlasovani.py`,
  `web/templates/{base,poslanec,hlasovani}.html`, `web/static/style.css`.
- **Rozhraní:** `GET /poslanci` (vyhledávání podle jména, HTMX), `GET /poslanec/{id_poslanec}`
  (historie hlasování po stránkách), `GET /hlasovani/{id_hlasovani}` (výsledek, hlasy po klubech,
  odkaz na psp.cz). Dotazy do DB jsou v `db/dotazy.py`, ne v routách.
- **Ověření:** v prohlížeči (Playwright) najdu Stržínka, otevřu hlasování 288 a vidím hlasy po klubech.

### Task 3: Stahování dokumentů
- **Soubory:** `dokumenty/stahovani.py`, rozšíření `schema.sql` o tabulku `dokument`
  (typ, url, cesta, verze, stazeno), CLI `uv run politika stahni-dokumenty --schuze N`.
- **Rozhraní:** `stahni(url: str, cil: Path, client: httpx.Client) -> Path` (cache + pauza);
  `stahni_steno_schuze(conn, schuze: int) -> list[Path]`; `stahni_navrhy_tisku(conn, tisk: int) -> list[Path]`.
- **Ověření:** stažení dokumentů pro 34. schůzi a při druhém spuštění se nestáhne nic.

### Task 4: Párování hlasování → předmět → PDF
- **Soubory:** `parovani/steno.py`, `parovani/navrhy.py`, tabulka `predmet_hlasovani`
  (id_hlasovani, uryvek, oznaceni_navrhu, druh, id_dokument, stav), CLI `uv run politika paruj`,
  `tests/test_parovani.py` s úryvky reálných stenozáznamů jako fixturami.
- **Rozhraní:**
  - `najdi_uryvek(text: str, cislo_hlasovani: int) -> str | None`
  - `rozpoznej_predmet(uryvek: str) -> Predmet` (dataclass: `druh` ∈ {"pozmenovaci", "celek",
    "proceduralni", "nezjisteno"}, `oznaceni: str | None`, např. "B2")
  - `prirad_dokument(conn, id_hlasovani: int, predmet: Predmet) -> int | None`
- **Testy:** úryvek pro „hlasování pořadové číslo 288“ se najde i při zalomení řádku uprostřed věty;
  rozpoznání A1/B2, „jako celek“ a procedurálního hlasování; nenalezené číslo → `nezjisteno`.
- **Ověření:** report úspěšnosti pro 34. schůzi (kolik hlasování má předmět / PDF), detail hlasování 288
  v aplikaci ukazuje úryvek, označení návrhu a odkaz na PDF otevřitelné v prohlížeči.

### Task 5: Sledovaní a proud novinek (úvodní stránka)
- **Před začátkem:** mockup úvodní stránky k odsouhlasení (co nahoře / dole).
- **Soubory:** tabulky `skupina` (název, typ: poslanec/strana/seznam), `skupina_clen`;
  `web/routes/sledovani.py`, `web/routes/proud.py`, šablony.
- **Rozhraní:** `GET /` (proud: hlasování sledovaných, nejnovější nahoře, filtr podle skupiny),
  `GET/POST /sledovani` (přidat a odebrat skupinu a členy).
- **Ověření:** přidám Stržínka a jeden klub a proud ukazuje jejich poslední hlasování s předmětem.

### Task 6: Analýza v profilu
- **Soubory:** `analyza/statistiky.py`, `tests/test_statistiky.py`, rozšíření šablony profilu.
- **Rozhraní:** `dochazka(conn, id_poslanec, od, do) -> Dochazka`;
  `proti_klubu(conn, id_poslanec) -> list[int]` (id hlasování); `jednota_klubu(conn, id_organ) -> float`.
- **Pravidlo:** „proti klubu“ = poslancův hlas A/B se liší od většinového A/B klubu v daném hlasování.
  Klub se bere k datu hlasování. Absence a zdržení zvlášť.
- **Testy:** na malé ručně sestavené DB (tmp_path): většina, remíza v klubu (→ nepočítat), změna klubu.
- **Ověření:** profil Stržínka ukazuje docházku a seznam hlasování proti klubu.

### Task 7: Denní obnova a provoz
- **Soubory:** CLI `uv run politika obnova` (import → stažení nových dokumentů → párování),
  `README.md` (spuštění, Plánovač úloh Windows / cron na serveru), `STATUS.md`, projektový `CLAUDE.md`.
- **Ověření:** `obnova` doběhne dvakrát po sobě bez chyby a druhý běh nic znovu nestahuje.

**Po T7:** jedna nezávislá revize kódu celého projektu.
