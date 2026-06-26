import os
import logging
from typing import cast
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands

from database import get_timezones

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ks-evnt-sch-bot")

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
BOT_MODE = os.getenv("BOT_MODE", "debug").strip().lower()  # debug | production
TEST_GUILD_ID: int | None = None

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

if BOT_MODE not in {"debug", "production"}:
    raise RuntimeError("BOT_MODE must be either 'debug' or 'production'")

if BOT_MODE == "debug":
    if not (temp_test_guild_id := os.getenv("TEST_GUILD_ID")):
        raise RuntimeError("Missing TEST_GUILD_ID for debug mode")
    try:
        TEST_GUILD_ID = int(temp_test_guild_id)
    except ValueError as e:
        raise RuntimeError("TEST_GUILD_ID is not set or invalid for debug mode") from e

SELF_REGISTERED_ACCOUNT_ID: int = 0
DUMMY_ACCOUNT_ID: int = -1


# --------------------------------------------------
# Autocomplete
# --------------------------------------------------

async def region_autocomplete(
        interaction: discord.Interaction,
        current: str,
) -> list[app_commands.Choice[str]]:
    bot = cast(KsEventSchedulerBot, interaction.client)

    return [
        choice
        for choice in bot.tz_region_choices
        if current.lower() in choice.name.lower()
    ][:25]


async def timezone_autocomplete(
        interaction: discord.Interaction,
        current: str,
) -> list[app_commands.Choice[str]]:
    tz_region = getattr(interaction.namespace, "tz_region", None)
    if not isinstance(tz_region, str) or not tz_region:
        return []
    bot = cast(KsEventSchedulerBot, interaction.client)

    locations = bot.tz_names.get(tz_region, [])
    return [
        app_commands.Choice[str](name=tz, value=tz)
        for tz in locations
        if current.lower() in tz.lower()
    ][:25]


# TODO: replace with logic that queries the accounts table for the given
#       discord_id and returns the account_id, or returns None if the
#       discord_id doesn't exist on the accounts table.
def lookup_acct_id_from_discord_id(_discord_id: int) -> int | None:
    # the real function will return a value of None if the discord_id is not found in the accounts table, or the account_id if it is found
    # as this is just a stub function, we are currently returning -1 to represent a dummy account_id.
    return DUMMY_ACCOUNT_ID


# --------------------------------------------------
# Command Group
# --------------------------------------------------

