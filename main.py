import os
import traceback
from dotenv import load_dotenv

from mutual_variables.dictionaries import starting_parameters

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "params.env"))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "main.env"))

from main_log_config import setup_logger

setup_logger(os.path.dirname(__file__))

from bot_setup.bot_poller import poll
from search_for_levels import *
from binance.get_pairs_async import get_pairs


async def restarter():
    refresh_hours = int(os.getenv('UPDATE_TIME_HOURS', '2'))
    while True:
        if datetime.now().hour % refresh_hours == 0 and datetime.now().minute == 0:
            terminator.set()
            break
        else:
            await asyncio.sleep(60)


async def restart_polling():
    while True:
        try:
            await poll()
        except Exception as e:
            traceback.format_exc()
            print(e)
            print(traceback)
        finally:
            await asyncio.sleep(5)


async def main():
    update_lock = asyncio.Lock()

    while True:
        # Start the background update task
        tasks = [
            asyncio.create_task(restarter()),
            asyncio.create_task(restart_polling())
        ]

        # Start trading tasks
        excluded = ['BTCUSDT', 'ETHUSDT']
        live_coins, coins_verb = await get_pairs(excluded, 'USDT')
        starting_parameters['coins'] = coins_verb
        starting_parameters['params'] = (f"Running with following parameters:\n\n"
               f"Room to the left: {c_room}\n"
               f"Room upper/lower in DOM: {d_room}\n"
               f"Wiggle room: {wiggle_room_perc * 100}%\n\n"
               f"ATR distance mpl: x{atr_dis}\n"
               f"Absolute dis: {abs_dis}%\n\n"
               f"Size among others: x{size_mpl}\n"
               f"Size x Vol mpl (chart): x{vol_mpl_chart}\n"
               f"Size x Vol mpl (DOM): x{vol_mpl_depth}")


        await asyncio.sleep(30)

        for coin in live_coins:
            tasks.append(asyncio.create_task(search(coin, update_lock,)))

        await asyncio.gather(*tasks)
        terminator.clear()

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
