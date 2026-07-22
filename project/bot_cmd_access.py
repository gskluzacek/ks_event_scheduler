import discord

from cmd_check import BotMode, cc_admin_bot_mode_at_least_admin


async def _reject_account_list_request(
        interaction: discord.Interaction,
) -> bool:
    curr_bot_mode = BotMode.curr_bot_mode()

    # do not allow command execution if the bot is down
    if curr_bot_mode == BotMode.DOWN:
        await interaction.response.send_message(
            "❌Sorry the bot is currently down. You cannot Register an account at this time.",
            ephemeral=True,
        )
        return True

    # if the bot is under maintenance, only allow Admins to register accounts
    if curr_bot_mode == BotMode.MAINTENANCE:
        is_authorized, authorization_error = cc_admin_bot_mode_at_least_admin.command_check(
            interaction.user.id
        )
        if not is_authorized:
            authorization_error = authorization_error[:-1] + f" when the bot is {curr_bot_mode.msg_desc}."
            await interaction.response.send_message(authorization_error, ephemeral=True)
            return True

    return False
