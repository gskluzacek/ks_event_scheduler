import logging

import discord
from discord.ext import commands
from discord import app_commands

import read_env
from ks_db import get_timezones


logger = logging.getLogger("ksbot.bot")


class KsEventSchedulerBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.config = read_env.get_config()

        self.tz_names: dict[str, list[str]] = {}
        self.tz_region_choices: list[app_commands.Choice[str]] = []

    async def setup_hook(self):
        # after bot.run() is executed, setup_hook() runs once before the bot connects fully
        self.tz_names = await get_timezones()
        logger.debug("tz_names: Loaded %s timezone regions", len(self.tz_names))
        for region, locations in self.tz_names.items():
            logger.debug("tz_names: For timezone region %s, Loaded %s timezone locations", region, len(locations))

        self.tz_region_choices = [
            app_commands.Choice[str](name=region, value=region)
            for region in sorted(self.tz_names)
        ]
        logger.debug("tz_region_choices: Loaded %s timezone regions", len(self.tz_region_choices))

        await self.sync_commands()
        logger.info("Bot fully initialized")

    async def sync_commands(self):
        try:
            # Sync logic (DEBUG vs PRODUCTION)
            logger.info("Top-level commands BEFORE sync:")
            for cmd in self.tree.get_commands():
                logger.info(" - %s (%s)", cmd.name, type(cmd).__name__)

            if self.config.BOT_MODE == "debug":
                if self.config.TEST_GUILD_ID is None:
                    logger.error("BOT_MODE set to DEBUG but TEST_GUILD_ID is not set")
                    raise ValueError("BOT_MODE set to DEBUG but TEST_GUILD_ID is not set")

                guild = discord.Object(id=self.config.TEST_GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info("BOT_MODE = debug: Synced %s commands to guild: %s", len(synced), self.config.TEST_GUILD_ID)
            else:
                synced = await self.tree.sync()
                logger.info("BOT_MODE = production: Synced %s global commands", len(synced))

        except Exception:
            logger.exception("Command sync failed")
            raise
