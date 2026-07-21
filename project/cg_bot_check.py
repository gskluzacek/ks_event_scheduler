import discord
from discord import app_commands


class BotCheck(app_commands.Group):
    def __init__(self):
        super().__init__(name="botcheck", description="Tools to check the bot")

    @app_commands.command(name="ping", description="Check if the bot is running and responding")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ pong", ephemeral=True)
