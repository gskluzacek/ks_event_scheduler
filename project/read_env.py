import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class BotConfig:
    TOKEN: str
    BOT_MODE: str
    TEST_GUILD_ID: int | None
    ADMIN_ZERO_ID: int
    DEFAULT_KINGDOM: int
    DEFAULT_ALLIANCE: str
    SELF_REGISTERED_ACCOUNT_ID: int
    DB_FILE: str

_config: BotConfig | None = None

def load_config() -> BotConfig:
    global _config
    load_dotenv()

    TOKEN = os.getenv("DISCORD_TOKEN")
    BOT_MODE = os.getenv("BOT_MODE", "debug").strip().lower()  # debug | production
    TEST_GUILD_ID: int | None = None

    if not TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN")

    if BOT_MODE not in {"debug", "production"}:
        raise RuntimeError("BOT_MODE must be either 'debug' or 'production'")

    if BOT_MODE == "debug":
        if not (temp_test_guild_id := os.getenv("TEST_GUILD_ID")):
            raise RuntimeError("Missing TEST_GUILD_ID for debug mode")
        try:
            TEST_GUILD_ID = int(temp_test_guild_id)
        except ValueError as e:
            raise RuntimeError("TEST_GUILD_ID is not set or invalid for debug mode") from e

    if not (temp_admin_zero_id := os.getenv("ADMIN_ZERO_ID")):
        raise RuntimeError("Missing ADMIN_ZERO_ID for server initialization ")
    try:
        ADMIN_ZERO_ID = int(temp_admin_zero_id)
    except ValueError as e:
        raise RuntimeError("ADMIN_ZERO_ID is not set or is not a valid Discord User ID") from e

    if not (temp_default_kingdom := os.getenv("DEFAULT_KINGDOM")):
        raise RuntimeError("Missing DEFAULT_KINGDOM")
    try:
        DEFAULT_KINGDOM = int(temp_default_kingdom)
    except ValueError as e:
        raise RuntimeError("DEFAULT_KINGDOM is not set or not a valid integer") from e

    if not (temp_default_alliance := os.getenv("DEFAULT_ALLIANCE")):
        raise RuntimeError("Missing DEFAULT_ALLIANCE")
    DEFAULT_ALLIANCE = temp_default_alliance

    DB_FILE = os.getenv("DB_FILE")
    if not DB_FILE:
        raise RuntimeError("Missing DB_FILE")

    # Sentinel meaning "the Discord user created their own account."
    SELF_REGISTERED_ACCOUNT_ID: int = 0

    config = BotConfig(
        TOKEN=TOKEN,
        BOT_MODE=BOT_MODE,
        TEST_GUILD_ID=TEST_GUILD_ID,
        ADMIN_ZERO_ID=ADMIN_ZERO_ID,
        DEFAULT_KINGDOM=DEFAULT_KINGDOM,
        DEFAULT_ALLIANCE=DEFAULT_ALLIANCE,
        SELF_REGISTERED_ACCOUNT_ID=SELF_REGISTERED_ACCOUNT_ID,
        DB_FILE=DB_FILE
    )
    _config = config
    return config

def get_config() -> BotConfig:
    if _config is None:
        raise RuntimeError("Configuration has not been loaded. Call load_config() first.")
    return _config
