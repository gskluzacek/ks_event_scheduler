import os
from dotenv import load_dotenv

import discord
import asyncio

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.application import get_app

from database import create_account, create_admin, get_timezones, get_database_tables, create_db_tables
from redis_session import SessionManager, AppStateManager


load_dotenv()


if not (temp_token := os.getenv("DISCORD_TOKEN")):
    raise RuntimeError("Missing DISCORD_TOKEN")
TOKEN = temp_token

if not (temp_test_guild_id := os.getenv("TEST_GUILD_ID")):
    raise RuntimeError("Missing TEST_GUILD_ID for debug mode")
try:
    TEST_GUILD_ID = int(temp_test_guild_id)
except ValueError as e:
    raise RuntimeError("TEST_GUILD_ID is not set or invalid for debug mode") from e

if not (temp_admin_zero_id := os.getenv("ADMIN_ZERO_ID")):
    raise RuntimeError("Missing ADMIN_ZERO_ID for server initialization ")
try:
    ADMIN_ZERO_ID = int(temp_admin_zero_id)
except ValueError as e:
    raise RuntimeError("ADMIN_ZERO_ID is not set or is not a valid Discord User ID") from e

if not (temp_default_kingdom := os.getenv("DEFAULT_KINGDOM")):
    raise RuntimeError("Missing DEFAULT_KINGDOM")
try:
    DEFAULT_KINGDOM = int(temp_default_kingdom)
except ValueError as e:
    raise RuntimeError("DEFAULT_KINGDOM is not set or not a valid integer") from e

if not (temp_default_alliance := os.getenv("DEFAULT_ALLIANCE")):
    raise RuntimeError("Missing DEFAULT_ALLIANCE")
DEFAULT_ALLIANCE = temp_default_alliance

# Sentinel meaning "the Discord user created their own account."
SELF_REGISTERED_ACCOUNT_ID: int = 0


def show_completions():
    get_app().current_buffer.start_completion()


