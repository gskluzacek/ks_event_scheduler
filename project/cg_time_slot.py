import logging

import discord
from discord import app_commands

import shared_state
from bot_autocomplete import (
    player_id_for_active_account_autocomplete,
    event_id_autocomplete,
    time_autocomplete,
    TIME_SLOTS_SET,
    time_slot_id_autocomplete,
)

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
    #   event_id              uses the active player and event stored in the player session state. These can be
    #   player_id             overridden by specifying the event_id and player_id in the command execution
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

    # for an admin to add a time slot for another account's player, they must first activate the account, then they can
    #   use the player_id auto complete to specify the account's player to add the time slot to.
    #   or alternative, instead of specify the player_id, the can active the player and then use the command to add
    #   the time slot for the active player.
    @app_commands.command(name="add", description="Add an available Time Slot for a Kingshot Player")
    @app_commands.autocomplete(player_id=player_id_for_active_account_autocomplete)
    @app_commands.autocomplete(event_id=event_id_autocomplete)
    @app_commands.choices(tslot_type=[
        app_commands.Choice(name="Preferred", value="preferred"),
        app_commands.Choice(name="Acceptable", value="acceptable"),
        app_commands.Choice(name="Avoid", value="avoid"),
    ])
    @app_commands.autocomplete(start_time=time_autocomplete)
    @app_commands.autocomplete(end_time=time_autocomplete)
    @app_commands.choices(priority=[
        app_commands.Choice(name="1 - High", value=1),
        app_commands.Choice(name="2", value=2),
        app_commands.Choice(name="3 - Medium", value=3),
        app_commands.Choice(name="4", value=4),
        app_commands.Choice(name="5 - Low", value=5),
    ])
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
        session = shared_state.get_session()
        player_id_final = player_id or session.get(interaction.user.id, "active_player_id")
        event_id_final = event_id or session.get(interaction.user.id, "active_event_id")

        if start_time not in TIME_SLOTS_SET or end_time not in TIME_SLOTS_SET:
            await interaction.response.send_message(
                f"❌ You provided start_time: {start_time} and end_time: {end_time}. Times must be in HH:MM 24-hour format, 15-minute increments (e.g. 09:15).",
                ephemeral=True,
            )
            return

        if end_time <= start_time:
            await interaction.response.send_message(
                f"❌ You provided start_time: {start_time} and end_time: {end_time}. The end_time must be later than the start_time.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ {tslot_type.capitalize()} time slot from {start_time} to {end_time} with a priority of {priority} added for: Player ID {player_id_final}, Event ID {event_id_final}", ephemeral=True
        )

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
    @app_commands.autocomplete(tslot_id=time_slot_id_autocomplete)
    @app_commands.autocomplete(event_id=event_id_autocomplete)
    @app_commands.autocomplete(player_id=player_id_for_active_account_autocomplete)
    async def show(
            self,
            interaction: discord.Interaction,
            tslot_id: int | None,
            player_id: int | None = None,
            event_id: int | None = None,
    ):
        # thinking ...
        # will use the active player and envent by default
        # you can specify a player_id and event_id to show a specific records
        await interaction.response.send_message(f"✅ time slot shown for Player ID: {player_id}, Event ID: {event_id} => Time Slot ID: {tslot_id}", ephemeral=True)
