# Sledování poslanců – design (v2)

## Cíl
Osobní webová aplikace (později případně veřejná), přehlednější než psp.cz. Po spuštění ukáže
dění u sledovaných politiků. Jádro: **jak hlasovali a o čem se doopravdy hlasovalo** (předmět
ze stenozáznamu, znění zákona a návrhů k otevření). Kolem jádra jsou profily poslanců,
statistiky, zákony, schůze a mapa kanceláří.

## Sekce (horní menu, tmavý režim výchozí + přepínač na světlý)
- **Přehled:** proud novinek sledovaných (zvýraznění: hlasoval proti klubu, chyběl u závěrečného
  hlasování), rychlé statistiky, nejbližší schůze.
- **Sledovaní:** zaškrtnutí poslanci, strany a vlastní skupiny, jejich hlasování na jednom místě a filtry.
- **Poslanci:** karty s fotkou a klubem, filtry podle klubu a kraje. **Profil:** foto, klub, kraj,
  výbory a funkce, kontakty, regionální kancelář, docházka (přítomen / omluven / neomluven),
  hlasování proti klubu, vystoupení, návrhy zákonů, pozměňovací návrhy, interpelace, hlasování.
- **Hlasování:** všechna hlasování s filtry (schůze, tisk, výsledek, těsná). Detail: předmět ze
  stenozáznamu + úryvek, návrh (PDF/DOCX), kluby, zdroj.
- **Zákony:** tisky – stav v legislativním procesu, znění (PDF), pozměňovací návrhy, hlasování
  k tisku, odkaz do Sbírky zákonů.
- **Schůze:** seznam, pořad bodů, hlasování po bodech.
- **Statistiky:** účast a neomluvené absence, kdo nepromluvil / mluví nejvíc, rebelové,
  jednota klubů, matice shody klubů, nejtěsnější hlasování.
- **Mapa:** regionální kanceláře poslanců (shlukování, filtr klub/kraj).
- Napříč aplikací: globální hledání (poslanec, číslo tisku, název), export tabulek do CSV.

## Rozsah
- **Později:** AI shrnutí (oddělené „co návrh dělá“ / „možné dopady – odhad AI“), dění kolem
  politika na webu, e-mailová upozornění, veřejné nasazení (přihlášení, GDPR).
- **Ne:** sociální sítě.
- **Anti-cíl:** odhad vydávaný za fakt. Když se předmět nezjistí, aplikace napíše „nezjištěno“
  a dá odkaz na zdroj.

## Klíčová rozhodnutí
- **Data:** otevřená data PSP (denní kompletní snímek): poslanci, hlasování, omluvy, schůze, tisky,
  stenozáznamy (metadata vystoupení), sněmovní dokumenty, interpelace, Sbírka. Obnova 1× denně.
- **Mimo otevřená data** (rozhodnutí 1A, jen pár stránek, uložené a obnovované jen při změně):
  texty stenozáznamů (soubory úseků `sNNNxxx.htm`), odkazy na soubory tisků a návrhů
  (`historie.sqw`, `tiskt.sqw`), mapa kanceláří (`pk.sqw`, souřadnice jsou přímo ve stránce),
  fotky poslanců (`/eknih/cdrom/2025ps/eknih/2025ps/poslanci/…/{id_osoba}.jpg`).
- **Dokumenty** v `data/` (`opendata/`, `steno/`, `dokumenty/`, `foto/`). Soubory tisků a návrhů
  (PDF, DOCX) se nestahují. Aplikace na ně odkazuje na psp.cz, uživatel si otevře jen to, co
  chce číst (méně požadavků na psp.cz). Stahování z psp.cz běží jen v nočním okně 22–6 h.
- **Stack:** Python 3.14 + FastAPI, Jinja2 + HTMX, SQLite. Mapa: Leaflet + OpenStreetMap.
  Grafy jen přes CSS/SVG, bez knihovny, dokud to stačí.
- **Přihlášení:** v1 žádné (domácí síť).
- **„Proti klubu“:** Ano/Ne poslance se liší od většinového Ano/Ne klubu k datu hlasování.
  Remíza v klubu se nepočítá. Absence a zdržení se počítají zvlášť.
- **Období:** 10. volební období (2025–), struktura dovolí přidat starší.
- **Distribuce:** později veřejný repozitář na GitHubu, ze kterého si aplikaci kdokoliv stáhne
  a spustí u sebe. Data se do repa nedávají, každá instalace si je stáhne z psp.cz sama.
  Mapa používá OpenStreetMap: při provozu u jednotlivce stačí, atribuce je povinná.
  Před zveřejněním: licence (návrh MIT), README pro instalaci, kontrola, že v repu nejsou osobní údaje.

Průzkum dat: `docs/specs/2026-10-24-pruzkum-dat.md`.
