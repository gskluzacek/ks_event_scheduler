import discord
from discord import app_commands

import shared_state
from cmd_check import BotMode, cc_admin_bot_mode_at_least_admin


BOT_MODE_STATE_KEY = "bot_mode"
VALID_BOT_MODES = (BotMode.NORMAL, BotMode.MAINTENANCE, BotMode.DOWN)
VALID_BOT_MODES_STR = ", ".join([m.value for m in VALID_BOT_MODES])


async def bot_mode_autocomplete(interaction: discord.Interaction, current: str):
    # Return a list of valid bot modes that start with the current input
    return [
        app_commands.Choice(name=mode.value, value=mode.value)
        for mode in VALID_BOT_MODES
        if mode.value.startswith(current.lower())
    ]


class Admin(app_commands.Group):
    def __init__(self):
        super().__init__(name="admin", description="Administration Tools")

    # /admin bot_mode
    @app_commands.command(name="set_bot_mode", description="Set the bot mode")
    @app_commands.autocomplete(requested_mode=bot_mode_autocomplete)
    async def set_bot_mode(
            self,
            interaction: discord.Interaction,
            requested_mode: str
    ):
        app_state = shared_state.get_app_state()

        is_authorized, authorization_error = cc_admin_bot_mode_at_least_admin.command_check(interaction.user.id)
        if not is_authorized:
            await interaction.response.send_message(authorization_error, ephemeral=True)
            return

        new_mode = BotMode.from_str(requested_mode)
        if new_mode not in VALID_BOT_MODES:
            await interaction.response.send_message(
                f"❌ Invalid bot mode: {requested_mode}. Valid modes are: {VALID_BOT_MODES_STR}", ephemeral=True
            )
            return

        current_mode = BotMode.from_str(app_state.get(BOT_MODE_STATE_KEY))
        if current_mode == BotMode.UNKNOWN:
            await interaction.response.send_message(
                f"❌ Invalid current bot mode: {current_mode.value}.", ephemeral=True
            )
            return

        if current_mode == new_mode:
            await interaction.response.send_message(
                f"❌ Bot mode is already set to {new_mode.value}.", ephemeral=True
            )
            return

        app_state.set("bot_mode", new_mode.value)
        await interaction.response.send_message(
            f"✅ Bot mode changed to: {new_mode.msg_desc}", ephemeral=True
        )

    @app_commands.command(name="get_bot_mode", description="Set the bot mode")
    async def get_bot_mode(
            self,
            interaction: discord.Interaction,
    ):
        app_state = shared_state.get_app_state()

        is_authorized, authorization_error = cc_admin_bot_mode_at_least_admin.command_check(interaction.user.id)
        if not is_authorized:
            await interaction.response.send_message(authorization_error, ephemeral=True)
            return

        current_mode = BotMode.from_str(app_state.get(BOT_MODE_STATE_KEY))
        await interaction.response.send_message(
            f"✅ Current bot mode is: {current_mode.msg_desc}", ephemeral=True
        )
