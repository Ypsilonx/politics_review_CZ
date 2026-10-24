-- Schéma databáze. Tabulky z otevřených dat PSP se při importu celé přepisují
-- (zdroj je vždy kompletní snímek), proto nemají cizí klíče vynucené – snímky
-- jednotlivých ZIPů nemusí být k sobě v každém okamžiku konzistentní.

CREATE TABLE IF NOT EXISTS osoba (
    id_osoba    INTEGER PRIMARY KEY,
    titul_pred  TEXT,
    prijmeni    TEXT NOT NULL,
    jmeno       TEXT NOT NULL,
    titul_za    TEXT,
    narozeni    TEXT,
    pohlavi     TEXT
);

CREATE TABLE IF NOT EXISTS poslanec (
    id_poslanec INTEGER PRIMARY KEY,
    id_osoba    INTEGER NOT NULL,
    id_kraj     INTEGER,
    id_obdobi   INTEGER NOT NULL,  -- id_organ sněmovny daného období (174 = PS 2025)
    email       TEXT
);
CREATE INDEX IF NOT EXISTS ix_poslanec_osoba ON poslanec (id_osoba);

-- Orgány: sněmovna, kluby, výbory, strany… (id_typ 1 = poslanecký klub)
CREATE TABLE IF NOT EXISTS organ (
    id_organ     INTEGER PRIMARY KEY,
    id_nadrazeny INTEGER,
    id_typ       INTEGER NOT NULL,
    zkratka      TEXT,
    nazev        TEXT,
    od           TEXT,
    do           TEXT
);

-- Členství osoby v orgánu (jen členství, ne funkce).
CREATE TABLE IF NOT EXISTS zarazeni (
    id_osoba INTEGER NOT NULL,
    id_organ INTEGER NOT NULL,
    od       TEXT,
    do       TEXT
);
CREATE INDEX IF NOT EXISTS ix_zarazeni_osoba ON zarazeni (id_osoba);
CREATE INDEX IF NOT EXISTS ix_zarazeni_organ ON zarazeni (id_organ);

CREATE TABLE IF NOT EXISTS schuze (
    id_schuze INTEGER PRIMARY KEY,
    id_organ  INTEGER NOT NULL,
    cislo     INTEGER NOT NULL,
    od        TEXT,
    do        TEXT
);
CREATE INDEX IF NOT EXISTS ix_schuze_cislo ON schuze (id_organ, cislo);

CREATE TABLE IF NOT EXISTS bod (
    id_bod    INTEGER PRIMARY KEY,
    id_schuze INTEGER NOT NULL,
    id_tisk   INTEGER,
    cislo     INTEGER,
    nazev     TEXT,
    zkratka   TEXT,
    pozvanka  INTEGER                -- 1 = bod z pozvánky (návrh pořadu), jinak schválený pořad
);
CREATE INDEX IF NOT EXISTS ix_bod_schuze ON bod (id_schuze, cislo);

CREATE TABLE IF NOT EXISTS tisk (
    id_tisk     INTEGER PRIMARY KEY,
    ct          INTEGER,             -- číslo sněmovního tisku
    id_obdobi   INTEGER,
    id_druh     INTEGER,             -- druh_tisku (návrh zákona, mezinárodní smlouva…)
    id_stav     INTEGER,             -- stavy → typ_stavu (aktuální stav projednávání)
    navrhovatel TEXT,                -- např. „vláda“, „ministr kultury“, „poslanci“
    nazev       TEXT,
    uplny_nazev TEXT,
    predlozeno  TEXT,
    rozeslano   TEXT
);
CREATE INDEX IF NOT EXISTS ix_tisk_ct ON tisk (id_obdobi, ct);

CREATE TABLE IF NOT EXISTS druh_tisku (
    id_druh INTEGER PRIMARY KEY,
    nazev   TEXT
);

-- Stav tisku: stavy.id_typ → typ_stavu.popis.
CREATE TABLE IF NOT EXISTS stav_tisku (
    id_stav INTEGER PRIMARY KEY,
    id_typ  INTEGER,
    popis   TEXT
);
CREATE TABLE IF NOT EXISTS typ_stavu (
    id_typ INTEGER PRIMARY KEY,
    popis  TEXT
);

-- Legislativní historie tisku: událost (přechod mezi stavy) s datem.
CREATE TABLE IF NOT EXISTS hist_tisku (
    id_hist    INTEGER PRIMARY KEY,
    id_tisk    INTEGER NOT NULL,
    datum      TEXT,
    id_hlas    INTEGER,              -- hlasování, které událost rozhodlo
    id_prechod INTEGER,
    schuze     INTEGER
);
CREATE INDEX IF NOT EXISTS ix_hist_tisk ON hist_tisku (id_tisk, datum);
CREATE TABLE IF NOT EXISTS prechod (
    id_prechod INTEGER PRIMARY KEY,
    odkud      INTEGER,
    kam        INTEGER,              -- id_stav po události
    id_akce    INTEGER
);
CREATE TABLE IF NOT EXISTS typ_akce (
    id_akce INTEGER PRIMARY KEY,
    popis   TEXT
);

