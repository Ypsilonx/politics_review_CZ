# STATUS

## Cíl
Webová aplikace pro sledování poslanců PSP ČR: jak hlasovali a o čem se doopravdy hlasovalo
(stenozáznam, znění návrhů), profily, statistiky, zákony, schůze, mapa kanceláří.
Návrh: `docs/specs/2026-10-24-sledovani-poslancu-design.md`.

## Hotovo
- Plán v2 (T0–T10) dokončen: import otevřených dat, stahování dokumentů, párování předmětu
  hlasování (schůze 34: 261/282), všechny sekce webu, CSV export, globální hledání,
  příkaz `obnova`, README, projektový CLAUDE.md.
- Revize kódu (9 nálezů) opravena. Stahování z psp.cz jen v noci 22–6 h (`--ihned` mimo okno),
  kontakt v User-Agentu z `POLITIKA_KONTAKT`, soubory tisků a návrhů jen jako odkazy na psp.cz.

## Rozpracováno
- První kompletní stažení stenozáznamů (hotovo schůze 35–25, zbytek po nocích přes `obnova`).

## Další krok
- Naplánovat denní `obnova` ve 22:05 (Plánovač úloh, příkaz v README) – vytvoří uživatel.
- Ověřit `obnova` 2× po sobě (druhý běh nemá nic stahovat).
- Později: AI shrnutí návrhů, dění kolem politika na webu, veřejné nasazení (licence, přihlášení).

## Otevřené otázky / slepé uličky
- ZIPy stenozáznamů po schůzích (`/stenprot/zip/NNNschuz.zip`) pro 2025ps vracejí 404 → stahují se úseky.
- `steno.zip` v otevřených datech má jen metadata (úseky s časy, řečníci), ne texty.
- Stahovat všechny úseky stenozáznamů (~4300) je pomalé: psp.cz posílá `Connection: close`
  a omezuje nová spojení (výpadky TCP/TLS) → jen úseky kolem hlasování (~27 %).
- Odkazy na soubory tisků nejsou v otevřených datech → `historie.sqw` a `tiskt.sqw` (rozhodnutí 1A).
- Pozměňovací návrhy jsou jen DOCX; převod na HTML (mammoth) zrušen – uživatel čte jen část,
  stahování všeho zbytečně zatěžovalo psp.cz → odkaz na originál.
- Ústní interpelace (`interp.zip`) zatím nemají data pro období 2025 → v profilu nejsou.
- Před zveřejněním na GitHubu: licence (návrh MIT), kontrola osobních údajů (autor v pyproject.toml).
