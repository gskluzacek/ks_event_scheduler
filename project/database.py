from collections import defaultdict
import aiosqlite


class AcctCreateError(Exception):
    pass

class DupAcctAccountNameError(AcctCreateError):
    pass


class DupAcctDiscordIdError(AcctCreateError):
    pass


DB_FILE = "ks_bot.db"


# date time-stamps will be stored in UTC on the database
# to convert them to user's local time zone (if set...)
#
# from datetime import datetime, UTC
# from zoneinfo import ZoneInfo
#
# dt = datetime.fromisoformat(db_timestamp.replace(" ", "T"))
# dt = dt.replace(tzinfo=UTC)
#
# local_dt = dt.astimezone(ZoneInfo("America/Chicago"))

# async def initialize_database():
#     async with aiosqlite.connect(DB_FILE) as db:
#         await db.execute(
#             """
#             CREATE TABLE IF NOT EXISTS players (
#                 player_id         INTEGER PRIMARY KEY AUTOINCREMENT,
#
#                 kingshot_id       INTEGER NOT NULL UNIQUE,
#                 kingshot_name     TEXT NOT NULL UNIQUE,
#
#                 power             REAL NOT NULL,
#                 town_center_level TEXT NOT NULL,
#                 kingdom           INTEGER NOT NULL,
#                 alliance TEXT     NOT NULL,
#
#                 -- discord_id        INTEGER,
#                 -- discord_name      TEXT,
#                 -- discord_nick      TEXT,
#                 account_id        INTEGER,
#
#                 create_account_id INTEGER NOT NULL,
#                 create_date_time  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- format YYYY-MM-DD HH:MM:SS
#                 update_account_id INTEGER NOT NULL,
#                 update_date_time  TEXT NOT NULL -- use datetime('now') to populate
#             );
#
#             CREATE TABLE IF NOT EXISTS accounts (
#                 account_id        INTEGER PRIMARY KEY AUTOINCREMENT,
#                 account_type      TEXT NOT NULL CHECK (account_type IN ('member', 'user', 'manual')),
#                 account_name      TEXT NOT NULL UNIQUE,
#                 account_tz        INTEGER NOT NULL,
#
#                 discord_id        INTEGER UNIQUE,
#                 discord_name      TEXT,
#                 discord_nick      TEXT,
#
#                 create_account_id INTEGER NOT NULL, -- set to 0 if user is adding themselves
#                 create_date_time  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- format YYYY-MM-DD HH:MM:SS
#                 update_account_id INTEGER NOT NULL, -- for insert, set to 0 if user is adding themselves
#                 update_date_time  TEXT NOT NULL -- use datetime('now') to populate
#             );
#             """
#         )
#         await db.commit()

async def get_timezones():
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT region, location
            FROM timezone
            ORDER BY region, location
            """
        ) as cursor:
            rows = await cursor.fetchall()
    tz_by_region = defaultdict(list)
    for row in rows:
        tz_by_region[row["region"]].append(row["location"])
    return dict(tz_by_region)


async def get_acct_id(discord_id: int) -> int | None:
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT account_id
            FROM accounts
            WHERE discord_id = ?
            """,
            (discord_id,),
        ) as cursor:
            row = await cursor.fetchone()
    return row["account_id"] if row else None


async def create_account(
    account_type: str,
    account_name: str,
    account_tz: str,
    discord_id: int | None,
    discord_name: str | None,
    discord_nick: str | None,
    create_account_id: int,
    update_account_id: int,
) -> int | None:
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute(
                """
                INSERT INTO accounts (
                    account_type,
                    account_name,
                    account_tz,
                    discord_id,
                    discord_name,
                    discord_nick,
                    create_account_id,
                    update_account_id,
                    update_date_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                RETURNING account_id
                """,
                (
                    account_type,
                    account_name,
                    account_tz,
                    discord_id,
                    discord_name,
                    discord_nick,
                    create_account_id,
                    update_account_id,
                ),
            )

            row = await cursor.fetchone()
            await db.commit()

            return row[0] if row else None

    except aiosqlite.IntegrityError as e:
        # This catches UNIQUE(account_name) OR UNIQUE(discord_id)
        msg = str(e).lower()
        if "account_name" in msg:
            raise DupAcctAccountNameError("The account name already exists")
        if "discord_id" in msg:
            raise DupAcctDiscordIdError("The Discord ID already exists")
        raise AcctCreateError("Unexpected database integrity error during account creation") from e


# async def save_player(player: dict):
#     #
#     # we may wnat to remove columns that are null from the player dict
#     # def build_patch(player: dict):
#     #     return {k: v for k, v in player.items() if v is not None}
#     #
#     async with aiosqlite.connect(DB_FILE) as db:
#         await db.execute(
#             """
#             INSERT INTO players (
#                 kingshot_id,
#                 kingshot_name,
#                 power,
#                 town_center_level,
#                 kingdom,
#                 alliance,
#                 discord_id,
#                 discord_name,
#                 discord_nick,
#                 create_user_id,
#                 update_user_id,
#                 update_date_time
#             )
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
#             ON CONFLICT(kingshot_id)
#             DO UPDATE SET
#                 kingshot_name=excluded.kingshot_name,
#                 power=excluded.power,
#                 -- depending how discord sends us values we may have to do something like
#                 --     COALESCE(excluded.town_center_level, town_center_level)
#                 town_center_level=excluded.town_center_level,
#                 kingdom=excluded.kingdom,
#                 alliance=excluded.alliance,
#                 discord_name=excluded.discord_name,
#                 discord_nick=excluded.discord_nick,
#                 update_user_id=excluded.update_user_id,
#                 update_date_time=datetime('now')
#             """, (
#                 # change over to player.git("field") if we are not getting all columns from discord
#                 player["kingshot_id"],
#                 player["kingshot_name"],
#                 player["power"],
#                 player["town_center_level"],
#                 player["kingdom"],
#                 player["alliance"],
#                 player["discord_id"],
#                 player["discord_name"],
#                 player["discord_nick"],
#                 player["create_user_id"],
#                 player["update_user_id"],
#             )
#         )
#         await db.commit()
#
#
# async def get_player(player_id: int):
#     async with aiosqlite.connect(DB_FILE) as db:
#         db.row_factory = aiosqlite.Row
#         async with db.execute(
#             """
#             SELECT *
#             FROM players
#             WHERE player_id = ?
#             """, (player_id, )
#         ) as cursor:
#             row = await cursor.fetchone()
#         return dict(row) if row else None
#
#
# async def delete_player(player_id: int):
#     async with aiosqlite.connect(DB_FILE) as db:
#         await db.execute(
#             """
#             DELETE FROM players
#             WHERE player_id = ?
#             """, (player_id, )
#         )
#         await db.commit()
#
#
# async def get_all_players():
#     async with aiosqlite.connect(DB_FILE) as db:
#         db.row_factory = aiosqlite.Row
#         async with db.execute(
#             """
#             SELECT *
#             FROM players
#             ORDER BY kingshot_name
#             """
#         ) as cursor:
#             rows = await cursor.fetchall()
#         return [dict(r) for r in rows]
