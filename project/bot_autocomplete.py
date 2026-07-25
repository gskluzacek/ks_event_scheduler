import discord
from discord import app_commands

import shared_state
from ks_db import get_accounts_ac, get_players_ac, get_players_for_account_ac


async def account_id_autocomplete(
        _interaction: discord.Interaction,
        current: str,
) -> list[app_commands.Choice[int]]:
    accounts = await get_accounts_ac(current)
    return [
        app_commands.Choice[int](
            name=account_name,
            value=account_id,
        )
        for account_name, account_id in accounts
    ]


# Autocomplete function for account_id with "All Accounts" (`_wall`) option
async def account_id_autocomplete_wall(
        _interaction: discord.Interaction,
        current: str,
) -> list[app_commands.Choice[int]]:
    accounts = await get_accounts_ac(current)
    if not current:
        accounts = [("All Accounts", 0)] + accounts
    return [
        app_commands.Choice[int](
            name=account_name,
            value=account_id,
        )
        for account_name, account_id in accounts
    ]


async def player_id_autocomplete(
        _interaction: discord.Interaction,
        current: str,
) -> list[app_commands.Choice[int]]:
    players = await get_players_ac(current)
    return [
        app_commands.Choice[int](
            name=player_name,
            value=player_id,
        )
        for player_name, player_id in players
    ]


async def player_id_for_active_account_autocomplete(
        interaction: discord.Interaction,
        current: str,
) -> list[app_commands.Choice[int]]:
    session = shared_state.get_session()
    active_account_id = session.get(interaction.user.id, "active_account_id")
    active_account_id = active_account_id or session.get(interaction.user.id, "account_id")

    players = await get_players_for_account_ac(active_account_id, current)
    return [
        app_commands.Choice[int](
            name=player_name,
            value=player_id,
        )
        for player_name, player_id in players
    ]
