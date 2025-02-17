import os
from dotenv import load_dotenv
load_dotenv('main.env')

from main_log_config import setup_logger
setup_logger(os.path.dirname(__file__))

import asyncio
from new_version.search_for_levels import search
from new_version.get_pairs_async import get_pairs
from new_version.bot_setup.bot_sender import update_message_every_5_seconds


async def main():
    update_lock = asyncio.Lock()

    # Start the background update task
    tasks = [asyncio.create_task(update_message_every_5_seconds(update_lock))]

    # Start trading tasks
    excluded = ['BTCUSDT', 'ETHUSDT']
    live_coins = await get_pairs(excluded, 'USDT', 0.05, 0.3, 60)

    await asyncio.sleep(30)

    for coin in live_coins:
        tasks.append(asyncio.create_task(search(coin, update_lock,)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
