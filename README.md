# Sledování poslanců

> Neoficiální projekt. Nesouvisí s Poslaneckou sněmovnou PČR a není jí podporovaný.
> Údaje pochází z jejích otevřených dat a webu; za správnost odvozených údajů (předmět
> hlasování, statistiky) neručím – v pochybnostech platí stenozáznam a web psp.cz.

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
- **Zákony:** průběh projednávání, odkazy na znění (PDF) a pozměňovací návrhy (DOCX) na psp.cz,
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
uv run politika stahni-dokumenty  # stenozáznamy, odkazy na tisky, kanceláře, fotky (v noci)
uv run politika paruj             # předmět hlasování ze stenozáznamů
uv run politika web               # http://127.0.0.1:8000
```

`stahni-dokumenty` poprvé trvá **několik hodin**. Server psp.cz omezuje počet spojení, proto
aplikace stahuje šetrně, po jednom souboru s pauzou, a jen v noci (22–6 h). V 6 h se stahování
samo ukončí a další běh pokračuje tam, kde skončil. Mimo noční okno se stahuje jen s `--ihned`.
Soubory tisků a pozměňovacích návrhů (PDF, DOCX) se nestahují. Aplikace na ně odkazuje
na psp.cz. Aplikaci můžeš používat hned, data se průběžně doplňují.

## Denní obnova

Sněmovna aktualizuje otevřená data jednou denně. Nejjednodušší je tlačítko **Aktualizovat data**
na Přehledu: přes den stáhne otevřená data a stenozáznamy schůzí z posledních 7 dní
(`DNY_CERSTVYCH` v `src/politika/config.py`), v nočním okně dostáhne i starší. Výpis běhu je
v `data/aktualizace.log`. Totéž z příkazové řádky, případně naplánované:

```bash
uv run politika obnova
```

- **Windows (Plánovač úloh):**
  `schtasks /Create /SC DAILY /ST 22:30 /TN "Sledovani poslancu" /TR "cmd /c cd /d E:\cesta\k\politics_review_CZ && uv run politika obnova >> data\obnova.log 2>&1"`
- **Linux (cron):** `30 22 * * * cd /cesta/k/politics_review_CZ && uv run politika obnova >> data/obnova.log 2>&1`

Při chybě některého kroku skončí příkaz s kódem 1, ostatní kroky přesto doběhnou.

## Nastavení

| Co | Kde |
|---|---|
| Složka s daty, soubor databáze | proměnné prostředí `POLITIKA_DATA`, `POLITIKA_DB` |
| Volební období, pauza mezi požadavky, noční okno (`NOCNI_OKNO`) | `src/politika/config.py` |
| Kontakt v User-Agentu pro správce psp.cz (e-mail) | proměnná prostředí `POLITIKA_KONTAKT` |
| Přístup z domácí sítě (ne z internetu, viz Bezpečnost) | `uv run politika web --host 0.0.0.0 --port 8000` |
| Barvy, písmo (oba režimy) | `src/politika/web/static/css/base.css` (proměnné v `:root`) |
| Sekce v menu | `MENU` v `src/politika/web/app.py` |

## Zdroje dat

- [Otevřená data Poslanecké sněmovny PČR](https://www.psp.cz/sqw/hp.sqw?k=1300) a veřejně
  zveřejněné stenozáznamy a dokumenty na psp.cz. Podmínkou využití dat je uvedení zdroje
  a data zpracování – aplikace je uvádí v patičce každé stránky. Data se do repozitáře
  nedávají, každá instalace si je stáhne sama.
- Fotografie poslanců jsou z webu psp.cz a patří jeho provozovateli. Aplikace je stahuje
  jen pro zobrazení v lokální instalaci, nešiř je dál.
- Mapové podklady © přispěvatelé [OpenStreetMap](https://www.openstreetmap.org/copyright).

## Šetrnost k psp.cz

Web psp.cz není API; aplikace z něj bere jen to, co v otevřených datech chybí. Pokud ji
používáš, prosím:

- nastav si kontakt, aby správci serveru věděli, komu napsat, místo aby přístup blokovali:
  `setx POLITIKA_KONTAKT tvuj@email.cz` (Windows) / `export POLITIKA_KONTAKT=…` (Linux),
- nesnižuj `PAUZA_MEZI_POZADAVKY`, nevypínej noční okno (`NOCNI_OKNO`) a nespouštěj
  stahování paralelně – server omezuje počet spojení a hromadné stahování ho zatěžuje.

## Bezpečnost

Aplikace nemá přihlášení a je určená pro jeden počítač nebo domácí síť. **Nevystavuj ji
do internetu** – kdokoli by mohl spouštět stahování z psp.cz a měnit sledované. Pro veřejný
provoz by bylo potřeba přihlášení a jiný poskytovatel mapových podkladů (dlaždice
OpenStreetMap nejsou pro provoz s větší návštěvností).

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

## Licence

Kód je pod licencí [MIT](LICENSE). Licence se nevztahuje na data z psp.cz (viz Zdroje dat).
