# Sledování poslanců

Webová aplikace pro přehledné sledování Poslanecké sněmovny PČR. Hlavní otázka, kterou
řeší: **jak poslanec hlasoval a o čem se doopravdy hlasovalo**. Oficiální web u hlasování
uvádí jen bod schůze. Aplikace dohledá ve stenozáznamu, co předsedající dal hlasovat
(pozměňovací návrh B2, návrh jako celek, procedurální návrh…), a nabídne znění návrhu.

Co umí:

- **Přehled a Sledovaní:** proud hlasování vybraných poslanců a klubů, ve skupinách,
  se zvýrazněním hlasování proti vlastnímu klubu,
- **Poslanci:** profil s docházkou, hlasováním proti klubu, vystoupeními, návrhy zákonů,
  výbory a regionální kanceláří,
- **Hlasování:** všechna hlasování s filtry, detail s půlkruhem sněmovny a předmětem
  ze stenozáznamu,
- **Zákony:** průběh projednávání, znění v PDF, pozměňovací návrhy (čitelné přímo v aplikaci),
  hlasování k tisku, odkaz do Sbírky zákonů,
- **Schůze, Statistiky** (účast, kdo nepromluvil, rebelové, jednota a shoda klubů),
  **Mapa** kanceláří, globální hledání (`34/288` otevře hlasování), export do CSV.

## Instalace

Potřebuješ [uv](https://docs.astral.sh/uv/) (Python si stáhne sám).

```bash
git clone <adresa repozitáře> && cd politics_review_CZ
uv sync
```

## První spuštění

```bash
uv run politika import            # otevřená data PSP → databáze (asi minuta)
uv run politika stahni-dokumenty  # stenozáznamy, soubory tisků, kanceláře, fotky
uv run politika paruj             # předmět hlasování ze stenozáznamů
uv run politika web               # http://127.0.0.1:8000
```

`stahni-dokumenty` poprvé trvá **několik hodin**. Server psp.cz omezuje počet spojení, proto
aplikace stahuje šetrně, po jednom souboru s pauzou. Aplikaci můžeš používat hned, data
se průběžně doplňují. Když se stahování přeruší, příští běh pokračuje tam, kde skončil.

## Denní obnova

Sněmovna aktualizuje otevřená data jednou denně. Obnovu spouští jeden příkaz:

```bash
uv run politika obnova
```

- **Windows (Plánovač úloh):**
  `schtasks /Create /SC DAILY /ST 06:30 /TN "Sledovani poslancu" /TR "cmd /c cd /d E:\cesta\k\politics_review_CZ && uv run politika obnova >> data\obnova.log 2>&1"`
- **Linux (cron):** `30 6 * * * cd /cesta/k/politics_review_CZ && uv run politika obnova >> data/obnova.log 2>&1`

Při chybě některého kroku skončí příkaz s kódem 1, ostatní kroky přesto doběhnou.

## Nastavení

| Co | Kde |
|---|---|
| Složka s daty, soubor databáze | proměnné prostředí `POLITIKA_DATA`, `POLITIKA_DB` |
| Volební období, pauza mezi požadavky na psp.cz | `src/politika/config.py` |
| Přístup z domácí sítě | `uv run politika web --host 0.0.0.0 --port 8000` |
| Barvy, písmo (oba režimy) | `src/politika/web/static/css/base.css` (proměnné v `:root`) |
| Sekce v menu | `MENU` v `src/politika/web/app.py` |

## Zdroje dat

- [Otevřená data Poslanecké sněmovny PČR](https://www.psp.cz/sqw/hp.sqw?k=1300) a veřejně
  zveřejněné stenozáznamy a dokumenty na psp.cz. Data se do repozitáře nedávají, každá
  instalace si je stáhne sama.
- Mapové podklady © přispěvatelé [OpenStreetMap](https://www.openstreetmap.org/copyright).

## Omezení

- Nejnovější hlasování se v otevřených datech objeví s denním zpožděním. Stenozáznam
  (a tedy předmět hlasování) vychází za několik hodin až dní, večerní jednání bývá
  zveřejněné nejpozději.
- Předmět hlasování se hledá automaticky podle textu stenozáznamu. Když ho předsedající
  neuvede číslem, aplikace napíše „nezjištěno“ a odkáže na zdroj.
- Ústní interpelace zatím v otevřených datech pro aktuální období nejsou.

## Vývoj

```bash
PYTHONUTF8=1 uv run pytest -q
uv run politika web --reload
```

Návrh aplikace a průzkum dat jsou v `docs/specs/`.
