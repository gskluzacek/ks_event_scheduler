import os
import logging
from typing import cast
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands

from redis_session import SessionManager, AppStateManager
from database import (
    get_timezones,
    create_account,
    DupAcctAccountNameError,
    DupAcctDiscordIdError,
    AcctCreateError,
    get_accounts,
    create_player,
    DupPlayerKingshotIdError,
    DupPlayerKingshotNameError,
    PlayerCreateError,
    get_player,
    get_players,
    create_admin,
    is_initialized,
)

# 🔥REMOVING the existing handlers completely
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s | %(name)s | [%(filename)s:%(lineno)d]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 🔥silence discord duplication
for name in [
    "discord",
    "discord.client",
    "discord.gateway",
    "discord.http",
    "discord.ext.commands",
    "discord.ext.commands.bot",
]:
    lg = logging.getLogger(name)
    lg.handlers.clear()
    lg.propagate = False

logger = logging.getLogger("ks_evnt_sch")
logger.setLevel(logging.DEBUG)


load_dotenv()

session = SessionManager()

TOKEN = os.getenv("DISCORD_TOKEN")
BOT_MODE = os.getenv("BOT_MODE", "debug").strip().lower()  # debug | production
TEST_GUILD_ID: int | None = None
ADMIN_ZERO_ID: int | None = None

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


async def account_id_autocomplete(
        _interaction: discord.Interaction,
        current: str,
) -> list[app_commands.Choice[int]]:
    accounts = await get_accounts(current)
    return [
        app_commands.Choice[int](
            name=account_name,
            value=account_id,
        )
        for account_name, account_id in accounts
    ]


async def player_id_with_recent_autocomplete(
        interaction: discord.Interaction,
        current: str,
) -> list[app_commands.Choice[int]]:
    recent_player_ids = session.get(interaction.user.id, "recent_players")
    recent_players = await get_players(recent_player_ids)
    print(">>>" + str(recent_players))
    return [
        app_commands.Choice[int](
            name=f"🕑 {kingshot_name} [{player_id:04}]",
            value=player_id
        )
        for kingshot_name, player_id in recent_players
    ]


# --------------------------------------------------
# Command Groups
# --------------------------------------------------

class Player(app_commands.Group):
    def __init__(self):
        super().__init__(name="player", description="Kingshot Player Tools")

    # /player add
    @app_commands.command(name="show", description="Display the details for Kingshot Player")
    @app_commands.autocomplete(player_id=player_id_with_recent_autocomplete)
    async def show(
            self,
            interaction: discord.Interaction,
            player_id: int
    ):
        player = await get_player(player_id)
        if player is None:
            await interaction.response.send_message(
                f"❌ Player not found, player_id: {player_id}", ephemeral=True
            )
            return

        update_recent_players(interaction.user.id, player_id)  # ⭐️🕑

        await interaction.response.send_message(
                f"""✅ Requested Player Details:
```text
        player_id: {player["player_id"]}
       account_id: {player["account_id"]}
      kingshot_id: {player["kingshot_id"]}
    kingshot_name: {player["kingshot_name"]}
            power: {player["power"]}
town_center_level: {player["town_center_level"]}
          kingdom: {player["kingdom"]}
         alliance: {player["alliance"]}
create_account_id: {player["create_account_id"]}
update_account_id: {player["update_account_id"]}
```""",
                ephemeral=True,
            )

    # /player add
    @app_commands.command(name="add", description="Add a Kingshot Player to an account")
    @app_commands.autocomplete(account_id=account_id_autocomplete)
    async def add(
            self,
            interaction: discord.Interaction,
            kingshot_id: int,
            kingshot_name: str,
            power: float,
            town_center_level: str,
            kingdom: int = DEFAULT_KINGDOM,
            alliance: str = DEFAULT_ALLIANCE,
            account_id: int | None = None,
    ):
        # interaction_account_id = await get_acct_id(discord_id=interaction.user.id)

        # get the discored user's account_id from the session. The user's session.account_id is
        # automatically created whenever a non-manual account is registered. If session.account_id
        # does not exits, then it means the user has not had an account registered. manual accounts
        # do not have an associated discord user (becuase they have not signed up for a Discord account)
        # and hence it is not posible for them to interact with a bot.
        interaction_account_id = session.get(interaction.user.id, "account_id")
        if interaction_account_id is None:
            await interaction.response.send_message(
                "❌ You must register your account before you can add a player.", ephemeral=True
            )
            return

        # 1. if account_name is provided, then someone other than the interaction.user is adding a player
        #    to the account_id corresoponding the specified account_name.
        if account_id is not None:
            account_id_final = account_id
            create_account_id = interaction_account_id
            update_account_id = interaction_account_id

        # 2. the interaction.user is adding a player to their own account
        else:
            account_id_final = interaction_account_id
            create_account_id = interaction_account_id
            update_account_id = interaction_account_id

        try:
            player_id = await create_player(
                account_id_final,
                kingshot_id,
                kingshot_name,
                power,
                town_center_level,
                kingdom,
                alliance,
                create_account_id,
                update_account_id,
            )
        except DupPlayerKingshotIdError:
            await interaction.response.send_message(
                f"❌ Player creation failed: kingshot_id '{kingshot_id}' "
                f"already exists, please check the Kingshot Player ID and try again", ephemeral=True
            )
            return
        except DupPlayerKingshotNameError:
            await interaction.response.send_message(
                f"❌ Player creation failed: kingshot_name '{kingshot_name}' "
                f"already exists, please check the Kingshot Player Name and try again", ephemeral=True
            )
            return
        except PlayerCreateError:
            logger.exception("Unexpected player creation error")
            await interaction.response.send_message(
                f"❌ Player creation failed: an unexpected error occurred while creating the player, "
                f"contact the admin and have him look at the logs", ephemeral=True
            )
            return

        if player_id is None:
            raise ValueError(
                f"Could not create player - returned player_id is None. Discord ID: {interaction.user.id}, "
                f"Account ID: {interaction_account_id}, Kingshot ID: {kingshot_id}, Kingshot Name: {kingshot_name}"
            )

        update_recent_players(interaction.user.id, player_id)  # ⭐️🕑

        await interaction.response.send_message(
                f"""✅ created player as:
```text
        player_id: {player_id}
       account_id: {account_id_final}
      kingshot_id: {kingshot_id}
    kingshot_name: {kingshot_name}
            power: {power}
town_center_level: {town_center_level}
          kingdom: {kingdom}
         alliance: {alliance}
create_account_id: {create_account_id}
update_account_id: {update_account_id}
```""",
            ephemeral=True,
        )


