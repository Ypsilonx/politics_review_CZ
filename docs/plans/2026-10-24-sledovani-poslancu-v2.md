# Sledování poslanců v2 – implementační plán

**Spec:** `docs/specs/2026-10-24-sledovani-poslancu-design.md` (v2), průzkum: `docs/specs/2026-10-24-pruzkum-dat.md`
**Stack:** Python 3.14 (uv), FastAPI + Jinja2 + HTMX, SQLite, httpx, beautifulsoup4, mammoth, Leaflet, pytest.
**Provádění:** po jednom tasku v hlavní session, po každém tasku zastávka.
**Hotovo:** T0 průzkum, T1 import otevřených dat, T2 první web (vyhledání, profil, detail hlasování).

## Struktura (cílová)

```
src/politika/
  config.py, cli.py              # cli: import, stahni-dokumenty, paruj, obnova, web
  db/schema.sql, connection.py, dotazy/   # dotazy rozdělené podle sekcí (poslanci, hlasovani, tisky…)
  importer/unl.py, opendata.py
  dokumenty/stahovani.py, odkazy.py, prevod.py, kancelare.py, foto.py
  parovani/steno.py, navrhy.py
  analyza/statistiky.py
  web/app.py, routes/*.py, templates/, static/css/, static/js/
data/  # mimo git: opendata/, steno/, dokumenty/, foto/, politika.db
```

## Body napojení

**Otevřená data PSP** (`/eknih/cdrom/opendata/*.zip`): UNL, `|` + koncové `|`, Windows-1250, denní
kompletní snímek → import po tabulkách v transakci (hotovo v T1). Kódy hlasů: A, B/N, C, K, F, @, M, W.
Bod 0 = „Pořad schůze“ = procedurální hlasování mimo bod.

**Stránky a soubory psp.cz mimo otevřená data** (1A): vždy `httpx` + `PAUZA_MEZI_POZADAVKY`,
`USER_AGENT` bez osobních údajů, retries=3, uložit do `data/` a znovu nestahovat. Kódování Windows-1250.
- stenozáznamy: `/eknih/2025ps/stenprot/{NNN}schuz/{S}-{D}.html` → úseky `s{NNN}{xxx}.htm`
  (neautorizované se po několika dnech stáhnou znovu; ZIPy po schůzích vracejí 404),
- soubory tisků: `/sqw/historie.sqw?T={ct}&O=10` (SD → `orig2.sqw?idd=`, DOCX),
  `/sqw/text/tiskt.sqw?o=10&ct={ct}&ct1={n}` (PDF verzí tisku),
- kanceláře: `/sqw/pk.sqw`, ve skriptu pole `[jméno, lat, lng, 'adresa<br>…', …, id_osoba]`,
- fotky: `/eknih/cdrom/2025ps/eknih/2025ps/poslanci/small/s{id_osoba}.jpg` (ověřit i velkou variantu).

**Prohlížeč:** PDF se servíruje inline, cesta k souboru jde z DB, nikdy z URL (path traversal).
Leaflet a htmx z CDN s pevnou verzí. Dlaždice OSM: uvést atribuci a nezatěžovat je (jen zobrazení mapy).

---

### Task 3: Vzhled a kostra aplikace
- **Co:** tmavý režim jako výchozí + přepínač (uložený v `localStorage`, respektuje
  `prefers-color-scheme`), horní menu (Přehled, Sledovaní, Poslanci, Hlasování, Zákony, Schůze,
  Statistiky, Mapa) s hamburgerem na mobilu, pole globálního hledání (zatím jen poslanci), nové
  rozložení stávajících stránek (karty poslanců, profil s hlavičkou, detail hlasování).
  Zatím neexistující sekce mají stránku „připravujeme“.
- **Soubory:** `static/css/{base,layout,komponenty}.css` (barvy jako proměnné pro oba režimy),
  `static/js/tema.js`, `templates/base.html` + `_menu.html`, úpravy stávajících šablon,
  `db/dotazy.py` → balíček `db/dotazy/` (`poslanci.py`, `hlasovani.py`).
- **Ověření:** Playwright: desktop i mobil, oba režimy, konzole bez chyb. Screenshoty ukázat.

### Task 4: Stahování dokumentů
- **Soubory:** `dokumenty/stahovani.py`, `dokumenty/odkazy.py` (`beautifulsoup4`), `dokumenty/prevod.py`
  (`mammoth`), tabulka `dokument` (typ, url, idd, cesta, autorizovano, stazeno), CLI `stahni-dokumenty`.
- **Rozhraní:** `stahni(url, cil, client) -> Path`; `stahni_steno_schuze(conn, schuze) -> list[Path]`;
  `stahni_soubory_tisku(conn, ct) -> list[Path]`; `docx_na_html(cesta) -> str`.
- **Ověření:** 34. schůze a tisk 213 se stáhnou, druhé spuštění nestáhne nic.

