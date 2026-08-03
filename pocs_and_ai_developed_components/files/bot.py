"""
bot.py  —  minimal discord.py bot showing SessionManager usage
--------------------------------------------------------------
Slash commands:
  /setdefault <key> <value>  — store a default setting for the calling user
  /getdefault <key>          — retrieve a stored setting
  /mysession                 — dump the caller's full session
  /clearsession              — delete the caller's session
"""

import os
import discord
from discord import app_commands
from redis_session import SessionManager

MY_GUILD = discord.Object(id=os.environ["TEST_GUILD_ID"])  # replace with your server's ID


# ── Bot setup ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# TTL: 2 hours of inactivity before a session is evicted from Redis.
# REDIS_HOST defaults to 'localhost' locally, 'redis' in Docker (via env var).
session = SessionManager(ttl_seconds=7200)


# ── Events ───────────────────────────────────────────────────────────────────

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")


# ── Commands ─────────────────────────────────────────────────────────────────

@tree.command(name="setdefault", description="Save a default value for a setting")
@app_commands.describe(key="Setting name", value="Value to store")
async def setdefault(interaction: discord.Interaction, key: str, value: str):
    session.set(interaction.user.id, key, value)
    await interaction.response.send_message(
        f"✅ Saved `{key}` = `{value}`", ephemeral=True
    )


@tree.command(name="getdefault", description="Retrieve a stored default value")
@app_commands.describe(key="Setting name")
async def getdefault(interaction: discord.Interaction, key: str):
    value = session.get(interaction.user.id, key)
    if value is None:
        await interaction.response.send_message(
            f"No value stored for `{key}`.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"`{key}` = `{value}`", ephemeral=True
        )


@tree.command(name="mysession", description="Show all your stored session data")
async def mysession(interaction: discord.Interaction):
    data = session.get_all(interaction.user.id)
    if not data:
        await interaction.response.send_message("No session data stored.", ephemeral=True)
        return
    lines = "\n".join(f"  {k}: {v}" for k, v in data.items())
    ttl = session.ttl_remaining(interaction.user.id)
    await interaction.response.send_message(
        f"**Your session** (expires in {ttl}s):\n```\n{lines}\n```", ephemeral=True
    )


@tree.command(name="clearsession", description="Delete all your session data")
async def clearsession(interaction: discord.Interaction):
    session.delete_session(interaction.user.id)
    await interaction.response.send_message("🗑️ Session cleared.", ephemeral=True)


# ── Entry point ───────────────────────────────────────────────────────────────
@client.event
async def on_ready():
    tree.copy_global_to(guild=MY_GUILD)
    await tree.sync(guild=MY_GUILD)
    print(f"Logged in as {client.user}")

# @client.event
# async def on_ready():
#     tree.clear_commands(guild=None)       # clear global commands
#     await tree.sync(guild=None)           # push the empty set to Discord
#     tree.copy_global_to(guild=MY_GUILD)
#     await tree.sync(guild=MY_GUILD)
#     print(f"Logged in as {client.user}")

client.run(os.environ["DISCORD_TOKEN"])
