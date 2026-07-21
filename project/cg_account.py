from dataclasses import dataclass
from typing import cast
import logging

import discord
from discord import app_commands

import read_env
import shared_state
from cmd_check import BotMode, cc_admin_bot_mode_at_least_admin, cvl_at_least_admin, Role
from ks_db import create_account, get_accounts, get_accounts_ac, get_account_by_id
from ks_db_errors import AcctCreateError, DupAcctAccountNameError, DupAcctDiscordIdError
from ks_event_scheduler_bot import KsEventSchedulerBot
from bot_utils import utc_to_local


logger = logging.getLogger("ksbot.acct")


# --------------------------------------------------
# Autocomplete Functions
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
    accounts = await get_accounts_ac(current)
    return [
        app_commands.Choice[int](
            name=account_name,
            value=account_id,
        )
        for account_name, account_id in accounts
    ]


# --------------------------------------------------
# Data Classes - context objects
# --------------------------------------------------

@dataclass
class RegistrationContext:
    # Input/Target Info
    discord_id_final: int | None = None
    create_account_id: int | None = None
    update_account_id: int | None = None

    # Resolved Details
    discord_name: str | None = None
    discord_nick: str | None = None
    account_name_final: str = ""
    account_type: str = ""

    # Validation Results
    account_tz: str | None = None
    account_id: int | None = None


# --------------------------------------------------
# Account Command Group
# --------------------------------------------------

