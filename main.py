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


# async def html_updater():
#     while True:
#         if datetime.now().second > 20:
#             await update_html()
#             await asyncio.sleep(40)
#         await asyncio.sleep(1)


async def main():
    while True:
        # Start the background update task
        tasks = [
            asyncio.create_task(restarter()),
            asyncio.create_task(restart_polling()),
            # asyncio.create_task(html_updater())
        ]

        # Start trading tasks
        live_coins, coins_verb = await get_pairs('USDT')
        starting_parameters['coins'] = coins_verb
        starting_parameters['params'] = (f"Running with following parameters:\n\n"
                                         f"Update time: {int(os.getenv('UPDATE_TIME_HOURS', '2'))} hr\n"
                                         f"Ticksize filter: {float(os.getenv("TICKSIZE_FILTER", 0.05))}\n"
                                         f"ATR filter: {float(os.getenv("ATR_FILTER", 0.3))}\n"
                                         f"Pairs limit: {int(os.getenv("PAIRS_LIMIT", 60))}\n\n"
                                         f"Room to the left: {c_room}\n"
                                         f"Room upper/lower in DOM: {d_room}\n"
                                         f"Wiggle room: {wiggle_room_perc * 100}\n\n"
                                         f"ATR distance mpl: x{atr_dis}\n"
                                         f"Absolute dis: {abs_dis}\n\n"
                                         f"Size among others: x{size_mpl}\n"
                                         f"Size x Vol mpl (chart): x{vol_mpl_chart}\n"
                                         f"Size x Vol mpl (DOM): x{vol_mpl_depth}")
        print(f'Starting with {len(live_coins)} coins')
        await asyncio.sleep(30)
        print(f'Processing search')
        for coin in live_coins:
            tasks.append(asyncio.create_task(search(coin)))

        await asyncio.gather(*tasks)
        terminator.clear()

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
