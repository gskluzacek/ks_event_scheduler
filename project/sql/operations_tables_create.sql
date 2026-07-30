-- PROMPT FOR ADDING INDEXES:
-- based on the queries in ks_db.py, what indexes would you suggest be added to the tables in operations_tables.sql?

CREATE TABLE IF NOT EXISTS accounts (
    account_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type      TEXT NOT NULL
         CHECK (account_type IN ('member', 'user', 'manual')),
    account_name      TEXT NOT NULL UNIQUE,
    account_tz        TEXT NOT NULL,
    -- account_cntry: think about acdding a country code?

    discord_id        INTEGER UNIQUE,
    discord_name      TEXT,
    discord_nick      TEXT,

    create_account_id INTEGER NOT NULL, -- set to 0 if user is adding themselves
    create_date_time  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- format YYYY-MM-DD HH:MM:SS
    update_account_id INTEGER NOT NULL, -- for insert, set to 0 if user is adding themselves
    update_date_time  TEXT NOT NULL -- use datetime('now') to populate
);

CREATE INDEX IF NOT EXISTS idx_accounts_lower_account_name
    ON accounts (lower(account_name));


CREATE TABLE IF NOT EXISTS players (
    player_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id        INTEGER,

    kingshot_id       INTEGER NOT NULL UNIQUE,
    kingshot_name     TEXT NOT NULL UNIQUE,

    power             REAL NOT NULL,
    town_center_level TEXT NOT NULL,
    kingdom           INTEGER NOT NULL,
    alliance          TEXT NOT NULL,

    create_account_id INTEGER NOT NULL,
    create_date_time  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- format YYYY-MM-DD HH:MM:SS
    update_account_id INTEGER NOT NULL,
    update_date_time  TEXT NOT NULL -- use datetime('now') to populate
);

CREATE INDEX IF NOT EXISTS idx_players_account_id
    ON players (account_id);

CREATE INDEX IF NOT EXISTS idx_players_lower_kingshot_name
    ON players (lower(kingshot_name));

CREATE INDEX IF NOT EXISTS idx_players_account_id_lower_kingshot_name
    ON players (account_id, lower(kingshot_name));


CREATE TABLE IF NOT EXISTS admins (
    admin_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id       INTEGER NOT NULL,
    admin_level      TEXT NOT NULL
        CHECK (admin_level IN ('super', 'regular')),
    create_account_id INTEGER NOT NULL,
    create_date_time  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- format YYYY-MM-DD HH:MM:SS

    UNIQUE (account_id, admin_level)
);


CREATE TABLE IF NOT EXISTS events
(
    event_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name        TEXT                           not null,
    event_desc        TEXT                           not null,
    qty_to_schedule   integer                        not null, -- how many events to schedule
    begin_date        TEXT                           not null, -- format YYYY-MM-DD (UTC)
    end_date          TEXT                           not null, -- format YYYY-MM-DD (UTC). use a value of for no end date: '9999-12-31'
    active_ind        INTEGER                        not null
        CHECK (active_ind IN (0, 1)),
    create_account_id INTEGER                        not null,
    create_date_time  TEXT not null default CURRENT_TIMESTAMP, -- format YYYY-MM-DD HH:MM:SS UTC
    update_account_id integer                        not null,
    update_date_time  TEXT                           not null,  -- UTC use datetime('now') to populate

    UNIQUE (event_name)
);


CREATE TABLE IF NOT EXISTS avails
(
    avail_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id          INTEGER                        not null,
    player_id         INTEGER                        not null,
    avail_type        TEXT                           not null
        CHECK (avail_type IN ('prefered', 'acceptable', 'avoid')),
    priority          INTEGER default 0              not null,
    start_time        TEXT                           not null, -- format HH:MM:SS
    end_time          TEXT                           not null, -- format HH:MM:SS
    validated_ind     INTEGER                        not null
        CHECK (validated_ind IN (0, 1)),
    create_account_id INTEGER                        not null,
    create_date_time  TEXT not null default CURRENT_TIMESTAMP, -- format YYYY-MM-DD HH:MM:SS UTC
    update_account_id integer                        not null,
    update_date_time  TEXT                           not null,  -- UTC use datetime('now') to populate

    UNIQUE (event_id, player_id, avail_type, start_time, end_time)
);
