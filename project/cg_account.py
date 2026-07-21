from typing import cast
import logging

import discord
from discord import app_commands

import read_env
import shared_state
from cmd_check import BotMode, cc_admin_bot_mode_at_least_admin, cvl_at_least_admin, Role
from ks_db import create_account
from ks_db_errors import AcctCreateError, DupAcctAccountNameError, DupAcctDiscordIdError
from ks_event_scheduler_bot import KsEventSchedulerBot


logger = logging.getLogger("ksbot.acct")


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


class Account(app_commands.Group):
    def __init__(self):
        super().__init__(name="account", description="User Account Tools")

    @staticmethod
    async def _reject_register_request(
            interaction: discord.Interaction,
            discord_user: discord.User | None,
            discord_id: str | None,
            account_name: str | None,
    ) -> bool:
        curr_bot_mode = BotMode.curr_bot_mode()

        if curr_bot_mode == BotMode.DOWN:
            await interaction.response.send_message(
                "❌Sorry the bot is currently down. You cannot Register an account at this time.",
                ephemeral=True,
            )
            return True

        if curr_bot_mode == BotMode.MAINTENANCE:
            is_authorized, authorization_error = cc_admin_bot_mode_at_least_admin.command_check(
                interaction.user.id
            )
            if not is_authorized:
                authorization_error = authorization_error[:-1] + f" when the bot is {curr_bot_mode.msg_desc}."
                await interaction.response.send_message(authorization_error, ephemeral=True)
                return True

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
    async def _validate_register_account_inputs(
            interaction: discord.Interaction,
            discord_user: discord.User | None,
            discord_id: str | None,
            account_name: str | None,
    ) -> tuple[bool, int | None, int | None, int | None]:
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
            return True, None, None, None

        # if the user is registering another account (and not for themselves) get the interaction.user account id
        create_account_id = update_account_id = config.SELF_REGISTERED_ACCOUNT_ID
        if discord_user or discord_id or account_name:
            # create_account_id = await get_acct_id(discord_id=interaction.user.id)
            create_account_id = session.get(interaction.user.id, "account_id")
            update_account_id = create_account_id
            if create_account_id is None or update_account_id is None:
                await interaction.response.send_message(
                    "❌ You must have a registered account to register an account that is not your own.", ephemeral=True
                )
                return True, None, None, None

        # convert discord_id (a string) into discord_id_final (an int) if it is not the empty string
        discord_id_final: int | None = None
        if discord_id:
            try:
                discord_id_final = int(discord_id)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid user_id. Must be a numeric Discord user ID.", ephemeral=True)
                return True, None, None, None

        return False, discord_id_final, create_account_id, update_account_id

    @staticmethod
    async def _resolve_register_account_details(
            interaction: discord.Interaction,
            discord_user: discord.User | None,
            discord_id_final: int | None,
            account_name: str | None,
            create_account_id: int | None,
            update_account_id: int | None,
    ) -> tuple[bool, int | None, str | None, str | None, str, str, int | None, int | None]:
        config = read_env.load_config()
        bot = cast(KsEventSchedulerBot, interaction.client)

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
                return True, None, None, None, "", "", None, None
            except discord.HTTPException:
                logger.exception("Unable to fetch Discord user %s", discord_id_final)
                await interaction.response.send_message(
                    "❌ Could not fetch user from Discord. Please try again later.", ephemeral=True
                )
                return True, None, None, None, "", "", None, None

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
            create_account_id = config.SELF_REGISTERED_ACCOUNT_ID  # user is adding themselves
            update_account_id = config.SELF_REGISTERED_ACCOUNT_ID  # for insert set update to create account id

        return (
            False,
            discord_id_final,
            discord_name,
            discord_nick,
            account_name_final,
            account_type,
            create_account_id,
            update_account_id,
        )

    @staticmethod
    async def _validate_register_timezone(
            interaction: discord.Interaction,
            tz_region: str,
            tz_location: str,
    ) -> tuple[bool, str | None]:
        bot = cast(KsEventSchedulerBot, interaction.client)

        # make sure the timezone region is valid, by getting the list of timezone locations for the specified region
        locations = bot.tz_names.get(tz_region)
        if not locations:
            await interaction.response.send_message(f"❌ Invalid timezone region: {tz_region}", ephemeral=True)
            return True, None

        # validate that the specified timezone location exists for the region
        if tz_location not in locations:
            await interaction.response.send_message(f"❌ Invalid timezone location: {tz_location}", ephemeral=True)
            return True, None

        return False, f"{tz_region}/{tz_location}"

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
        session = shared_state.get_session()

        rejected = await self._reject_register_request(
            interaction,
            discord_user,
            discord_id,
            account_name,
        )
        if rejected:
            return

        (
            invalid_inputs,
            discord_id_final,
            create_account_id,
            update_account_id
        ) = await self._validate_register_account_inputs(
            interaction,
            discord_user,
            discord_id,
            account_name,
        )
        if invalid_inputs:
            return

        bot = cast(KsEventSchedulerBot, interaction.client)

        (
            unresolved,
            discord_id_final,
            discord_name,
            discord_nick,
            account_name_final,
            account_type,
            create_account_id,
            update_account_id,
        ) = await self._resolve_register_account_details(
            interaction,
            discord_user,
            discord_id_final,
            account_name,
            create_account_id,
            update_account_id,
        )
        if unresolved:
            return

        invalid_timezone, account_tz = await self._validate_register_timezone(
            interaction,
            tz_region,
            tz_location,
        )
        if invalid_timezone:
            return

        # none of these variables should be None at this point, if they are then something went wrong and we should raise an error
        if account_tz is None:
            raise ValueError("Account timezone was not resolved.")
        if create_account_id is None:
            raise ValueError("Create account ID was not resolved.")
        if update_account_id is None:
            raise ValueError("Update account ID was not resolved.")

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
            session.set(discord_id_final, "account_tz", account_tz)

        await interaction.response.send_message("Account registered successfully.", ephemeral=True)