def update_recent_players(discord_user_id: int, player_id: int) -> None:
    recent_players: list[int] = session.get(discord_user_id, "recent_players", [])
    print(f"got recent_players: {recent_players}")
    if player_id in recent_players:
        recent_players.remove(player_id)
    print(f"after cond remove recent_players: {recent_players}")
    recent_players.insert(0, player_id)
    print(f"after insert recent_players: {recent_players}")
    recent_players = recent_players[:3]
    print(f"after trimming recent_players: {recent_players}")
    session.set(discord_user_id, "recent_players", recent_players)


class Admin(app_commands.Group):
    def __init__(self):
        super().__init__(name="admin", description="Administration Tools")

    # /admin init
    @app_commands.command(name="init", description="Initialize the owning Admin")
    @app_commands.autocomplete(tz_region=region_autocomplete)
    @app_commands.autocomplete(tz_location=timezone_autocomplete)
    async def init(
            self,
            interaction: discord.Interaction,
            tz_region: str,
            tz_location: str,
    ) -> None:
        bot = cast(KsEventSchedulerBot, interaction.client)

        if interaction.user.id != ADMIN_ZERO_ID:
            await interaction.response.send_message(
                "❌ You are not authorized to initialize the Admin account.", ephemeral=True
            )
            return
        if session.get(interaction.user.id, "roles") is not None:
            await interaction.response.send_message(
                "❌ The Admin account has already been initialize.", ephemeral=True
            )
            return

        # make sure the timezone region is valid, by getting the list of timezone locations for the specified region
        locations = bot.tz_names.get(tz_region)
        if not locations:
            await interaction.response.send_message(f"❌ Invalid timezone region: {tz_region}", ephemeral=True)
            return
        # validate that the specified timezone location exists for the region
        if tz_location not in locations:
            await interaction.response.send_message(f"❌ Invalid timezone location: {tz_location}", ephemeral=True)
            return
        account_tz = f"{tz_region}/{tz_location}"

        discord_id_final = interaction.user.id
        discord_name = interaction.user.name
        discord_nick = interaction.user.display_name
        account_name_final = discord_name
        account_type = "member"
        create_account_id = SELF_REGISTERED_ACCOUNT_ID  # user is adding themselves
        update_account_id = SELF_REGISTERED_ACCOUNT_ID  # for insert set update to create account id

        account_id = await create_account(
            account_type=account_type,
            account_name=account_name_final,
            account_tz=account_tz,
            discord_id=discord_id_final,
            discord_name=discord_name,
            discord_nick=discord_nick,
            create_account_id=create_account_id,
            update_account_id=update_account_id,
        )

        if account_id is None:
            raise ValueError(
                f"Could not create account - returned account_id is None. Discord ID: {discord_id_final}, "
                f"Account Name: {account_name_final}"
            )

        # TODO: modify database.py so that we have better transaction control.
        #   the create_account() call should not be committed until the create_admin() call succeeds.
        admin_id = await create_admin(
            account_id=account_id,
            admin_level="super",
            create_account_id=create_account_id,
        )

        if admin_id is None:
            raise ValueError(
                f"Count not create admin - returned admin_id is None. Discord ID: {discord_id_final}, "
            )

        session.set(discord_id_final, "account_id", account_id)
        session.set(discord_id_final, "account_name", account_name_final)
        session.set(discord_id_final, "roles", ["super"])

        bot.initialized = True

        await interaction.response.send_message(
                f"""✅ created account as:
```text
       account id: {account_id}
     account type: {account_type}
     account name: {account_name_final}
       account_tz: {account_tz}
       discord_id: {discord_id_final}
     discord_name: {discord_name}
     discord_nick: {discord_nick}
create_account_id: {create_account_id}
update_account_id: {update_account_id}
         admin id: {admin_id}
```""",
            ephemeral=True,
        )


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

        # if the user is registering another account (and not for themselves) get the interaction.user account id
        create_account_id = update_account_id = SELF_REGISTERED_ACCOUNT_ID
        if discord_user or discord_id or account_name:
            # create_account_id = await get_acct_id(discord_id=interaction.user.id)
            create_account_id = session.get(interaction.user.id, "account_id")
            update_account_id = create_account_id
            if create_account_id is None or update_account_id is None:
                await interaction.response.send_message(
                    "❌ You must have a registered account to register an account that is not your own.", ephemeral=True
                )
                return

        # convert discord_id (a string) into discord_id_final (an int) if it is not the empty string
        discord_id_final: int | None = None
        if discord_id:
            try:
                discord_id_final = int(discord_id)
            except ValueError:
                await interaction.response.send_message("❌ Invalid user_id. Must be a numeric Discord user ID.",
                                                        ephemeral=True)
                return

        # --------------------------------------------------
        # handle our 4 use cases
        # --------------------------------------------------

        # 1. if discord_user is provided, then someone other than the provided discord_user is
        #    registering an account for the specified discord_user.
        if discord_user is not None:
            discord_id_final = discord_user.id
            discord_name = discord_user.name
            discord_nick = discord_user.display_name
            account_name_final = discord_name
            account_type = "member"

        # 2. if (target) discord_id is provided, then someone other than the discord user
        #    corresponding to the provided discord_id is registering an account for the discord
        #    user that corresponds to the specified discord_id.
        elif discord_id_final is not None:
            try:
                # lookup the corresponding Discord user for the specified discord_id
                target_user = await bot.fetch_user(discord_id_final)
            except discord.NotFound:
                await interaction.response.send_message("❌ User not found on Discord.", ephemeral=True)
                return
            except discord.HTTPException:
                logger.exception("Unable to fetch Discord user %s", discord_id_final)
                await interaction.response.send_message(
                    "❌ Could not fetch user from Discord. Please try again later.", ephemeral=True
                )
                return
            discord_name = target_user.name
            discord_nick = None
            account_name_final = discord_name
            account_type = "user"

        # 3. if account_name is provided, then someone is registering an account for a
        #    user that is NOT a discord user.
        elif account_name:
            discord_id_final = None
            discord_name = None
            discord_nick = None
            account_name_final = account_name
            account_type = "manual"

        # 4. the user is self-registering an account for themselves.
        else:
            discord_id_final = interaction.user.id
            discord_name = interaction.user.name
            discord_nick = interaction.user.display_name
            account_name_final = discord_name
            account_type = "member"
            create_account_id = SELF_REGISTERED_ACCOUNT_ID  # user is adding themselves
            update_account_id = SELF_REGISTERED_ACCOUNT_ID  # for insert set update to create account id

        # make sure the timezone region is valid, by getting the list of timezone locations for the specified region
        locations = bot.tz_names.get(tz_region)
        if not locations:
            await interaction.response.send_message(f"❌ Invalid timezone region: {tz_region}", ephemeral=True)
            return
        # validate that the specified timezone location exists for the region
        if tz_location not in locations:
            await interaction.response.send_message(f"❌ Invalid timezone location: {tz_location}", ephemeral=True)
            return
        account_tz = f"{tz_region}/{tz_location}"

        try:
            account_id = await create_account(
                account_type=account_type,
                account_name=account_name_final,
                account_tz=account_tz,
                discord_id=discord_id_final,
                discord_name=discord_name,
                discord_nick=discord_nick,
                create_account_id=create_account_id,
                update_account_id=update_account_id,
            )
        except DupAcctAccountNameError:
            await interaction.response.send_message(
                f"❌ Account creation failed: account_name '{account_name_final}' "
                f"already exists, please check the Account Name and try again", ephemeral=True
            )
            return
        except DupAcctDiscordIdError:
            await interaction.response.send_message(
                f"❌ Account creation failed: discord_id '{discord_id_final}' "
                f"already exists, please check the Discord ID and try again", ephemeral=True
            )
            return
        except AcctCreateError:
            logger.exception("Unexpected account creation error")
            await interaction.response.send_message(
                f"❌ Account creation failed: an unexpected error occurred while creating the account, "
                f"contact the admin and have him look at the logs", ephemeral=True
            )
            return

        if account_id is None:
            raise ValueError(
                f"Could not create account - returned account_id is None. Discord ID: {discord_id_final}, "
                f"Account Name: {account_name_final}"
            )

        if account_type != "manual":
            if discord_id_final is None:
                raise ValueError("Discord ID not specified - cannot set user state!")
            session.set(discord_id_final, "account_id", account_id)
            session.set(discord_id_final, "account_name", account_name_final)
            session.set(discord_id_final, "roles", [])

        await interaction.response.send_message(
                f"""✅ created account as:
```text
       account id: {account_id}
     account type: {account_type}
     account name: {account_name_final}
       account_tz: {account_tz}
       discord_id: {discord_id_final}
     discord_name: {discord_name}
     discord_nick: {discord_nick}
create_account_id: {create_account_id}
update_account_id: {update_account_id}
```""",
            ephemeral=True,
        )


