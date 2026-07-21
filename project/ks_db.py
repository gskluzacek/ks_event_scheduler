from collections import defaultdict
from typing import AsyncIterator

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
