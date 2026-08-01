import discord
from discord import app_commands


# TODO: add a event command to initalize a default set of events.

class Event(app_commands.Group):
    def __init__(self):
        super().__init__(name="event", description="Kingshot Player Event Tools")

    # TODO: add /event activate to set the active event id for adding time slots.
    #       Currently setting the active event id to 1 in the account create command.

    async def activate(
            self,
            interaction: discord.Interaction,
            event_id: int
    ):
        ...