CREATE TABLE IF NOT EXISTS predkladatel (
    id_tisk  INTEGER NOT NULL,
    id_osoba INTEGER NOT NULL,
    poradi   INTEGER
);
CREATE INDEX IF NOT EXISTS ix_predkladatel_osoba ON predkladatel (id_osoba);
CREATE INDEX IF NOT EXISTS ix_predkladatel_tisk ON predkladatel (id_tisk);

-- Předpis ve Sbírce zákonů vzniklý z tisku.
CREATE TABLE IF NOT EXISTS sbirka (
    id_sbirka INTEGER PRIMARY KEY,
    cislo     INTEGER,
    rok       INTEGER,
    id_tisk   INTEGER,
    datum     TEXT
);
CREATE INDEX IF NOT EXISTS ix_sbirka_tisk ON sbirka (id_tisk);

-- Sněmovní dokumenty (typ 13 = písemný pozměňovací návrh k tisku ct).
CREATE TABLE IF NOT EXISTS sd (
    id_dokument INTEGER PRIMARY KEY,
    id_organ    INTEGER,
    cislo       INTEGER,
    typ         INTEGER,
    nazev       TEXT,
    ct          INTEGER,
    id_osoba    INTEGER,
    datum       TEXT
);
CREATE INDEX IF NOT EXISTS ix_sd_osoba ON sd (id_osoba);
CREATE INDEX IF NOT EXISTS ix_sd_tisk ON sd (id_organ, ct);

-- Úseky stenozáznamu (metadata): čas od/do v minutách od půlnoci.
CREATE TABLE IF NOT EXISTS steno (
    id_steno INTEGER PRIMARY KEY,
    id_organ INTEGER,
    schuze   INTEGER,
    turn     INTEGER,
    datum    TEXT,
    den      INTEGER,                -- pořadí jednacího dne schůze (34-8.html → 8)
    od_t     INTEGER,
    do_t     INTEGER
);
CREATE INDEX IF NOT EXISTS ix_steno_schuze ON steno (id_organ, schuze, turn);

-- Vystoupení: druh 2/4 = předsedající, 3/5 = řečník, 0/1 = nezpracováno.
CREATE TABLE IF NOT EXISTS vystoupeni (
    id_steno INTEGER NOT NULL,
    id_osoba INTEGER NOT NULL,
    aname    INTEGER,
    id_bod   INTEGER,
    druh     INTEGER
);
CREATE INDEX IF NOT EXISTS ix_vystoupeni_osoba ON vystoupeni (id_osoba);

-- Omluvy z jednání sněmovny (den a případně časový úsek).
CREATE TABLE IF NOT EXISTS omluva (
    id_organ    INTEGER,
    id_poslanec INTEGER NOT NULL,
    den         TEXT,
    od          TEXT,
    do          TEXT
);
CREATE INDEX IF NOT EXISTS ix_omluva_poslanec ON omluva (id_poslanec, den);

-- Funkce v orgánech (předseda výboru…): zarazeni s cl_funkce = 1 → funkce → typ_funkce.
CREATE TABLE IF NOT EXISTS funkce (
    id_funkce INTEGER PRIMARY KEY,
    id_organ  INTEGER,
    id_typ    INTEGER,
    nazev     TEXT
);
CREATE TABLE IF NOT EXISTS typ_funkce (
    id_typ INTEGER PRIMARY KEY,
    nazev  TEXT
);
CREATE TABLE IF NOT EXISTS zarazeni_funkce (
    id_osoba  INTEGER NOT NULL,
    id_funkce INTEGER NOT NULL,
    od        TEXT,
    do        TEXT
);
CREATE INDEX IF NOT EXISTS ix_zarazeni_funkce_osoba ON zarazeni_funkce (id_osoba);
CREATE TABLE IF NOT EXISTS typ_organu (
    id_typ INTEGER PRIMARY KEY,
    nazev  TEXT
);

CREATE TABLE IF NOT EXISTS hlasovani (
    id_hlasovani INTEGER PRIMARY KEY,
    id_organ     INTEGER NOT NULL,
    schuze       INTEGER NOT NULL,
    cislo        INTEGER NOT NULL,
    bod          INTEGER,
    datum        TEXT NOT NULL,     -- ISO yyyy-mm-dd
    cas          TEXT,
    pro          INTEGER,
    proti        INTEGER,
    zdrzel       INTEGER,
    nehlasoval   INTEGER,
    prihlaseno   INTEGER,
    kvorum       INTEGER,
    druh         TEXT,
    vysledek     TEXT,              -- A = přijato, R = zamítnuto, …
    nazev_dlouhy TEXT,
    nazev_kratky TEXT
);
CREATE INDEX IF NOT EXISTS ix_hlasovani_schuze ON hlasovani (id_organ, schuze, cislo);
CREATE INDEX IF NOT EXISTS ix_hlasovani_datum ON hlasovani (datum);

