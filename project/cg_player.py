import logging

import discord
from discord import app_commands
# from discord.ext import commands

import read_env
import shared_state
from bot_cmd_access import _down_or_maint_check
from cmd_check import Role, cvl_at_least_admin
from bot_autocomplete import account_id_autocomplete, account_id_autocomplete_wall, player_id_autocomplete, \
    player_id_for_active_account_autocomplete
from ks_db import create_player, get_players_for_account, get_account_by_id, get_player
from ks_db_errors import PlayerCreateError, DupPlayerKingshotIdError, DupPlayerKingshotNameError
from bot_utils import utc_to_local


logger = logging.getLogger("ksbot.plyr")


# --------------------------------------------------
# Autocomplete Functions
# --------------------------------------------------

# put autocomplete functions in bot_autocomplete.py !!!

# --------------------------------------------------
# Data Classes - context objects
# --------------------------------------------------

# none at this time

# --------------------------------------------------
# Player Command Group
# --------------------------------------------------

class Player(app_commands.Group):
    def __init__(self):
        super().__init__(name="player", description="Kingshot Player Tools")

    # /player add
    @app_commands.command(name="add", description="Add a Kingshot Player to an Account")
    @app_commands.autocomplete(account_id=account_id_autocomplete)
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

        # TODO: refactor this method ino smaller methods to make it more readable and maintainable

        if await _down_or_maint_check(interaction):
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

        # 1. if account_id is provided, then an admin is adding a player to another user's account.
        #       In this case, we will use the provided account_id to create the player.
        # 2. else use active_account_id of the interaction.user which could be either a normal user
        #       or an admin user (only admin users can change their active_account_id).
        account_id_final = account_id or session.get(interaction.user.id, "active_account_id")
        if account_id_final is None:
            await interaction.response.send_message(
                "❌ An unexpected error occured - final account id is None. Cannot add the account", ephemeral=True
            )
            return

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

        session = shared_state.get_session()
        session.set(interaction.user.id, "active_player_id", player_id)

        # TODO: when adding a player, we should show the account name tha playwer was added to. And we should also
        #  show the account name of the user that created the player. I don't think we need to show the
        #  updating account id / name as we just created the plaer.

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

    # TODO: we might want to rethink how we are doing the /player list commnad
    #       instead of allowing the user to specify an account_id, we should restrict them
    #       to only being able to list players for their active account.
    #       admins can set theier active account to any account they want, but normal users cannot.

    # TODO: we could add a set of query commands to allow normal users to list/show accounts and players
    #       for any account.

    # /player list
    @app_commands.command(name="list", description="List Kingshot Players")
    @app_commands.autocomplete(account_id=account_id_autocomplete_wall)
    async def list(
            self,
            interaction: discord.Interaction,
            account_id: int | None = None,
    ):
        if await _down_or_maint_check(interaction):
            return

        session = shared_state.get_session()
        account_id_final = account_id or session.get(interaction.user.id, "active_account_id")
        if account_id_final is None:
            await interaction.response.send_message(
                "❌ An unexpected error occured - final account id is None. Cannot list the players for the account", ephemeral=True
            )
            return

        players = await get_players_for_account(account_id_final)
        if not players:
            await interaction.response.send_message(
                f"❌ No players found for account ID {account_id_final}", ephemeral=True
            )
            return

        header_detail = ""
        if account_id_final != 0:
            account = await get_account_by_id(account_id_final)
            if account is None:
                await interaction.response.send_message(
                    f"❌ Oops something went wrong! No account found for account ID {account_id_final}", ephemeral=True
                )
                return
            header_detail = f" for ID: {account_id_final}, Account Name: {account['account_name']}"

        # todo: change this over to use the pagination system

        # TODO: try multiple line output for a single player. like output a header line with the player_id and kingshot_name,
        #       then output the rest of the player info on separate lines indented under the header line. This will make
        #       it easier to read the player list when there are many players with long names. or on mobile divices.

        player_list = []
        for player in players:
            player_str = ""
            if account_id_final == 0:
                player_str = f"ID: {player['account_id']}, Account Name: {player['account_name']} "
            player_str += f"Player ID: {player['player_id']} KS Name: {player['kingshot_name']} Power: {player['power']}"
            player_list.append(player_str)
        player_list_str = "\n".join(player_list)

        await interaction.response.send_message(f"Registered Players{header_detail}\n```text\n{player_list_str}```", ephemeral=True)

    # todo: we might want to rethink how we are doing the /player show commnad
    #       instead of using the player_id_autocomplete, we should use the
    #       player_id_for_active_account_autocomplete, so that the user can only show
    #       players for their active account.
    #       admins can set their active account to any account they want, but normal users cannot.

    # /player show
    @app_commands.command(name="show", description="Show Kingshot Player Details")
    @app_commands.autocomplete(player_id=player_id_autocomplete)
    async def show(
            self,
            interaction: discord.Interaction,
            player_id: int | None = None
    ):
        if await _down_or_maint_check(interaction):
            return

        session = shared_state.get_session()

        if player_id is None:
            player_id = session.get(interaction.user.id, "active_player_id")
            if player_id is None:
                await interaction.response.send_message("❌ You did not select a player and there is no active player set. Cannot show player details.", ephemeral=True)
                return

        player = await get_player(player_id)
        if not player:
            await interaction.response.send_message(f"❌ Player with ID {player_id} not found.", ephemeral=True)
            return

        user_tz_name = session.get(interaction.user.id, "account_tz", "UTC")
        max_label_len = max(len(label) for label in player.keys())

        # Format and send the player details
        player_lines = []
        for key, value in player.items():
            if key in ("create_date_time", "update_date_time",):
                value = utc_to_local(player[key], user_tz_name)
            player_lines.append(f"{key:>{max_label_len}}: {value}")
        player_details_str = "\n".join(player_lines)

        await interaction.response.send_message(f"Showing Details for Player ID: {player_id}\n```text\n{player_details_str}```", ephemeral=True)

    # /player activate
    @app_commands.command(name="activate", description="Set the Active Player to work with")
    @app_commands.autocomplete(player_id=player_id_for_active_account_autocomplete)
    async def activate(
            self,
            interaction: discord.Interaction,
            player_id: int | None = None
    ):
        if await _down_or_maint_check(interaction):
            return

        session = shared_state.get_session()

        # If player_id is None, then we want to show the currently active player for the user.
        if player_id is None:
            active_player_id = session.get(interaction.user.id, "active_player_id")
            if active_player_id is None:
                await interaction.response.send_message("✅ No active player has been set.", ephemeral=True)
                return
            player = await get_player(active_player_id)
            if not player:
                await interaction.response.send_message(f"❌ Active player with ID {active_player_id} not found.", ephemeral=True)
                return
            await interaction.response.send_message(f"✅ Active Player ID: {active_player_id}, Name: {player['kingshot_name']}", ephemeral=True)

        # If player_id is provided, then we want to set that player as the active player for the user.
        else:
            player = await get_player(player_id)
            if not player:
                await interaction.response.send_message(f"❌ Player with ID {player_id} not found.", ephemeral=True)
                return
            session.set(interaction.user.id, "active_player_id", player_id)
            await interaction.response.send_message(f"✅ Activated Player Name: {player['kingshot_name']}, ID: {player_id}", ephemeral=True)
