import os
from dotenv import load_dotenv

load_dotenv('main.env')

from new_version.main_log_config import setup_logger
setup_logger(os.path.dirname(__file__))

import asyncio
from new_version.search_for_levels import search
from new_version.get_pairs_async import get_pairs
from new_version.bot_setup.bot_sender import update_message_every_5_seconds


async def main():

    # Start the background update task
    update_task = asyncio.create_task(update_message_every_5_seconds())
    await asyncio.sleep(30)

    # Start trading tasks
    excluded = ['BTCUSDT', 'ETHUSDT']
    live_coins = await get_pairs(excluded, 'USDT', 0.05, 0.3, 60)
    tasks = [asyncio.create_task(search(coin)) for coin in live_coins]

    await asyncio.gather(*tasks, update_task)


if __name__ == "__main__":
    asyncio.run(main())
