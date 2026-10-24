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
    zkratka   TEXT
);
CREATE INDEX IF NOT EXISTS ix_bod_schuze ON bod (id_schuze, cislo);

CREATE TABLE IF NOT EXISTS tisk (
    id_tisk     INTEGER PRIMARY KEY,
    ct          INTEGER,             -- číslo sněmovního tisku
    id_obdobi   INTEGER,
    nazev       TEXT,
    uplny_nazev TEXT,
    predlozeno  TEXT
);
CREATE INDEX IF NOT EXISTS ix_tisk_ct ON tisk (id_obdobi, ct);

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
