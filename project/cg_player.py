import logging

import discord
from discord import app_commands
# from discord.ext import commands

import read_env
import shared_state
from bot_cmd_access import _reject_account_list_request
from cmd_check import Role, cvl_at_least_admin

from ks_db import create_player
from ks_db_errors import PlayerCreateError, DupPlayerKingshotIdError, DupPlayerKingshotNameError


logger = logging.getLogger("ksbot.plyr")


class Player(app_commands.Group):
    def __init__(self):
        super().__init__(name="player", description="Kingshot Player Tools")


    # /player add
    @app_commands.command(name="add", description="Add a Kingshot Player to an account")
    async def add(
            self,
            interaction: discord.Interaction,
            kingshot_id: int,
            kingshot_name: str,
            power: float,
            town_center_level: str,
            kingdom: int | None = None,
            alliance: str | None = None,
            account_id: int | None = None,
    ):
        session = shared_state.get_session()

        if await _reject_account_list_request(interaction):
            return

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

        # to register an account for another user, the user must be an Admin
        users_roles = set(Role.get_user_roles(interaction.user.id))
        if not cvl_at_least_admin.check(users_roles):
            if account_id:
                await interaction.response.send_message(
                    "❌You may only add a player to your own account. You cannot specify account_id unless you are an Admin.",
                    ephemeral=True,
                )
                return

        # 1. if account_id is provided, then someone other than the interaction.user is adding a player
        #    to the account_id corresponding to the specified account_id.
        if account_id is not None:
            account_id_final = account_id
            create_account_id = interaction_account_id
            update_account_id = interaction_account_id

        # 2. the interaction.user is adding a player to their own account
        else:
            account_id_final = interaction_account_id
            create_account_id = interaction_account_id
            update_account_id = interaction_account_id

        config = read_env.get_config()
        kingdom = kingdom or config.DEFAULT_KINGDOM
        alliance = alliance or config.DEFAULT_ALLIANCE

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
