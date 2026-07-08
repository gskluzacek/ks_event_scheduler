from collections import defaultdict
from pathlib import Path
from typing import Any

import aiosqlite


class AcctCreateError(Exception):
    pass

class DupAcctAccountNameError(AcctCreateError):
    pass


class DupAcctDiscordIdError(AcctCreateError):
    pass


class PlayerCreateError(Exception):
    pass


class DupPlayerKingshotIdError(PlayerCreateError):
    pass


class DupPlayerKingshotNameError(PlayerCreateError):
    pass


class AdminCreateError(Exception):
    pass


class DupAdminAccountIdAdminLevelError(AdminCreateError):
    pass


DB_FILE = "ks_bot.db"


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


# async def get_acct_id_old(discord_id: int) -> int | None:
#     async with aiosqlite.connect(DB_FILE) as db:
#         db.row_factory = aiosqlite.Row
#         async with db.execute(
#             """
#             SELECT account_id
#             FROM accounts
#             WHERE discord_id = ?
#             """,
#             (discord_id,),
#         ) as cursor:
#             row = await cursor.fetchone()
#     return row["account_id"] if row else None


async def get_acct_id(
        *, discord_id: int | None = None, account_name: str | None = None
) -> int | None:
    account_name = account_name.strip() if account_name else ""

    if discord_id is None and not account_name:
        return None
        # raise ValueError("Pass either valid discord_id or non-blank account_name")

    if discord_id is not None and account_name:
        return None
        # raise ValueError("Pass only one of discord_id or account_name")

    column_name = "discord_id" if discord_id is not None else "account_name"
    column_value = discord_id if discord_id is not None else account_name

    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""
            SELECT account_id
            FROM accounts
            WHERE {column_name} = ?
            """,
            (column_value,),
        ) as cursor:
            row = await cursor.fetchone()
    return row["account_id"] if row else None


async def get_accounts(partial_account_name: str) -> list[tuple[str, int]]:
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT account_name, account_id
            FROM accounts
            WHERE account_name LIKE ?
            ORDER BY account_name
            LIMIT 25
            """,
            (f"{partial_account_name.strip()}%", ),
        ) as cursor:
            rows = await cursor.fetchall()
        accounts = [(row["account_name"], row["account_id"]) for row in rows]
        return accounts


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


async def is_initialized() -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            """
            SELECT 1
            FROM admins
            WHERE admin_level = 'super'
            LIMIT 1
            """
        ) as cursor:
            return await cursor.fetchone() is not None


async def create_admin(
        account_id: int,
        admin_level: str,
        create_account_id: int,
) -> int | None:
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute(
                """
                INSERT INTO admins (
                    account_id,
                    admin_level,
                    create_account_id
                )
                VALUES (?, ?, ?)
                RETURNING admin_id
                """,
                (
                    account_id,
                    admin_level,
                    create_account_id,
                ),
            )
            row = await cursor.fetchone()
            await db.commit()
            return row[0] if row else None

    except aiosqlite.IntegrityError as e:
        msg = str(e).lower()
        if "account_id" in msg and "admin_level" in msg:
            raise DupAdminAccountIdAdminLevelError("The account already has that admin level")
        raise AdminCreateError("Unexpected database integrity error during admin creation") from e


async def get_player(player_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT
                player_id,
                account_id,
                kingshot_id,
                kingshot_name,
                power,
                town_center_level,
                kingdom,
                alliance,
                create_account_id,
                create_date_time,
                update_account_id,
                update_date_time
            FROM players
            WHERE player_id = ?
            """,
            (player_id,),
        ) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def get_players(player_ids: list[int]) -> list[tuple[str, int]]:
    if not player_ids:
        return []

    placeholders = ", ".join("?" for _ in player_ids)

    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""
            SELECT
                kingshot_name,
                player_id
            FROM players
            WHERE player_id IN ({placeholders})
            """,
            player_ids,
        ) as cursor:
            rows = await cursor.fetchall()
    player_order = {player_id: index for index, player_id in enumerate(player_ids)}
    players = sorted(
        ((row["kingshot_name"], row["player_id"]) for row in rows),
        key=lambda player: player_order[player[1]],
    )
    return players


async def create_player(
        account_id: int,
        kingshot_id: int,
        kingshot_name: str,
        power: float,
        town_center_level: str,
        kingdom: int,
        alliance: str,
        create_account_id: int,
        update_account_id: int,
) -> int | None:
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute(
                """
                INSERT INTO players ( 
                    account_id,
                    kingshot_id,
                    kingshot_name,
                    power,
                    town_center_level,
                    kingdom,
                    alliance,
                    create_account_id,
                    update_account_id,
                    update_date_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                RETURNING player_id
                """,
                (
                    account_id,
                    kingshot_id,
                    kingshot_name,
                    power,
                    town_center_level,
                    kingdom,
                    alliance,
                    create_account_id,
                    update_account_id
                ),
            )
            row = await cursor.fetchone()
            await db.commit()
            return row[0] if row else None

    except aiosqlite.IntegrityError as e:
        # This catches UNIQUE(kingshot_id) OR UNIQUE(kingshot_name)
        msg = str(e).lower()
        if "kingshot_id" in msg:
            raise DupPlayerKingshotIdError("The kingshot_id already exists")
        if "kingshot_name" in msg:
            raise DupPlayerKingshotNameError("The kingshot_name already exists")
        raise PlayerCreateError("Unexpected database integrity error during player creation") from e




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


async def get_database_tables():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ) as cursor:
            rows = await cursor.fetchall()
    return [row[0] for row in rows]

async def create_db_tables() -> None:
    sql_files = ["operations_tables_create.sql", "timezones_inserts.sql"]
    async with aiosqlite.connect(DB_FILE) as db:
        for sql_file in sql_files:
            print(f"executing file: {sql_file}")
            sql = (Path("sql") / Path(sql_file)).read_text(encoding="utf-8")
            await db.executescript(sql)
        await db.commit()

