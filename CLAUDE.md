# Sledování poslanců (politics_review_CZ)

Webová aplikace pro sledování hlasování poslanců PSP ČR: jak hlasovali a o čem se hlasovalo
(předmět ze stenozáznamu, znění návrhů), profily, zákony, schůze, statistiky, mapa kanceláří.
Zatím pro osobní použití, později veřejně na GitHubu. Velikost: M.

Doména: python-uv (web-api) + web-frontend. Obecná pravidla domén jsou ve skillech.

## Spuštění a ověření

- Web: `uv run politika web` (http://127.0.0.1:8000; domácí síť `--host 0.0.0.0`)
- Data: tlačítko „Aktualizovat data“ na Přehledu (`web/routes/aktualizace.py` spustí
  `python -m politika obnova --cerstve-ihned`), nebo `uv run politika obnova`, dílčí kroky `import`,
  `stahni-dokumenty [--schuze N] [--tisk CT] [--kancelare] [--fotky]`, `paruj [--schuze N]`
- Testy: `PYTHONUTF8=1 uv run pytest -q`
- UI ověřovat nad **kopií** DB (`POLITIKA_DB=<kopie> uv run politika web --port 8765`); kopii
  dělat přes `sqlite3.Connection.backup`, když do originálu zapisuje stahování.

## Mapa projektu

- `importer/` – UNL z otevřených dat PSP → SQLite (`opendata.py`: tabulka = popis `Tabulka`)
- `dokumenty/` – vše z psp.cz mimo otevřená data: úseky stenozáznamů, odkazy na soubory tisků
  (PDF, DOCX se nestahují), mapa kanceláří, fotky; `stahovani.Stahovac` = jediné místo pro HTTP na psp.cz
- `parovani/` – hlasování → úryvek stenozáznamu → druh předmětu, označení návrhu, dokument
- `analyza/` – předpočet (`hlas_klub`, `klub_hlasovani`) a statistiky (docházka, proti klubu…)
- `db/schema.sql`, `db/connection.py` (verze schématu), `db/dotazy/` – čtecí dotazy po sekcích
- `web/` – FastAPI routy po sekcích, šablony Jinja2 (`_makra.html` sdílené), CSS proměnné
  v `static/css/base.css`
- `docs/specs/` – návrh aplikace a průzkum dat (proč je to takhle)

## Rozhodnutí a pravidla tohoto projektu

- Data z otevřených dat PSP; HTML stránky psp.cz jen tam, kde otevřená data chybí (rozhodnutí 1A,
  viz spec) – vždy přes `Stahovac`, uložit do `data/` a znovu nestahovat.
- psp.cz posílá `Connection: close` a omezuje nová spojení → stahovat co nejméně požadavků
  (úseky stenozáznamu jen kolem hlasování podle časů ze `steno.unl`), pauza 1 s, při výpadku
  postupné čekání. Nikdy paralelně.
- Tabulky z otevřených dat se při importu celé přepisují; změna jejich sloupců = zvýšit
  `SCHEMA_VERZE`. Tabulky aplikace (`dokument`, `predmet_hlasovani`, `kancelar`, `sledovany`) import nemaže.
- Předmět hlasování je fakt ze stenozáznamu (úryvek + odkaz); co se nezjistí, zůstane „nezjištěno“.
  Žádné domýšlení. AI shrnutí je odložené.
- Stahování z psp.cz jen v nočním okně (`config.NOCNI_OKNO`, 22–6 h); mimo něj `--ihned`.
  User-Agent nese kontakt jen z proměnné prostředí `POLITIKA_KONTAKT` – osobní údaje ne do repa.
- Odchylka od L1 (web-frontend): výchozí ověření UI 1440 px a 390 px platí; přepínač režimu
  je na mobilu v menu.

## Body napojení

- Otevřená data `https://www.psp.cz/eknih/cdrom/opendata/*.zip` – UNL, `|`, Windows-1250,
  denní kompletní snímek; pozor: hlasování se objeví s denním zpožděním.
- Stenozáznam úseku `/eknih/2025ps/stenprot/NNNschuz/sNNNttt.htm` – vyhlášení výsledku je
  odkaz `hlasy.sqw?G=<id_hlasovani>`; pozor: automatické odkazy občas chybují (kontrola data)
  a večerní část jednání vychází se zpožděním dní.
- Soubory tisků: `/sqw/historie.sqw?T=ct&O=10` (SD → DOCX), `/sqw/text/tiskt.sqw?o=10&ct=…&ct1=…` (PDF).
- Kanceláře `/sqw/pk.sqw` (souřadnice v JS), fotky `/eknih/cdrom/2025ps/eknih/2025ps/poslanci/i{id_osoba}.jpg`.

Stav práce: viz `STATUS.md`.