-- Hlas poslance: A = ano, B/N = ne, C = zdržel se, F = nehlasoval, @ = nepřihlášen,
-- M = omluven, W = před slibem, K = zdržel se / nehlasoval.
CREATE TABLE IF NOT EXISTS hlas (
    id_poslanec  INTEGER NOT NULL,
    id_hlasovani INTEGER NOT NULL,
    vysledek     TEXT NOT NULL,
    PRIMARY KEY (id_hlasovani, id_poslanec)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS ix_hlas_poslanec ON hlas (id_poslanec, id_hlasovani);

-- Dokumenty z psp.cz mimo otevřená data: stažené stránky (stenozáznamy, historie a verze tisků)
-- a odkazy na soubory tisků a návrhů (PDF, DOCX se nestahují, cesta je NULL).
-- Tabulku plní stahování dokumentů, import otevřených dat ji nepřepisuje.
-- typ: steno_den, steno_usek, tisk_historie, tisk_verze, tisk_pdf, sd_docx
CREATE TABLE IF NOT EXISTS dokument (
    url          TEXT PRIMARY KEY,   -- relativní k https://www.psp.cz nebo absolutní
    typ          TEXT NOT NULL,
    cesta        TEXT,               -- relativní k DATA_DIR; NULL = jen odkaz, nestaženo
    schuze       INTEGER,
    poradi       INTEGER,            -- pořadí úseku stenozáznamu v rámci schůze
    ct           INTEGER,            -- číslo tisku
    ct1          INTEGER,            -- verze tisku (213/3 → 3)
    cislo_sd     INTEGER,
    id_osoba     INTEGER,            -- autor pozměňovacího návrhu
    nazev        TEXT,
    popis        TEXT,
    datum        TEXT,
    autorizovano INTEGER,            -- u úseků stenozáznamu: 1 = autorizovaná verze
    stazeno      TEXT NOT NULL       -- ISO čas posledního stažení
);
CREATE INDEX IF NOT EXISTS ix_dokument_schuze ON dokument (typ, schuze, poradi);
CREATE INDEX IF NOT EXISTS ix_dokument_tisk ON dokument (typ, ct);

-- Předmět hlasování zjištěný ze stenozáznamu (plní `politika paruj`, import ho nepřepisuje).
-- druh: pozmenovaci | celek | proceduralni | jine
CREATE TABLE IF NOT EXISTS predmet_hlasovani (
    id_hlasovani  INTEGER PRIMARY KEY,
    uryvek        TEXT NOT NULL,      -- text stenozáznamu před vyhlášením výsledku
    otazka        TEXT,               -- věta, kterou předsedající hlasování uvedl
    druh          TEXT NOT NULL,
    oznaceni      TEXT,               -- označení pozměňovacího návrhu (B2, A1.3)
    zdroj_url     TEXT,               -- úsek stenozáznamu s vyhlášením (relativní URL)
    dokument_url  TEXT,               -- tisk s pozměňovacími návrhy (PDF), je-li znám
    autorizovano  INTEGER             -- 1 = úryvek z autorizovaného stenozáznamu
);

-- Předpočty pro statistiky (plní analyza.predpocet po importu, z tabulek výše).
-- Hlas poslance s klubem, jehož byl v den hlasování členem (B/N sjednoceno na B).
CREATE TABLE IF NOT EXISTS hlas_klub (
    id_hlasovani INTEGER NOT NULL,
    id_poslanec  INTEGER NOT NULL,
    vysledek     TEXT NOT NULL,
    id_klub      INTEGER,
    PRIMARY KEY (id_hlasovani, id_poslanec)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS ix_hlas_klub_poslanec ON hlas_klub (id_poslanec);
-- Většinový hlas klubu v hlasování (A / B, NULL = remíza nebo nikdo z klubu nehlasoval A/B).
CREATE TABLE IF NOT EXISTS klub_hlasovani (
    id_hlasovani INTEGER NOT NULL,
    id_klub      INTEGER NOT NULL,
    ano          INTEGER NOT NULL,
    ne           INTEGER NOT NULL,
    vetsina      TEXT,
    PRIMARY KEY (id_hlasovani, id_klub)
) WITHOUT ROWID;

-- Regionální kanceláře poslanců (z mapy na psp.cz, plní dokumenty.kancelare).
CREATE TABLE IF NOT EXISTS kancelar (
    id_osoba INTEGER NOT NULL,
    lat      REAL NOT NULL,
    lng      REAL NOT NULL,
    adresa   TEXT,
    skupina  TEXT                    -- název pole na mapě psp.cz (addressPoints…)
);
CREATE INDEX IF NOT EXISTS ix_kancelar_osoba ON kancelar (id_osoba);

-- Sledovaní (data uživatele – import je nikdy nemaže). typ: poslanec | klub,
-- id = id_poslanec nebo id_organ klubu, skupina = pojmenovaný seznam („Moji sledovaní“…).
CREATE TABLE IF NOT EXISTS sledovany (
    typ     TEXT NOT NULL CHECK (typ IN ('poslanec', 'klub')),
    id      INTEGER NOT NULL,
    skupina TEXT NOT NULL,
    pridano TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (typ, id, skupina)
);
