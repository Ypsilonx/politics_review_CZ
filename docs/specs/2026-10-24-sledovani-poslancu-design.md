# Sledování poslanců – design (v1)

## Cíl
Osobní webová aplikace, přehlednější než psp.cz: po spuštění hned ukáže dění u sledovaných
politiků, hlavně **jak hlasovali a o čem se doopravdy hlasovalo**. U každého hlasování je
konkrétní předmět („pozměňovací návrh B2 posl. X“, „návrh jako celek“), úryvek ze
stenozáznamu a odkaz na PDF návrhu, které jde otevřít přímo v aplikaci.
Hotovo v1 = vyberu politika a u jeho hlasování vidím, o čem bylo, a otevřu příslušné PDF.

## Rozsah
- **Ano (v1):** hlasování s popisem z faktů (stenozáznam a dokumenty), sledovaní
  (jeden poslanec / strana / vlastní seznam, kdykoliv změnitelní), proud novinek na úvodní
  stránce, detail hlasování (všichni poslanci, po klubech, odkaz na psp.cz jako zdroj),
  profil poslance (historie hlasování, docházka, hlasování proti klubu).
- **Později:** AI shrnutí obsahu návrhů (oddělené „co návrh dělá“ / „možné dopady – odhad AI“),
  dění kolem politika jinde na webu (samostatný návrh), veřejné nasazení.
- **Ne:** získávání dat z webových stránek psp.cz (scraping HTML stránek), sociální sítě.
- **Anti-cíl:** aplikace vydává odhad za fakt. Když se předmět hlasování nepodaří zjistit,
  napíše „nezjištěno“ a nabídne odkaz na zdroj.

## Klíčová rozhodnutí
- **Zdroj dat:** otevřená data PSP (`psp.cz/eknih/cdrom/opendata/`): `poslanci.zip`,
  `hl-2025ps.zip`, `schuze.zip`, `tisky.zip`, `steno.zip`, `sd.zip`. Jde o tabulky UNL
  (oddělovač `|`, kódování Windows-1250). Aktualizují se **denně**, vždy jako kompletní snímek.
  Proto se obnovuje 1× denně (plánovaná úloha) a import probíhá idempotentně.
- **Dokumenty (PDF návrhů, texty stenozáznamů):** stahují se zveřejněné soubory, každý jen
  jednou, pomalu (pauza mezi požadavky). Ukládají se na jedno místo `data/` s pevnou strukturou
  (`data/opendata/`, `data/steno/`, `data/dokumenty/`). Preferované je PDF.
- **Předmět hlasování:** ve stenozáznamu se najde věta s „hlasování (pořadové) číslo N“
  a uloží se úryvek kolem ní. Z úryvku se pravidly vytáhne označení návrhu (A1, B2…)
  a spáruje se s dokumentem pozměňovacích návrhů k tisku. Pokud spárování selže,
  zůstane úryvek a vazba na tisk.
- **Stack (moje volba):** Python + FastAPI, šablony Jinja2 + HTMX (bez JS bundleru),
  databáze **SQLite**. Jeden soubor, žádný server navíc, na domácí server stačí.
  Na PostgreSQL by šlo přejít, kdyby přišel veřejný provoz.
- **Přihlášení (moje volba):** v1 bez přihlašování, aplikace běží jen v domácí síti.
  Řeší se až při veřejném nasazení.
- **„Proti klubu“ (moje volba):** hlas poslance se liší od většinového hlasu jeho klubu
  v daném hlasování (Ano/Ne). Nepřítomnost a zdržení se počítají zvlášť.
- **Období:** v1 importuje 10. volební období (2025–). Struktura dovolí přidat starší.

## Moduly
- `importer/`: stažení ZIPů, parsování UNL a import do DB (poslanci, hlasování, schůze, tisky).
- `dokumenty/`: stahování a evidence stenozáznamů a PDF (cache, pauzy mezi požadavky).
- `parovani/`: vazba hlasování → úryvek ze stenozáznamu → označení návrhu → PDF.
- `analyza/`: docházka, hlasování proti klubu, jednota klubu.
- `web/`: FastAPI, šablony (proud, profil, detail hlasování, správa sledovaných, prohlížeč PDF).
- `db/`: schéma SQLite a přístup k datům.

## Otevřené otázky (ověřit v prvních tascích)
1. Co přesně obsahuje `steno.zip`: plné texty, nebo jen metadata (řečník, strana stenozáznamu,
   bod)? Když jen metadata, jsou plné texty dostupné jako soubory ke stažení
   (např. ZIP za schůzi)?
2. Kde se v datech ukazuje na soubor s pozměňovacími návrhy (PDF) k tisku: tabulky v `tisky.zip`,
   nebo `sd.zip`?
3. Jak úspěšné je párování „hlasování → označení návrhu“ na reálné schůzi (měřit na 34. schůzi).
4. Úvodní stránka: co nahoře a co dole. Doladíme nad mockupem.