class Account(app_commands.Group):
    def __init__(self):
        super().__init__(name="account", description="User Account Tools")

    # /account register
    @app_commands.command(name="register", description="Register an Account")
    @app_commands.autocomplete(tz_region=region_autocomplete)
    @app_commands.autocomplete(tz_location=timezone_autocomplete)
    async def register(
            self,
            interaction: discord.Interaction,
            tz_region: str,
            tz_location: str,
            discord_user: discord.User | None = None,
            discord_id: str | None = None,
            account_name: str | None = None,
    ) -> None:
        bot = cast(KsEventSchedulerBot, interaction.client)

        # discord_user, discord_id, account_name are optional and MUTUALLY EXCLUSIVE
        discord_id = discord_id.strip() if discord_id else ""
        account_name = account_name.strip() if account_name else ""
        set_count = sum(bool(value) for value in (discord_user, discord_id, account_name))
        if set_count > 1:
            await interaction.response.send_message(
                "❌ You can only specify one of `discord_user`, `discord_id` or `account_name`.", ephemeral=True
            )
            return

        # if the user is registering another account (and not themselves) get the user's account id
        create_account_id = update_account_id = None
        if discord_user or discord_id or account_name:
            create_account_id = lookup_acct_id_from_discord_id(_discord_id=interaction.user.id)
            update_account_id = create_account_id
            if create_account_id is None:
                await interaction.response.send_message(
                    "❌ You must have a registered account to register an account that is not your own.", ephemeral=True
                )
                return

        # convert discord_id (a stringb) into target_discord_id (an int) if it is not the empty string
        target_discord_id: int | None = None
        if discord_id:
            try:
                target_discord_id = int(discord_id)
            except ValueError:
                await interaction.response.send_message("❌ Invalid user_id. Must be a numeric Discord user ID.",
                                                        ephemeral=True)
                return

        # --------------------------------------------------
        # handle our 4 use cases
        # --------------------------------------------------

        # 1. if discord_user is provided, then someone other than the provided discord_user is
        #    regeistering an account for the specified discord_user.
        if discord_user is not None:
            target_discord_id = discord_user.id
            discord_name = discord_user.name
            discord_nick = discord_user.display_name
            account_name = discord_name
            account_type = "member"

        # 2. if (target) discord_id is provided, then someone other than the discord user
        #    corresponding to the provided discord_id is registering an account for the discord
        #    user that corresponds to the specified discord_id.
        elif target_discord_id is not None:
            try:
                # lookup the corresponding discord_user for the specificed discord_id
                discord_user = await bot.fetch_user(target_discord_id)
            except discord.NotFound:
                await interaction.response.send_message("❌ User not found on Discord.", ephemeral=True)
                return
            except discord.HTTPException:
                await interaction.response.send_message(
                    "❌ Could not fetch user from Discord. Please try again later.", ephemeral=True
                )
                return
            discord_name = discord_user.name
            discord_nick = None
            account_name = discord_name
            account_type = "user"

        # 3. if account_name is provided, then someone is registering an account for a
        #    user that is NOT a discord user.
        elif account_name:
            target_discord_id = None
            discord_name = None
            discord_nick = None
            account_type = "manual"

        # 4. the user is self-registering an account for themselves.
        else:
            target_discord_id = interaction.user.id
            discord_name = interaction.user.name
            discord_nick = interaction.user.display_name
            account_name = discord_name
            account_type = "member"
            create_account_id = SELF_REGISTERED_ACCOUNT_ID  # user is adding themselves
            update_account_id = SELF_REGISTERED_ACCOUNT_ID  # for insert set update to create account id

        # make sure the timezone region is valid, by getting the list of timezone locations for the specified region
        locations = bot.tz_names.get(tz_region)
        if not locations:
            await interaction.response.send_message(f"❌ Invalid timezone region: {tz_region}", ephemeral=True)
            return
        # validate that the specified timezone location exists fcr the region
        if tz_location not in locations:
            await interaction.response.send_message(f"❌ Invalid timezone location: {tz_location}", ephemeral=True)
            return
        account_tz = f"{tz_region}/{tz_location}"

        await interaction.response.send_message(
            (
                f"✅ created account with:\n"
                f"\taccount type: {account_type}\n\taccount name: {account_name}\n\taccount_tz: {account_tz}\n"
                f"\tdiscord_id: {target_discord_id}\n\tdiscord_name: {discord_name}\n\tdiscord_nick: {discord_nick}\n"
                f"\tcreate_account_id: {create_account_id}\n\tupdate_account_id: {update_account_id}"
            ),
            ephemeral=True,
        )


# --------------------------------------------------
# Bot setup
# --------------------------------------------------

class KsEventSchedulerBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.tz_names: dict[str, list[str]] = {}
        self.tz_region_choices: list[app_commands.Choice[str]] = []

    async def setup_hook(self):
        # after bot.run() is executed, setup_hook() runs once before the bot connects fully
        self.tz_names = await get_timezones()
        logger.debug("Loaded %s timezone regions", len(self.tz_names))

        self.tz_region_choices = [
            app_commands.Choice[str](name=region, value=region)
            for region in sorted(self.tz_names)
        ]
        await self.sync_commands()
        logger.info("Bot fully initialized")

    async def sync_commands(self):
        try:
            # Sync logic (DEBUG vs PRODUCTION)
            if BOT_MODE == "debug":
                if TEST_GUILD_ID is None:
                    logger.error("BOT_MODE set to DEBUG but TEST_GUILD_ID is not set")
                    raise ValueError("BOT_MODE set to DEBUG but TEST_GUILD_ID is not set")

                guild = discord.Object(id=TEST_GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info("BOT_MODE = debug: Synced %s commands to guild: %s", len(synced), TEST_GUILD_ID)
            else:
                synced = await self.tree.sync()
                logger.info("BOT_MODE = production: Synced %s global commands", len(synced))

        except Exception:
            logger.exception("Command sync failed")
            raise


# --------------------------------------------------
# Register commands and run
# --------------------------------------------------

ks_event_scheduler_bot = KsEventSchedulerBot()
ks_event_scheduler_bot.tree.add_command(Account())
ks_event_scheduler_bot.run(TOKEN)