class Account(app_commands.Group):
    def __init__(self):
        super().__init__(name="account", description="User Account Tools")

    # --------------------------------------------------
    # helpers
    # --------------------------------------------------

    @staticmethod
    async def _reject_register_request(
            interaction: discord.Interaction,
            discord_user: discord.User | None,
            discord_id: str | None,
            account_name: str | None,
    ) -> bool:
        curr_bot_mode = BotMode.curr_bot_mode()

        # do not allow command execution if the bot is down
        if curr_bot_mode == BotMode.DOWN:
            await interaction.response.send_message(
                "❌Sorry the bot is currently down. You cannot Register an account at this time.",
                ephemeral=True,
            )
            return True

        # if the bot is under maintenance, only allow Admins to register accounts
        if curr_bot_mode == BotMode.MAINTENANCE:
            is_authorized, authorization_error = cc_admin_bot_mode_at_least_admin.command_check(
                interaction.user.id
            )
            if not is_authorized:
                authorization_error = authorization_error[:-1] + f" when the bot is {curr_bot_mode.msg_desc}."
                await interaction.response.send_message(authorization_error, ephemeral=True)
                return True

        # to register an account for another user, the user must be an Admin
        users_roles = set(Role.get_user_roles(interaction.user.id))
        if not cvl_at_least_admin.check(users_roles):
            if discord_user or discord_id or account_name:
                await interaction.response.send_message(
                    "❌You may only register an account for yourself. You cannot specify discord_user, discord_id, or account_name unless you are an Admin.",
                    ephemeral=True,
                )
                return True

        return False

    @staticmethod
    async def _reject_account_list_request(
            interaction: discord.Interaction,
    ) -> bool:
        curr_bot_mode = BotMode.curr_bot_mode()

        # do not allow command execution if the bot is down
        if curr_bot_mode == BotMode.DOWN:
            await interaction.response.send_message(
                "❌Sorry the bot is currently down. You cannot Register an account at this time.",
                ephemeral=True,
            )
            return True

        # if the bot is under maintenance, only allow Admins to register accounts
        if curr_bot_mode == BotMode.MAINTENANCE:
            is_authorized, authorization_error = cc_admin_bot_mode_at_least_admin.command_check(
                interaction.user.id
            )
            if not is_authorized:
                authorization_error = authorization_error[:-1] + f" when the bot is {curr_bot_mode.msg_desc}."
                await interaction.response.send_message(authorization_error, ephemeral=True)
                return True

        return False

    @staticmethod
    async def _validate_register_account_inputs(
            interaction: discord.Interaction,
            ctx: RegistrationContext,
            discord_user: discord.User | None,
            discord_id: str | None,
            account_name: str | None,
    ) -> bool:
        config = read_env.load_config()
        session = shared_state.get_session()

        # discord_user, discord_id, account_name are optional and MUTUALLY EXCLUSIVE
        discord_id = discord_id.strip() if discord_id else ""
        account_name = account_name.strip() if account_name else ""
        set_count = sum(bool(value) for value in (discord_user, discord_id, account_name))
        if set_count > 1:
            await interaction.response.send_message(
                "❌ You can only specify one of `discord_user`, `discord_id` or `account_name`.", ephemeral=True
            )
            return True

        # if the user is registering another account (and not for themselves) get the interaction.user account id
        ctx.create_account_id = ctx.update_account_id = config.SELF_REGISTERED_ACCOUNT_ID
        if discord_user or discord_id or account_name:
            # create_account_id = await get_acct_id(discord_id=interaction.user.id)
            ctx.create_account_id = session.get(interaction.user.id, "account_id")
            ctx.update_account_id = ctx.create_account_id
            if ctx.create_account_id is None or ctx.update_account_id is None:
                await interaction.response.send_message(
                    "❌ You must have a registered account to register an account that is not your own.", ephemeral=True
                )
                return True

        # convert discord_id (a string) into discord_id_final (an int) if it is not the empty string
        if discord_id:
            try:
                ctx.discord_id_final = int(discord_id)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid user_id. Must be a numeric Discord user ID.", ephemeral=True)
                return True

        return False

    @staticmethod
    async def _resolve_register_account_details(
            interaction: discord.Interaction,
            ctx: RegistrationContext,
            discord_user: discord.User | None,
            account_name: str | None,
    ) -> bool:
        config = read_env.load_config()
        bot = cast(KsEventSchedulerBot, interaction.client)

        # --------------------------------------------------
        # handle our 4 use cases
        # --------------------------------------------------

        # 1. if discord_user is provided, then someone other than the provided discord_user is
        #    registering an account for the specified discord_user.
        if discord_user is not None:
            ctx.discord_id_final = discord_user.id
            ctx.discord_name = discord_user.name
            ctx.discord_nick = discord_user.display_name
            ctx.account_name_final = discord_user.name
            ctx.account_type = "member"

        # 2. if (target) discord_id is provided, then someone other than the discord user
        #    corresponding to the provided discord_id is registering an account for the discord
        #    user that corresponds to the specified discord_id.
        elif ctx.discord_id_final is not None:
            try:
                # lookup the corresponding Discord user for the specified discord_id
                target_user = await bot.fetch_user(ctx.discord_id_final)
            except discord.NotFound:
                await interaction.response.send_message("❌ User not found on Discord.", ephemeral=True)
                return True
            except discord.HTTPException:
                logger.exception("Unable to fetch Discord user %s", ctx.discord_id_final)
                await interaction.response.send_message(
                    "❌ Could not fetch user from Discord. Please try again later.", ephemeral=True
                )
                return True

            ctx.discord_name = target_user.name
            ctx.discord_nick = None
            ctx.account_name_final = target_user.name
            ctx.account_type = "user"

        # 3. if account_name is provided, then someone is registering an account for a
        #    user that is NOT a discord user.
        elif account_name:
            ctx.discord_id_final = None
            ctx.discord_name = None
            ctx.discord_nick = None
            ctx.account_name_final = account_name
            ctx.account_type = "manual"

        # 4. the user is self-registering an account for themselves.
        else:
            ctx.discord_id_final = interaction.user.id
            ctx.discord_name = interaction.user.name
            ctx.discord_nick = interaction.user.display_name
            ctx.account_name_final = interaction.user.name
            ctx.account_type = "member"
            ctx.create_account_id = config.SELF_REGISTERED_ACCOUNT_ID  # user is adding themselves
            ctx.update_account_id = config.SELF_REGISTERED_ACCOUNT_ID  # for insert set update to create account id

        return False

    @staticmethod
    async def _validate_register_timezone(
            interaction: discord.Interaction,
            ctx: RegistrationContext,
            tz_region: str,
            tz_location: str,
    ) -> bool:
        bot = cast(KsEventSchedulerBot, interaction.client)

        # make sure the timezone region is valid, by getting the list of timezone locations for the specified region
        locations = bot.tz_names.get(tz_region)
        if not locations:
            await interaction.response.send_message(f"❌ Invalid timezone region: {tz_region}", ephemeral=True)
            return True

        # validate that the specified timezone location exists for the region
        if tz_location not in locations:
            await interaction.response.send_message(f"❌ Invalid timezone location: {tz_location}", ephemeral=True)
            return True

        ctx.account_tz = f"{tz_region}/{tz_location}"
        return False

    @staticmethod
    async def _perform_account_creation(
            interaction: discord.Interaction,
            ctx: RegistrationContext,
    ) -> bool:
        # none of these variables should be None at this point, if they are then something went wrong and we should raise an error
        if ctx.account_tz is None:
            raise ValueError("Account timezone was not resolved.")
        if ctx.create_account_id is None:
            raise ValueError("Create account ID was not resolved.")
        if ctx.update_account_id is None:
            raise ValueError("Update account ID was not resolved.")

        try:
            ctx.account_id = await create_account(
                account_type=ctx.account_type,
                account_name=ctx.account_name_final,
                account_tz=ctx.account_tz,
                discord_id=ctx.discord_id_final,
                discord_name=ctx.discord_name,
                discord_nick=ctx.discord_nick,
                create_account_id=ctx.create_account_id,
                update_account_id=ctx.update_account_id,
            )
        except DupAcctAccountNameError:
            await interaction.response.send_message(
                f"❌ Account creation failed: account_name '{ctx.account_name_final}' "
                f"already exists, please check the Account Name and try again", ephemeral=True
            )
            return True
        except DupAcctDiscordIdError:
            await interaction.response.send_message(
                f"❌ Account creation failed: discord_id '{ctx.discord_id_final}' "
                f"already exists, please check the Discord ID and try again", ephemeral=True
            )
            return True
        except AcctCreateError:
            logger.exception("Unexpected account creation error")
            await interaction.response.send_message(
                f"❌ Account creation failed: an unexpected error occurred while creating the account, "
                f"contact the admin and have him look at the logs", ephemeral=True
            )
            return True

        if ctx.account_id is None:
            raise ValueError(
                f"Could not create account - returned account_id is None. Discord ID: {ctx.discord_id_final}, "
                f"Account Name: {ctx.account_name_final}"
            )

        return False

    @staticmethod
    def _finalize_registration(
            ctx: RegistrationContext,
    ) -> None:
        session = shared_state.get_session()

        if ctx.account_type != "manual":
            if ctx.discord_id_final is None:
                raise ValueError("Discord ID not specified - cannot set user state!")
            session.set(ctx.discord_id_final, "account_id", ctx.account_id)
            session.set(ctx.discord_id_final, "account_name", ctx.account_name_final)
            session.set(ctx.discord_id_final, "account_tz", ctx.account_tz)

    # --------------------------------------------------
    # slash commands
    # --------------------------------------------------

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
        ctx = RegistrationContext()

        if await self._reject_register_request(
                interaction,
                discord_user,
                discord_id,
                account_name,
        ):
            return

        if await self._validate_register_account_inputs(
                interaction,
                ctx,
                discord_user,
                discord_id,
                account_name,
        ):
            return

        if await self._resolve_register_account_details(
                interaction,
                ctx,
                discord_user,
                account_name,
        ):
            return

        if await self._validate_register_timezone(
                interaction,
                ctx,
                tz_region,
                tz_location,
        ):
            return

        if await self._perform_account_creation(
                interaction,
                ctx,
        ):
            return

        self._finalize_registration(ctx)

        await interaction.response.send_message(
f"""✅ created account as:
```text
       account id: {ctx.account_id}
     account type: {ctx.account_type}
     account name: {ctx.account_name_final}
       account_tz: {ctx.account_tz}
       discord_id: {ctx.discord_id_final}
     discord_name: {ctx.discord_name}
     discord_nick: {ctx.discord_nick}
create_account_id: {ctx.create_account_id}
update_account_id: {ctx.update_account_id}
```""",
            ephemeral=True,
        )

    # /account list
    @app_commands.command(name="list", description="List all registered accounts")
    async def list(self, interaction: discord.Interaction):
        if await self._reject_account_list_request(interaction):
            return

        accounts = await get_accounts()
        if not accounts:
            await interaction.response.send_message("❌ No accounts found.", ephemeral=True)
            return

        # todo: change this over to use the pagination system
        # Format and send the list of accounts
        account_list_str = "\n".join(
            f"ID: {acct['account_id']} Name: {acct['account_name']} TZ: {acct['account_tz']} Player Cnt: {acct['player_count']}"
            for acct in accounts
        )
        await interaction.response.send_message(f"Registered Accounts:\n```text\n{account_list_str}```", ephemeral=True)

    # /account show
    @app_commands.command(name="show", description="Show details of a registered account")
    @app_commands.autocomplete(account_id=account_id_autocomplete)
    async def show(self, interaction: discord.Interaction, account_id: int):
        if await self._reject_account_list_request(interaction):
            return

        account = await get_account_by_id(account_id)
        if not account:
            await interaction.response.send_message(f"❌ Account with ID {account_id} not found.", ephemeral=True)
            return

        session = shared_state.get_session()
        user_tz_name = session.get(interaction.user.id, "account_tz", "UTC")
        max_label_len = max(len(label) for label in account.keys())

        # Format and send the account details
        account_lines = []
        for key, value in account.items():
            if key in ("create_date_time", "update_date_time",):
                value = utc_to_local(account[key], user_tz_name)
            account_lines.append(f"{key:>{max_label_len}}: {value}")
        account_details_str = "\n".join(account_lines)

        await interaction.response.send_message(f"Account Details:\n```text\n{account_details_str}```", ephemeral=True)