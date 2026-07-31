import logging

import discord
from discord import app_commands


logger = logging.getLogger("ksbot.timeslot")


# --------------------------------------------------
# Autocomplete Functions
# --------------------------------------------------

# put autocomplete functions in bot_autocomplete.py !!!

# --------------------------------------------------
# Data Classes - context objects
# --------------------------------------------------

# none at this time

# --------------------------------------------------
# time_slots table columns
# --------------------------------------------------
#
#   tslot_id
#   event_id
#   player_id
#   tslot_type
#   priority
#   start_time
#   end_time
#   validated_ind
#   create_account_id
#   create_date_time
#   update_account_id
#   update_date_time

# --------------------------------------------------
# Time Slot Command Group
# --------------------------------------------------

class TimeSlot(app_commands.Group):
    def __init__(self):
        super().__init__(name="timeslot", description="Kingshot Player available Time Slot Tools")

    # /timeslot add: inserts a record into the time_slots table.
    #   uses the active player and event stored in the player session state.
    #   user must specify
    #       - tslot_type:     prefered, acceptable, avoid
    #       - start_time:     This is in the user's LOCAL time. It is only the time value, in 24 hour format.
    #                         It is specified in 15 minute increments, e.g. 14:00, 14:15, 14:30, 14:45, 15:00, etc.
    #       - end_time:       see start_time details.
    #       - priority:       integer
    #   validated_ind:        defaults to 1 (true), the scheduling admin can set this to 0 (false) and ask the player to confirm their time slot is accurate.
    #   create_date_time:     set to the current timestamp
    #   update_date_time:
    #   create_account_id:    set to the account_id of the person executing the command
    #   update_account_id:
    @app_commands.command(name="add", description="Add an available Time Slot for a Kingshot Player")
    async def add(
            self,
            interaction: discord.Interaction,
            tslot_type: str,
            start_time: str,
            end_time: str,
            priority: int | None = None,
            player_id: int | None = None,
            event_id: int | None = None,
    ):
        await interaction.response.send_message("✅ time slot added", ephemeral=True)

    # /timeslot edit: updates a record in the time_slots table.
    @app_commands.command(name="edit", description="Edit an available Time Slot for a Kingshot Player")
    async def edit(
            self,
            interaction: discord.Interaction,
            player_id: int | None = None,
            event_id: int | None = None,
            tslot_id: int | None = None,
    ):
        await interaction.response.send_message("✅ time slot updated", ephemeral=True)

    # /timeslot remove: delete a record from the time_slots table.
    @app_commands.command(name="remove", description="Removes an available Time Slot for a Kingshot Player")
    async def remove(
            self,
            interaction: discord.Interaction,
            player_id: int | None = None,
            event_id: int | None = None,
            tslot_id: int | None = None,
    ):
        await interaction.response.send_message("✅ time slot deleted", ephemeral=True)

    # /timeslot list: lists all records in the time_slots table for the active player and event
    @app_commands.command(name="list", description="List available Time Slots for a Kingshot Player")
    async def list(
            self,
            interaction: discord.Interaction,
            player_id: int | None = None,
            event_id: int | None = None,
    ):
        await interaction.response.send_message("✅ time slots listed", ephemeral=True)

    # /timeslot show: shows a specific record in the time_slots table for the active player and event
    @app_commands.command(name="show", description="Show an available Time Slot for a Kingshot Player")
    async def show(
            self,
            interaction: discord.Interaction,
            player_id: int | None = None,
            event_id: int | None = None,
            tslot_id: int | None = None,
    ):
        # thinking ...
        # will use the active player and envent by default
        # you can specify a player_id and event_id to show a specific records
        await interaction.response.send_message("✅ time slot shown", ephemeral=True)
