import logging

import discord
from discord import app_commands

import shared_state
from bot_cmd_access import _down_or_maint_check
from bot_autocomplete import event_id_autocomplete
from ks_db import get_event_by_id


logger = logging.getLogger("ksbot.evnt")


# TODO: add a event command to initalize a default set of events.

class Event(app_commands.Group):
    def __init__(self):
        super().__init__(name="event", description="Kingshot Player Event Tools")

    # /event activate
    @app_commands.command(name="activate", description="Set the Active Event to work with")
    @app_commands.autocomplete(event_id=event_id_autocomplete)
    async def activate(
            self,
            interaction: discord.Interaction,
            event_id: int | None = None
    ):
        if await _down_or_maint_check(interaction):
            return

        session = shared_state.get_session()

        # If event_id is None, then we want to show the currently active event for the user.
        if event_id is None:
            active_event_id = session.get(interaction.user.id, "active_event_id")
            if active_event_id is None:
                await interaction.response.send_message("✅ No active event has been set.", ephemeral=True)
                return
            event = await get_event_by_id(active_event_id)
            if not event:
                await interaction.response.send_message(f"❌Active Event set to an invalid ID {active_event_id}", ephemeral=True)
                return
            await interaction.response.send_message(f"✅ Active Event Name: {event['event_name']}, ID: {active_event_id}", ephemeral=True)

        # If event_id is provided, then we want to set that event as the active event for the user.
        else:
            event = await get_event_by_id(event_id)
            if not event:
                await interaction.response.send_message(f"❌ Event with ID {event_id} not found.", ephemeral=True)
                return
            session.set(interaction.user.id, "active_event_id", event_id)
            await interaction.response.send_message(f"✅ Activated Event Name: {event['event_name']}, ID: {event_id}", ephemeral=True)
