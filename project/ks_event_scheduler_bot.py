import os
from typing import cast
import traceback
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands

from database import get_timezones

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
BOT_MODE = os.getenv("BOT_MODE", "debug")  # debug | production
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

if BOT_MODE == "debug" and not TEST_GUILD_ID:
    raise RuntimeError("Missing TEST_GUILD_ID for debug mode")

# --------------------------------------------------
# Autocomplete
# --------------------------------------------------

async def region_autocomplete(
    interaction: discord.Interaction,
    current: str,
):
    bot = cast(MyBot, interaction.client)

    return [
        choice
        for choice in bot.tz_region_choices
        if current.lower() in choice.name.lower()
    ][:25]

async def timezone_autocomplete(interaction: discord.Interaction, current: str):
    tz_region = getattr(interaction.namespace, "tz_region", None)
    if not tz_region:
        return []
    bot = cast(MyBot, interaction.client)

    locations = bot.tz_names.get(tz_region, [])
    return [
        app_commands.Choice(name=tz, value=tz)
        for tz in locations
        if current.lower() in tz.lower()
    ][:25]


# TODO: replace with logic that queries the accounts table for the given
#       discord_id and return the account_id. or retunrs None if the
#       discord_id doesn't exist on the accounts table.
def lookup_acct_id_from_discord_id(discord_id) -> int:
    # currently we are returning -1 to represent a dummy account is being returned
    return -1

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
    ):
        bot = cast(MyBot, interaction.client)

        # discord_user, discord_id, account_name are optional and MUTUALLY EXCLUSIVE
        set_count = sum(bool(value) for value in (discord_user, discord_id, account_name))
        if set_count > 1:
            return await interaction.response.send_message(
                "❌ You can only specify one of `discord_user`, `discord_id` or `account_name`.",
                ephemeral=True,
            )

        create_account_id = update_account_id = None
        if discord_user or discord_id or account_name:
            # User is registering another account (not themselves)
            create_account_id = lookup_acct_id_from_discord_id(interaction.user.id)
            update_account_id = create_account_id
            if not create_account_id:
                return await interaction.response.send_message(
                    "❌ You must have a registered account to register an account that is not your own.",
                    ephemeral=True,
                )

        if discord_user is not None:
            discord_id = discord_user.id
            discord_name = discord_user.name
            discord_nick = discord_user.display_name
            account_name = discord_name
            account_type = "member"

        elif discord_id is not None:
            try:
                discord_id = int(discord_id)
            except ValueError:
                return await interaction.response.send_message(
                    "❌ Invalid user_id. Must be a numeric Discord user ID.",
                    ephemeral=True,
                )
            try:
                discord_user = await bot.fetch_user(discord_id)
            except discord.NotFound:
                return await interaction.response.send_message(
                    "❌ User not found on Discord.",
                    ephemeral=True,
                )
            discord_name = discord_user.name
            discord_nick = None
            account_name = discord_name
            account_type = "user"

        elif account_name is not None:
            discord_id = None
            discord_name = None
            discord_nick = None
            account_type = "manual"

        else:
            discord_id = interaction.user.id
            discord_name = interaction.user.name
            discord_nick = interaction.user.display_name
            account_name = discord_name
            account_type = "member"
            create_account_id = 0  # user is adding themselves
            update_account_id = 0  # for insert set update to create account id

        locations = bot.tz_names.get(tz_region)
        if not locations:
            return await interaction.response.send_message(
                f"❌ Invalid timezone region: {tz_region}",
                ephemeral=True,
            )
        if tz_location not in locations:
            return await interaction.response.send_message(
                f"❌ Invalid timezone location: {tz_location}",
                ephemeral=True,
            )
        account_tz = f"{tz_region}/{tz_location}"

        await interaction.response.send_message(
            (
                f"✅ created account with:\n"
                f"\taccount type: {account_type}\n\taccount name: {account_name}\n\taccount_tz: {account_tz}\n"
                f"\tdiscord_id: {discord_id}\n\tdiscord_name: {discord_name}\n\tdiscord_nick: {discord_nick}\n"
                f"\tcreate_account_id: {create_account_id}\n\tupdate_account_id: {update_account_id}"
            ),
            ephemeral=True,
        )


# --------------------------------------------------
# Bot setup
# --------------------------------------------------

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.tz_names: dict[str, list[str]] = {}
        self.tz_region_choices: list[app_commands.Choice[str]] = []

    async def setup_hook(self):
        # after bot.run() is executed, setup_hook() runs once before the bot connects fully
        self.tz_names = await get_timezones()
        print(f"Loaded {len(self.tz_names)} timezone regions")

        self.tz_region_choices = [
            app_commands.Choice[str](name=region, value=region)
            for region in sorted(self.tz_names)
        ]
        await self.sync_commands()
        print("Bot fully initialized")

    async def sync_commands(self):
        try:
            # Sync logic (DEBUG vs PRODUCTION)
            if BOT_MODE == "debug":
                guild = discord.Object(id=int(TEST_GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"[DEBUG] Synced {len(synced)} commands to guild {TEST_GUILD_ID}")
            else:
                synced = await self.tree.sync()
                print(f"[PRODUCTION] Synced {len(synced)} global commands")
        except Exception as e:
            print("Command sync failed")
            traceback.print_exc()


# --------------------------------------------------
# Register commands and run
# --------------------------------------------------

# created account with:
#       account type: member
#       account name: gskluzacek
#       account_tz: America/Chicago
#       discord_id: 835177531904098380
#       discord_name: gskluzacek
#       discord_nick: Cornelius
#       create_account_id: 0
#       update_account_id: 0


bot = MyBot()
bot.tree.add_command(Account())
bot.run(TOKEN)
