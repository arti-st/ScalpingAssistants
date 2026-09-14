import os
from dotenv import load_dotenv
from database_v2 import update_unlisted_coins, create_table, get_coins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "params.env"))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "keys.env"))

from PIL import PngImagePlugin

PngImagePlugin.DEBUG = 0

import matplotlib
import traceback
from datetime import datetime
from main_log_config import setup_logger
from bot_setup.bot_poller import poll
from main_logic.sizes_v2 import *
from binance.get_pairs_async import *
from mutual_variables.dictionaries import coin_updates, starting_parameters

matplotlib.set_loglevel("WARNING")
setup_logger(os.path.dirname(__file__))


async def restarter():
    refresh_hours = float(os.getenv('UPDATE_TIME_HOURS'))
    while True:
        await asyncio.sleep(3600 * refresh_hours)
        terminator.set()
        print(f'{datetime.now()} Terminator is SET')


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


async def healthcheck_pinger():
    healthcheck_url = os.getenv("HEALTHCHECK_URL")

    if not healthcheck_url:
        print("HEALTHCHECK_URL is not configured")
        return

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(healthcheck_url, timeout=30) as response:
                    if response.status == 200:
                        # print("Healthcheck ping sent successfully")
                        pass
                    else:
                        print(f"Healthcheck ping failed: HTTP {response.status}")

            except Exception as e:
                print(f"Healthcheck ping error: {e}")

            await asyncio.sleep(600)


def calculate_reload_time(coins_number: int) -> tuple[int, int]:
    depth_len = int(os.getenv('DEPTH_LEN'))

    if depth_len <= 100:
        depth_weight = 5
    elif depth_len <= 500:
        depth_weight = 25
    elif depth_len <= 1000:
        depth_weight = 50
    else:
        depth_weight = 250

    klines_weight = 2

    cycle_weight = (depth_weight + klines_weight) * coins_number

    reload_time = int((cycle_weight * 60 / 6000) * 1.5)  # 1.2 - збільшення часу очікування задля безпеки

    reload_time = 10 if reload_time < 10 else reload_time
    repeat_rate = max(int(60 / reload_time), 2)

    return reload_time, repeat_rate

async def main():
    asyncio.create_task(healthcheck_pinger())
    asyncio.create_task(restarter())
    asyncio.create_task(restart_polling())
    last_restart_hour = 0

    while True:
        # Clear ignoring set of coins
        if last_restart_hour != datetime.now().hour:
            last_restart_hour = datetime.now().hour

    #     print("Updating pairs")
    #     await get_pairs_async()
    #
    #     print("Pause for 30 seconds")
    #     await asyncio.sleep(30)
    #
    #     await asyncio.to_thread(update_unlisted_coins)
    #
        live_coins = get_coins()
        starting_parameters['upd_time'] = datetime.now()
        starting_parameters['coins'] = live_coins
        await asyncio.sleep(6000000)

    #     reload_time, repeat_rate = calculate_reload_time(len(live_coins))
    #
    #     print(f'Starting with {len(live_coins)} coins, reload time: {reload_time} and repeat: {repeat_rate}')
    #
    #     search_tasks = [
    #         asyncio.create_task(main_search(coin, params, reload_time, repeat_rate))
    #         for coin, params in live_coins.items()
    #     ]
    #
    #     await asyncio.gather(*search_tasks)
    #
    #     print(f'Search loop ended')
    #     coin_updates.clear()
    #     terminator.clear()


if __name__ == "__main__":
    create_table()
    asyncio.run(main())
