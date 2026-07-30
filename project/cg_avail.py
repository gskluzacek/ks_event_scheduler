import logging

import discord
from discord import app_commands


logger = logging.getLogger("ksbot.avail")


# --------------------------------------------------
# Autocomplete Functions
# --------------------------------------------------

# put autocomplete functions in bot_autocomplete.py !!!

# --------------------------------------------------
# Data Classes - context objects
# --------------------------------------------------

# none at this time

# --------------------------------------------------
# avail table columns
# --------------------------------------------------
#
#   avail_id
#   event_id
#   player_id
#   avail_type
#   priority
#   start_time
#   end_time
#   validated_ind
#   create_account_id
#   create_date_time
#   update_account_id
#   update_date_time

# --------------------------------------------------
# Availability Command Group
# --------------------------------------------------

class Avail(app_commands.Group):
    def __init__(self):
        super().__init__(name="avail", description="Kingshot Player Availability Tools")

    # /avail add: inserts a record into the avails table.
    #   uses the active player and event stored in the player session state.
    #   user must specify
    #       - avail_type:     prefered, acceptable, avoid
    #       - start_time:     This is in the user's LOCAL time. It time value only, in 24 hour format.
    #                         It is specified in 15 minute increments, e.g. 14:00, 14:15, 14:30, 14:45, 15:00, etc.
    #       - end_time:       see start_time details.
    #       - priority:       integer
    #   validated_ind:        defaults to 1 (true), the scheduling admin can set this to 0 (false) and ask the player to confirm their availablity is accruate.
    #   create_date_time:     set to the current timestamp
    #   update_date_time:
    #   create_account_id:    set to the account_id of the person executing the command
    #   update_account_id:
    @app_commands.command(name="add", description="Add Availability for a Kingshot Player")
    async def add(
            self,
            interaction: discord.Interaction,
            avail_type: str,
            start_time: str,
            end_time: str,
            priority: int | None = None,
            player_id: int | None = None,
            event_id: int | None = None,
    ):
        await interaction.response.send_message("✅ availability added", ephemeral=True)

    # /avail edit: updates a record in the avails table.
    @app_commands.command(name="edit", description="Edit Availability for a Kingshot Player")
    async def edit(
            self,
            interaction: discord.Interaction,
            player_id: int | None = None,
            event_id: int | None = None,
            avail_id: int | None = None,
    ):
        await interaction.response.send_message("✅ availability updated", ephemeral=True)

    # /avail remove: delete a record from the avails table.
    @app_commands.command(name="remove", description="Removes Availability for a Kingshot Player")
    async def remove(
            self,
            interaction: discord.Interaction,
            player_id: int | None = None,
            event_id: int | None = None,
            avail_id: int | None = None,
    ):
        await interaction.response.send_message("✅ availability deleted", ephemeral=True)

    # /avail list: lists all records in the avails table for the active player and event
    @app_commands.command(name="list", description="List Availability for a Kingshot Player")
    async def list(
            self,
            interaction: discord.Interaction,
            player_id: int | None = None,
            event_id: int | None = None,
    ):
        await interaction.response.send_message("✅ availability listed", ephemeral=True)

    # /avail show: shows a specific record in the avails table for the active player and event
    @app_commands.command(name="show", description="Show Availability for a Kingshot Player")
    async def show(
            self,
            interaction: discord.Interaction,
            player_id: int | None = None,
            event_id: int | None = None,
            avail_id: int | None = None,
    ):
        # thinking ...
        # will use the active player and envent by default
        # you can specify a player_id and event_id to show a specific records
        await interaction.response.send_message("✅ availability shown", ephemeral=True)
