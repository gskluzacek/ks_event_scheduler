CREATE TABLE IF NOT EXISTS accounts (
    account_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type      TEXT NOT NULL CHECK (account_type IN ('member', 'user', 'manual')),
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

CREATE TABLE IF NOT EXISTS players (
    player_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id        INTEGER,

    kingshot_id       INTEGER NOT NULL UNIQUE,
    kingshot_name     TEXT NOT NULL UNIQUE,

    power             REAL NOT NULL,
    town_center_level TEXT NOT NULL,
    kingdom           INTEGER NOT NULL,
    alliance TEXT     NOT NULL,

    create_account_id INTEGER NOT NULL,
    create_date_time  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- format YYYY-MM-DD HH:MM:SS
    update_account_id INTEGER NOT NULL,
    update_date_time  TEXT NOT NULL -- use datetime('now') to populate
);
