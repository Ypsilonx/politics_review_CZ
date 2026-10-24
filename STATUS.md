# STATUS

## Cíl
Webová aplikace pro sledování poslanců PSP ČR: jak hlasovali a o čem se doopravdy hlasovalo
(stenozáznam, znění návrhů), profily, statistiky, zákony, schůze, mapa kanceláří.
Návrh: `docs/specs/2026-10-24-sledovani-poslancu-design.md`.

## Hotovo
- Plán v2 (T0–T10) dokončen: import otevřených dat, stahování dokumentů, párování předmětu
  hlasování (schůze 34: 261/282), všechny sekce webu, CSV export, globální hledání,
  příkaz `obnova`, README, projektový CLAUDE.md.

## Rozpracováno
- První kompletní stažení dokumentů celého období běží (`stahni-dokumenty`, hodiny), pak
  `uv run politika paruj` pro všechny schůze.

## Další krok
- Nezávislá revize kódu celého projektu (dle plánu po T10).
- Naplánovat denní `obnova` (Plánovač úloh).
- Později: AI shrnutí návrhů, dění kolem politika na webu, veřejné nasazení (licence, přihlášení).

## Otevřené otázky / slepé uličky
- ZIPy stenozáznamů po schůzích (`/stenprot/zip/NNNschuz.zip`) pro 2025ps vracejí 404 → stahují se úseky.
- `steno.zip` v otevřených datech má jen metadata (úseky s časy, řečníci), ne texty.
- Stahovat všechny úseky stenozáznamů (~4300) je pomalé: psp.cz posílá `Connection: close`
  a omezuje nová spojení (výpadky TCP/TLS) → jen úseky kolem hlasování (~27 %).
- Odkazy na soubory tisků nejsou v otevřených datech → `historie.sqw` a `tiskt.sqw` (rozhodnutí 1A).
- Pozměňovací návrhy jsou jen DOCX → převod na HTML přes mammoth (2A).
- Ústní interpelace (`interp.zip`) zatím nemají data pro období 2025 → v profilu nejsou.
- Před zveřejněním na GitHubu: licence (návrh MIT), kontrola osobních údajů (autor v pyproject.toml).