async def main():
    print("\n\nStarting Discord Utilities...\n")

    session = SessionManager()
    app_state = AppStateManager(redis_client=session._redis)  # reuse one connection

    app_state_exists = False
    if app_state.exists():
        app_state_exists = True
        bot_mode = app_state.get("bot_mode")
        print(f"Redis session already exists.\nBot Mode: {bot_mode}\n")

    admin_zero_exists = False
    super_admin_exists = False
    if (session_keys := session.all_session_keys()):
        print("Found session keys for the following users:")
        for session_key in session_keys:
            discord_user_id = session_key.split(":")[1]
            account_id = session.get(discord_user_id, "account_id")
            account_name = session.get(discord_user_id, "account_name")
            roles = session.get(discord_user_id, "roles", [])
            if "super" in roles:
                super_admin_exists = True
                admin_role = "super"
            elif "regular" in roles:
                admin_role = "regular"
            else:
                admin_role = "none"
            if discord_user_id == str(ADMIN_ZERO_ID):
                admin_zero_exists = True
                leader = "  ==>>  "
            elif admin_role == "super":
                leader = "  --->  "
            else:
                leader = "        "
            print(f"{leader}User ID: {discord_user_id}, Account ID: {account_id}, Account Name: {account_name}, Admin Role: {admin_role}")
        if admin_zero_exists or super_admin_exists:
            print("Admin zero/super admin exists.")

    if app_state_exists or session_keys:
        print("\nCannot continue with bot initialization as existing application data may be lost and/or corrupted.")
        print("    found application state and/or Admin Zero or super admin or other users found.")
        print("    Please contact the admin to resolve above issues to continue.\n\n")
        return

    print("")
    print("-" * 100)
    print("")

    client = discord.Client(intents=discord.Intents.none())
    await client.login(TOKEN)

    try:
        user = await client.fetch_user(ADMIN_ZERO_ID)
        print(f"Found Discord ID: {ADMIN_ZERO_ID:25} - for Discord User name: '{user.name}'")
    except discord.NotFound:
        print(f"Admin Zero User not found for Discord ID {ADMIN_ZERO_ID}")
        await client.close()
        return

    try:
        guild = await client.fetch_guild(TEST_GUILD_ID)
        print(f"Found Guild ID:   {TEST_GUILD_ID:25} - for Guild name: '{guild.name}'")
    except discord.NotFound:
        print(f"Guild not found for Guild ID {TEST_GUILD_ID}")
        await client.close()
        return

    try:
        member = await guild.fetch_member(ADMIN_ZERO_ID)
        print(f"Found Discord ID: {ADMIN_ZERO_ID:25} - for Guild Member: '{member.display_name}'")
    except discord.NotFound:
        print("Admin Zero User: Member not found in the guild.")
        await client.close()
        return

    await client.close()

    print("")
    print("-" * 100)
    print("")

    # check for database tables - if any database tables exist exit
    database_tables = await get_database_tables()
    if database_tables:
        print("Found database tables:")
        for database_table in database_tables:
            print(f"    {database_table}")
        print("\nCannot continue with bot initialization as existing database tables may be lost and/or corrupted.")
        print("    Please contact the admin to resolve above issues to continue.\n\n")
        return
    else:
        print(f"No database tables found - running script to create tables")
        await create_db_tables()

    print("\nintializing application state - bot mode: down\n\n")
    app_state.set("bot_mode", "down")
    app_state.set("initialization", "in_progress")

    tz_names = await get_timezones()

    tz_regions = list(tz_names.keys())
    tz_regions_lkp = {c.lower(): c for c in tz_regions}
    completer = WordCompleter(tz_regions, ignore_case=True)
    p_session = PromptSession(completer=completer)

    while True:
        cmd_raw = await p_session.prompt_async("Enter/select a timezone region: ", pre_run=show_completions)
        cmd = tz_regions_lkp.get(cmd_raw.lower())
        if cmd is not None:
            break
        print(f"Invalid region: `{cmd_raw}`. please begin typing then enter/select a valid region from the drop down.")
        print(f"{', '.join(tz_regions)}")
    tz_region = cmd
    print("You have selected a time zone region of:", tz_region)

    tz_locations = tz_names[cmd]
    tz_locations_lkp = {c.lower(): c for c in tz_locations}
    completer = WordCompleter(tz_locations, ignore_case=True)
    p_session = PromptSession(completer=completer)

    while True:
        cmd_raw = await p_session.prompt_async("Enter/select a timezone location: ", pre_run=show_completions)
        cmd = tz_locations_lkp.get(cmd_raw.lower())
        if cmd is not None:
            break
        print(f"Invalid location: `{cmd_raw}`. please begin typing then enter/select a valid location from the drop down.")
        print(f"{', '.join(tz_locations)}")
    tz_location = cmd
    print("You have selected a time zone location of:", tz_location)

    account_tz = f"{tz_region}/{tz_location}"
    print("Setting your timezone to: ")

    # TODO: either delete the user from the table or truncate the table

    account_id = await create_account(
        account_type="member",
        account_name=member.name,
        account_tz=account_tz,
        discord_id=member.id,
        discord_name=member.name,
        discord_nick=member.display_name,
        create_account_id=SELF_REGISTERED_ACCOUNT_ID,
        update_account_id=SELF_REGISTERED_ACCOUNT_ID,
    )

    if account_id is None:
        raise ValueError(
            f"Could not create account - returned account_id is None. Discord ID: {member.id}, "
            f"Account Name: {member.name}"
        )

    # TODO: either delete the user from the table or truncate the table

    admin_id = await create_admin(
        account_id=account_id,
        admin_level="super",
        create_account_id=SELF_REGISTERED_ACCOUNT_ID,
    )

    if admin_id is None:
        raise ValueError(
            f"Count not create admin - returned admin_id is None. Discord ID: {member.id}, "
        )

    session.set(member.id, "account_id", account_id)
    session.set(member.id, "account_name", member.name)
    session.set(member.id, "roles", ["super"])

    app_state.set("bot_mode", "maintenance")
    # TODO: remind user that the admin can use /admin botmod <mode> to bring the bot up



if __name__ == "__main__":
    asyncio.run(main())
