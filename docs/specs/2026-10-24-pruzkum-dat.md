# Průzkum dat PSP (Task 0, 2026-10-24)

## Otevřená data (`/eknih/cdrom/opendata/*.zip`)
- UNL: oddělovač `|`, řádek končí `|`, Windows-1250. Ověřeno.
- `hl-2025ps.zip`: `hl2025s.unl` (hlasování), `hl2025h1.unl` (hlasy poslanců, `h2` je zatím prázdný),
  `omluvy.unl`, `zmatecne.unl`.
  `hl2025s` sloupce: id_hlasovani, id_organ (174 = PS 2025), schuze, cislo, bod, datum, cas, pro,
  proti, zdrzel, nehlasoval, prihlaseno, kvorum, druh, vysledek (A/R…), nazev_dlouhy, nazev_kratky.
- **Zpoždění:** snímek z 24. 10. ráno končí hlasováním 34/282 (23. 10. 23:29). Hlasování 288
  (24. 10. 4:40) v něm ještě není.
- **Název hlasování často chybí** (např. 34/256–270 mají prázdný název; jde o procedurální hlasování).
- `schuze.zip` → `bod_schuze.unl`: bod schůze → id_tisk (tisk 231 = id_tisk 43353).
- `tisky.zip` → `tisky.unl`: id_tisk, …, ct (číslo tisku, sl. 4), id_obdobi (sl. 8), název. **Neobsahuje odkazy na soubory.**
- `sd.zip` → `sd_dokument.unl`: sněmovní dokumenty (pozměňovací návrhy = typ 13), sl. 3 = číslo SD,
  sl. 7 = číslo tisku, sl. 8 = id_osoba autora, sl. 9 = datum. **Bez odkazu na soubor.**
- `steno.zip`: **jen metadata** (`steno.unl` = úseky (turny) schůze, `rec.unl` = řečníci,
  `steno_bod.unl` = úsek ↔ bod). Plné texty neobsahuje.

## Stenozáznamy (texty)
- ZIPy po schůzích (`/eknih/2025ps/stenprot/zip/NNNschuz.zip`) jsou na webu uvedené, ale **vracejí 404**
  (pro 2025ps zkoušeny 033 a 034). Pro 2021ps fungují, takže jde o chybu na straně serveru.
- Funkční cesta: den `034schuz/34-8.html` → odkazy na úseky `034schuz/s034NNN.htm` (cca 10 min jednání,
  Windows-1250). Vycházejí se zpožděním několika hodin a jako „neautorizováno“.
- **Pravidlo pro předmět:** číslo zazní až po hlasování („Hlasování číslo 274, přihlášeno 152…“).
  Předmět je v textu **před** ním, od předchozího hlasování („hlasujeme návrh pana poslance Bendy,
  aby pevné hlasování bylo…“). Úryvek = text od konce předchozí zmínky „hlasování číslo N-1“ po „hlasování číslo N“.
  Číslo se ale občas vůbec nevysloví (34/257, 258 …) → `nezjisteno`.

## Pozměňovací návrhy a tisky (soubory)
- Tisk 231 je teprve v 1. čtení a pozměňovací návrhy nemá. Hlasování 34/280–288 jsou procedurální.
- Tisk 213 (2. čtení): jednotlivé návrhy (SD) jsou jen **DOCX** (`orig2.sqw?idd=…`). ID souboru (`idd`)
  je jen na stránce `historie.sqw?T=213&O=10`.
- Verze tisku (213/0, 213/3 …) mají **PDF** i DOCX. Odkazy jsou na stránce `text/tiskt.sqw?o=10&ct=213&ct1=3`
  → `orig2.sqw?idd=281676` (application/pdf, ověřeno). Statická cesta `/eknih/2025ps/tisky/*.pdf` neexistuje.
- Neověřeno: souhrnný dokument návrhů s písmeny (A1, B2…) po 2. čtení. Tisk 213 má 3. čtení nejdřív 31. 10.
