import logging

import read_env
import shared_state
from ks_event_scheduler_bot import KsEventSchedulerBot

from cg_admin import Admin
from cg_bot_check import BotCheck
from cg_account import Account
from cg_player import Player


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s | %(name)s | [%(filename)s:%(lineno)d]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("ksbot")
logger.setLevel(logging.DEBUG)


def main():
    config = read_env.load_config()
    shared_state.init_shared_state()
    logger.info(f"Config and Shared State loaded for mode: {config.BOT_MODE}")

    ks_event_scheduler_bot = KsEventSchedulerBot()
    ks_event_scheduler_bot.tree.add_command(BotCheck())
    ks_event_scheduler_bot.tree.add_command(Admin())
    ks_event_scheduler_bot.tree.add_command(Account())
    ks_event_scheduler_bot.tree.add_command(Player())
    ks_event_scheduler_bot.run(config.TOKEN)


if __name__ == "__main__":
    main()
