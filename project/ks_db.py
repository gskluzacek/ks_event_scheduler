from collections import defaultdict
from typing import AsyncIterator, cast, Any

import aiosqlite

from contextlib import asynccontextmanager

import read_env
from ks_db_errors import AcctCreateError, DupAcctAccountNameError, DupAcctDiscordIdError


@asynccontextmanager
async def _connection(db: aiosqlite.Connection | None) -> AsyncIterator[tuple[aiosqlite.Connection, bool]]:
    """
    Internal helper: if `db` was passed in (part of an outer transaction),
    reuse it and let the caller own commit/rollback/close. Otherwise open,
    use, and clean up a connection here.

    Yields (db, owns_conn).
    """
    config = read_env.load_config()
    if db is not None:
        yield db, False
        return

    conn = await aiosqlite.connect(config.DB_FILE)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn, True
    finally:
        await conn.close()


async def get_timezones(db: aiosqlite.Connection | None = None):
    async with _connection(db) as (conn, _owns_conn):
        async with conn.execute(
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


async def create_account(
    account_type: str,
    account_name: str,
    account_tz: str,
    discord_id: int | None,
    discord_name: str | None,
    discord_nick: str | None,
    create_account_id: int,
    update_account_id: int,
    db: aiosqlite.Connection | None = None,
) -> int | None:
    async with _connection(db) as (conn, owns_conn):
        try:
            cursor = await conn.execute(
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
            if owns_conn:
                await conn.commit()
            return row[0] if row else None

        except aiosqlite.IntegrityError as e:
            if owns_conn:
                await conn.rollback()
            # This catches UNIQUE(account_name) OR UNIQUE(discord_id)
            msg = str(e).lower()
            if "account_name" in msg:
                raise DupAcctAccountNameError("The account name already exists")
            if "discord_id" in msg:
                raise DupAcctDiscordIdError("The Discord ID already exists")
            raise AcctCreateError("Unexpected database integrity error during account creation") from e

async def get_accounts():
    async with _connection(db=None) as (conn, _owns_conn):
        async with conn.execute(
            """
            with player_counts as (
                select 
                    account_id, 
                    count(*) as player_count
                from players
                group by account_id
            )
            SELECT
                t1.account_id,
                t1.account_type,
                t1.account_name,
                t1.account_tz,
                t1.discord_id,
                t1.discord_name,
                t1.discord_nick,
                t1.create_account_id,
                coalesce(t2.account_name, t1.account_name) as create_account_name,
                t1.create_date_time,
                t1.update_account_id,
                t1.update_date_time,
                coalesce(t3.account_name, t1.account_name) as update_account_name,
                coalesce(t4.player_count, 0) as player_count
            FROM accounts t1
            left join accounts t2 on t1.create_account_id = t2.account_id
            left join accounts t3 on t1.update_account_id = t3.account_id
            left join player_counts as t4 on t1.account_id = t4.account_id
            """
        ) as cursor:
            rows = await cursor.fetchall()
    return [cast(dict[str, Any], dict(row)) for row in rows] if rows else []


async def get_accounts_ac(
        partial_account_name: str,
) -> list[tuple[str, int]]:
    async with _connection(db=None) as (conn, _owns_conn):
        async with conn.execute(
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


async def get_account_by_id(account_id: int) -> dict[str, Any] | None:
    async with _connection(db=None) as (conn, _owns_conn):
        async with conn.execute(
            """
            with player_counts as (
                select 
                    account_id, 
                    count(*) as player_count
                from players
                group by account_id
            )
            SELECT
                t1.account_id,
                t1.account_type,
                t1.account_name,
                t1.account_tz,
                t1.discord_id,
                t1.discord_name,
                t1.discord_nick,
                t1.create_account_id,
                coalesce(t2.account_name, t1.account_name) as create_account_name,
                t1.create_date_time,
                t1.update_account_id,
                t1.update_date_time,
                coalesce(t3.account_name, t1.account_name) as update_account_name,
                coalesce(t4.player_count, 0) as player_count
            FROM accounts t1
            left join accounts t2 on t1.create_account_id = t2.account_id
            left join accounts t3 on t1.update_account_id = t3.account_id
            left join player_counts as t4 on t1.account_id = t4.account_id
            where t1.account_id = ?
            """,
            (account_id,),
        ) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None