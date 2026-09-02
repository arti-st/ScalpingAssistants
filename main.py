import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "params.env"))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "keys.env"))

from PIL import PngImagePlugin

PngImagePlugin.DEBUG = 0

import matplotlib
import traceback
from main_log_config import setup_logger
from bot_setup.bot_poller import poll
from main_logic.sizes import *
from binance.get_pairs_async import *
from mutual_variables.dictionaries import coin_updates, starting_parameters, coins_to_ignore

matplotlib.set_loglevel("WARNING")
setup_logger(os.path.dirname(__file__))


async def restarter():
    refresh_hours = float(os.getenv('UPDATE_TIME_HOURS', '1.0'))
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
                        print("Healthcheck ping sent successfully")
                    else:
                        print(f"Healthcheck ping failed: HTTP {response.status}")

            except Exception as e:
                print(f"Healthcheck ping error: {e}")

            await asyncio.sleep(600)


async def main():
    # cleanup_old_records(20)

    asyncio.create_task(healthcheck_pinger())
    asyncio.create_task(restarter())
    asyncio.create_task(restart_polling())
    last_restart_hour = 0

    while True:
        # Clear ignoring set of coins
        if last_restart_hour != datetime.now().hour:
            coins_to_ignore.clear()
            last_restart_hour = datetime.now().hour

        # Start trading tasks
        print(f"Coins to ignore: {coins_to_ignore}")
        live_coins, coins_verb = await get_pairs('USDT', list(coins_to_ignore))
        starting_parameters['coins'] = coins_verb
        starting_parameters['upd_time'] = datetime.now().replace(microsecond=0)
        starting_parameters['params'] = (f"Running with following parameters:\n\n"

                                         f"Filter's timeframe: {os.getenv("TF")}m\n"
                                         f"Update time: {os.getenv('UPDATE_TIME_HOURS')} hr\n"
                                         f"Ticksize filter: {os.getenv("TICKSIZE_FILTER")}\n"
                                         f"ATR filter: {os.getenv("ATR_FILTER")}\n"
                                         f"Pairs limit: {os.getenv("PAIRS_LIMIT")}\n"
                                         f"Spot verified: {os.getenv("SPOT_VERIFIED")}\n\n"

                                         f"Sizes block:\n"
                                         f"Depth length: {os.getenv("DEPTH_LEN")}\n"
                                         f"Depth (min) length: {os.getenv("MIN_DEPTH_LEN")}\n"
                                         f"Klines length: {os.getenv("KLINES_LEN")}\n"
                                         f"Klines (min) length: {os.getenv("MIN_KLINES_LEN")}\n"
                                         f"Room to the left: {os.getenv("C_ROOM")}\n"
                                         f"Room upper/lower in DOM: {os.getenv("D_ROOM")}\n"
                                         f"Wiggle room: {os.getenv("WIGGLE_ROOM_PERC")}%\n"
                                         f"Absolute dis: {os.getenv("ABS_DIS")}\n\n"
                                         f"Size among others: x{os.getenv("SIZE_MPL")}\n"
                                         f"Size x Vol mpl (DOM): x{os.getenv("VOL_MPL_DEPTH")}\n"
                                         f"Times to repeat: {os.getenv("REPEAT_COUNTER")}\n\n"

                                         f"Divergences block:\n"
                                         f"Look for extermum in last: {os.getenv("EXTREMUM_WINDOW")} candles\n"
                                         f"Extr. RttL: {os.getenv("EXTREMUM_ROOM_LEFT")}\n"
                                         f"Vertical price range filter: {os.getenv("PRICE_RANGE_WINDOW")}\n"
                                         f"Part of a vertical range: 1/{os.getenv("PRICE_RANGE_PART")}\n"
                                         f"Delta RttL: {os.getenv("DELTA_WINDOW")}")

        print(f'Starting with {len(live_coins)} coins')
        await asyncio.sleep(30)
        print(f'Processing search')
        search_tasks = [asyncio.create_task(sizes_search(coin)) for coin in live_coins]
        await asyncio.gather(*search_tasks)
        print(f'Search loop ended')

        coin_updates.clear()
        terminator.clear()


if __name__ == "__main__":
    asyncio.run(main())
