import os
import traceback
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "params.env"))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "main.env"))

from main_log_config import setup_logger

setup_logger(os.path.dirname(__file__))

from bot_setup.bot_poller import poll
from search_for_levels import *
from binance.get_pairs_async import *
from mutual_variables.dictionaries import starting_parameters


async def restarter():
    refresh_hours = int(os.getenv('UPDATE_TIME_HOURS', '2'))
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


async def main():
    asyncio.create_task(restarter())
    asyncio.create_task(restart_polling())

    while True:
        # Start trading tasks
        live_coins, coins_verb = await get_pairs('USDT')
        starting_parameters['coins'] = coins_verb
        starting_parameters['params'] = (f"Running with following parameters:\n\n"
                                         f"Update time: {int(os.getenv('UPDATE_TIME_HOURS', '2'))} hr\n"
                                         f"Ticksize filter: {float(os.getenv("TICKSIZE_FILTER", 0.05))}\n"
                                         f"ATR filter: {float(os.getenv("ATR_FILTER", 0.3))}\n"
                                         f"Pairs limit: {int(os.getenv("PAIRS_LIMIT", 60))}\n\n"
                                         f"Room upper/lower in DOM: {d_room}\n"
                                         f"Absolute dis: {abs_dis}\n\n"
                                         f"Size among others: x{size_mpl}\n"
                                         f"Size x Vol mpl (DOM): x{vol_mpl_depth}")
        print(f'Starting with {len(live_coins)} coins')
        await asyncio.sleep(30)
        print(f'Processing search')
        search_tasks = [asyncio.create_task(search(coin)) for coin in live_coins]
        await asyncio.gather(*search_tasks)
        print(f'Search loop ended')
        terminator.clear()


if __name__ == "__main__":
    asyncio.run(main())
