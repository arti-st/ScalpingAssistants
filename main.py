import os
from dotenv import load_dotenv

load_dotenv('main.env')
load_dotenv('params.env')

from main_log_config import setup_logger
setup_logger(os.path.dirname(__file__))

import asyncio
from new_version.search_for_levels import search, restarter, terminator, c_room, d_room, wiggle_room_perc, atr_dis, size_mpl, vol_mpl_chart, vol_mpl_depth, abs_dis
from new_version.get_pairs_async import get_pairs
from new_version.bot_setup.bot_service_sender import send_sevice_message
from new_version.bot_setup.bot_sender import update_message_every_5_seconds


async def main():

    update_lock = asyncio.Lock()

    while True:
        # Start the background update task
        tasks = [
            asyncio.create_task(update_message_every_5_seconds(update_lock)),
            asyncio.create_task(restarter()),
        ]

        # Start trading tasks
        excluded = ['BTCUSDT', 'ETHUSDT']
        live_coins = await get_pairs(excluded, 'USDT')

        msg = (f"Restarting with following parameters:\n\n"
               f"Room to the left: {c_room}\n"
               f"Room upper/lower in DOM: {d_room}\n"
               f"Wiggle room: {wiggle_room_perc*100}%\n\n"
               f"ATR distance mpl: x{atr_dis}\n"
               f"Absolute dis: {abs_dis}%\n\n"
               f"Size among others: x{size_mpl}\n"
               f"Size x Vol mpl (chart): x{vol_mpl_chart}\n"
               f"Size x Vol mpl (DOM): x{vol_mpl_depth}\n\n"
               f"Coins found: {len(live_coins)}")
        await send_sevice_message(msg)
        await asyncio.sleep(30)

        for coin in live_coins:
            tasks.append(asyncio.create_task(search(coin, update_lock,)))

        await asyncio.gather(*tasks)
        terminator.clear()

        await asyncio.sleep(60)



if __name__ == "__main__":
    asyncio.run(main())