### Task 5: Předmět hlasování ze stenozáznamu
- **Pravidlo:** číslo zazní až po hlasování → úryvek = text od předchozí zmínky „hlasování (číslo) N-1“
  po „hlasování číslo N“ (posledních ~1 500 znaků), hledat i v sousedním úseku. Rozpoznat druh:
  pozměňovací (A1, B2…), celek, procedurální, nezjištěno.
- **Soubory:** `parovani/steno.py`, `parovani/navrhy.py`, tabulka `predmet_hlasovani`, CLI `paruj`,
  `tests/test_parovani.py` (fixtury z reálných úseků `s034426.htm`, `s034402.htm`).
- **Rozhraní:** `najdi_uryvek(text, cislo) -> str | None`; `rozpoznej_predmet(uryvek) -> Predmet`;
  `prirad_dokument(conn, id_hlasovani, predmet) -> int | None`.
- **Testy:** 34/274 (návrh pana poslance Bendy), 34/256 (přerušení schůze), 34/257 → nezjištěno.
- **Ověření:** report úspěšnosti pro 34. schůzi, detail hlasování ukazuje úryvek a odkaz na návrh.

### Task 6: Zákony a schůze
- **Co:** seznam tisků (filtr stav/druh, hledání), detail tisku (stav z `hist.unl`, předkladatelé,
  verze s PDF, pozměňovací návrhy s autory, všechna hlasování k tisku, odkaz do Sbírky přes `sbirka.zip`);
  prohlížeč dokumentů (PDF inline, DOCX jako HTML); seznam schůzí, pořad bodů, hlasování po bodech.
- **Soubory:** import `hist`, `predkladatel`, `sd_dokument`, `sbirka`; `routes/tisky.py`, `routes/schuze.py`,
  `routes/dokumenty.py`, `db/dotazy/{tisky,schuze}.py`, šablony.
- **Ověření:** tisk 213 ukazuje verze, návrhy a hlasování; PDF i DOCX se otevřou v aplikaci.

### Task 7: Profil poslance naplno + mapa kanceláří
- **Co:** foto (cache v `data/foto/`), kraj, výbory a funkce (`zarazeni` s `cl_funkce=1` + `funkce`),
  e-mail, regionální kancelář, docházka (přítomen / omluven z `omluvy.unl` / neomluven), hlasování
  proti klubu, vystoupení (`rec.unl`), návrhy zákonů, pozměňovací návrhy, interpelace (`interp.zip`).
  Mapa: Leaflet + markercluster, filtr klub a kraj, odkaz na profil.
- **Soubory:** `dokumenty/kancelare.py`, `dokumenty/foto.py`, tabulky `kancelar`, `vystoupeni`, `omluva`,
  `interpelace`, `funkce`; `analyza/statistiky.py` (docházka, proti klubu), `routes/mapa.py`,
  `static/js/mapa.js`, `tests/test_statistiky.py`.
- **Pravidlo „proti klubu“:** viz spec. Testy na malé DB: většina, remíza (nepočítat), změna klubu.
- **Ověření:** profil Stržínka má všechny bloky, mapa ukazuje ~185 kanceláří, testy statistik projdou.

### Task 8: Statistiky
- **Co:** žebříčky (účast, neomluvené absence, vystoupení / nepromluvili, rebelové), jednota klubů,
  matice shody klubů (heatmapa v CSS), nejtěsnější hlasování; filtr období (celé / posledních 90 dní).
- **Soubory:** `analyza/statistiky.py` (rozšíření), `routes/statistiky.py`, šablony.
  Výpočty náročné na čas se po importu předpočítají do tabulek.
- **Ověření:** čísla u 2–3 poslanců ručně porovnaná s psp.cz, stránka se načte do 1 s.

### Task 9: Sledovaní a Přehled
- **Před začátkem:** mockup úvodní stránky k odsouhlasení.
- **Co:** skupiny (poslanec / strana / vlastní seznam), tlačítko „sledovat“ v profilu a v seznamech,
  stránka Sledovaní (hlasování skupin s filtry), Přehled (proud se zvýrazněním „proti klubu“ /
  „chyběl u závěrečného hlasování“, rychlé statistiky, nejbližší schůze). Úvodní stránka = Přehled.
- **Soubory:** tabulky `skupina`, `skupina_clen`; `routes/{sledovani,prehled}.py`, šablony.
- **Ověření:** po přidání Stržínka a jednoho klubu ukazuje proud jejich poslední hlasování s předmětem.

### Task 10: Hledání, export, obnova a provoz
- **Co:** globální hledání (poslanec, číslo tisku, název), export CSV u tabulek, CLI `obnova`
  (import → dokumenty → párování → předpočty), README (spuštění, Plánovač úloh / cron),
  `STATUS.md`, projektový `CLAUDE.md`.
- **Ověření:** `obnova` doběhne 2× po sobě bez chyby a druhý běh nic nestahuje.

**Po T10:** jedna nezávislá revize kódu celého projektu.