# --------------------------------------------------
# Bot setup
# --------------------------------------------------

class KsEventSchedulerBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        # self.initialized = False
        self.tz_names: dict[str, list[str]] = {}
        self.tz_region_choices: list[app_commands.Choice[str]] = []

    async def setup_hook(self):
        # self.initialized = await is_initialized()
        # print("init", self.initialized)

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

    # async def interaction_check(self, interaction: discord.Interaction) -> bool:
    #     bot = cast(KsEventSchedulerBot, interaction.client)
    #
    #     print("interaction check 0", interaction.command.qualified_name)
    #
    #     # Allow /admin init even before initialization
    #     if interaction.command and interaction.command.qualified_name == "admin init":
    #         print("interaction check 1")
    #         return True
    #
    #     if not bot.initialized:
    #         await interaction.response.send_message(
    #             "❌ This bot has not been initialized. The Admin Zero Discord user must run `/admin init` first.",
    #             ephemeral=True,
    #         )
    #         return False
    #
    #     print("interaction check 2")
    #     return True

    async def sync_commands(self):
        try:
            # Sync logic (DEBUG vs PRODUCTION)
            logger.info("Top-level commands BEFORE sync:")
            for cmd in self.tree.get_commands():
                logger.info(" - %s (%s)", cmd.name, type(cmd).__name__)

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

# @ks_event_scheduler_bot.event
# async def on_interaction(interaction: discord.Interaction):
#     bot = cast(KsEventSchedulerBot, interaction.client)
#
#     print("RAW INTERACTION RECEIVED:", interaction.data)
#
#     # Extract command name safely
#     data = interaction.data or {}
#     name = data.get("name")
#
#     # Allow admin init ALWAYS
#     if name == "admin":
#         return
#
#     # Block everything else until initialized
#     if not getattr(bot, "initialized", False):
#         if interaction.type == discord.InteractionType.application_command:
#             await interaction.response.send_message(
#                 "❌ Bot not initialized. Run /admin init first.",
#                 ephemeral=True,
#             )
#         return

ks_event_scheduler_bot.tree.add_command(Admin())
ks_event_scheduler_bot.tree.add_command(Account())
ks_event_scheduler_bot.tree.add_command(Player())
ks_event_scheduler_bot.run(TOKEN)
