import glob
import os
import time
from datetime import datetime
from threading import Thread, Event
import telebot
from modules import klines, order_book
import sys
from get_pairsV5_beta import get_pairs
from screenshoterV2 import screenshoter_send
from screenshoterV3_beta import screenshoter_send_beta
from bot_handling import start_bot
import threading
from dotenv import load_dotenv


PERSONAL_TELEGRAM_TOKEN = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(PERSONAL_TELEGRAM_TOKEN)
personal_id = int(os.getenv('PERSONAL_ID'))

# Event to signal threads to stop
stop_event = Event()

os.environ['BINANCE_SENT'] = ""
os.environ['FILTERED'] = ""
os.environ['IN_WORK'] = ""
os.environ['RELOAD_TIMESTAMP'] = ""
os.environ['BOT_STATE'] = "run"


def search(symbol, reload_time, time_log):
    levels_f = {}
    levels_s = {}

    levels_f_volumes = {}
    levels_s_volumes = {}

    static_f = []
    static_s = []

    c_room = 30  # кімната зліва
    d_room = 10  # вікно зверху і знизу стакану
    atr_dis = 1.5  # мультиплікатор відстані до сайзу в ATR
    size_mpl = 1.3 # мультиплікатор максимального сайзу
    vol_mpl = 5 # мультиплікатор відносності об'єму

    while not stop_event.is_set():
        if os.getenv('BOT_STATE') == "run":
            time1 = time.perf_counter()

            for market_type in ["f", "s"]:
                try:
                    depth = order_book(symbol, 500, market_type)
                except Exception as e:
                    personal_message = f"⛔️ Error in downloading depth for {symbol}({market_type}): {e}"
                    print(personal_message)
                    personal_bot.send_message(personal_id, personal_message)

                try:
                    the_klines = klines(symbol, "1m", 100, market_type)
                except Exception as e:
                    personal_message = f"⛔️ Error in downloading klines for {symbol}({market_type}): {e}"
                    print(personal_message)
                    personal_bot.send_message(personal_id, personal_message)

                market_type_verbose = 'FUTURES' if market_type == 'f' else 'SPOT'

                if depth is not None and the_klines is not None:

                    c_time, c_open, c_high, c_low, c_close, avg_vol = the_klines[0], the_klines[1], the_klines[2], the_klines[3], the_klines[4], the_klines[5]
                    depth = depth[1]  # [ціна, об'єм]

                    avg_atr_per = [(c_high[-c] - c_low[-c]) / (c_close[-c] / 100) for c in range(30)]
                    avg_atr_per = float('{:.2f}'.format(sum(avg_atr_per) / len(avg_atr_per)))

                    if len(c_high) == len(c_low):

                        # пошук екстремуму, а потім сайзу на ньому
                        for i in range(2, len(c_low) - c_room):
                            if c_high[-i] >= max(c_high[-1: -i - c_room: -1]):
                                for item in depth:
                                    # щільність знаходиться між 9-ю спочатку, 9-ю з кінця та ціна щільності == хаю
                                    if d_room - 1 < depth.index(item) < len(depth) - d_room and c_high[-i] == item[0]:
                                        # сайзи між ціною щільності -10 та ціною щільності
                                        lower_sizes = [depth[k][1] for k in range(depth.index(item) - d_room, depth.index(item))]
                                        # сайзи між ціною щільності +10 та ціною щільності
                                        higher_sizes = [depth[k][1] for k in range(depth.index(item) + 1, depth.index(item) + d_room + 1)]
                                        # дистанція до ціни
                                        distance_per = abs(c_high[-i] - c_close[-1]) / (c_close[-1] / 100)
                                        distance_per = float('{:.2f}'.format(distance_per))

                                        if all(item[1] >= dom * size_mpl for dom in lower_sizes+higher_sizes) and distance_per <= atr_dis * avg_atr_per and item[1] >= avg_vol * vol_mpl:

                                            levels_dict = levels_f if market_type == "f" else levels_s
                                            static_dict = static_f if market_type == "f" else static_s

                                            direction = '🔼' if item[0] >= c_close[-1] else '🔽'

                                            if c_high[-i] not in levels_dict.keys():
                                                levels_dict.update({c_high[-i]: c_time[-i]})

                                            else:
                                                if levels_dict.get(c_high[-i]) == c_time[-i]:

                                                    message_for_screen = f"""
🐘 Size on extremum!
{market_type_verbose} #{symbol}

current price: {c_close[-1]}
average vol: {round(avg_vol/1000, 1)}K coins

size price: {item[0]} {direction} {round(distance_per, 2)}% from current price
size vol: {round(item[1]/1000, 1)}K coins

<b>size/avg.vol: {round(item[1] / avg_vol, 1)}</b>

<i>Повідомлення не є торговою рекомендацією.</i>
@UA_sizes_bot
"""
                                                    screenshoter_send(symbol, market_type, item[0], message_for_screen)
                                                    if c_high[-i] not in static_dict:
                                                        static_dict.append(c_high[-i])
                                        break

                            if c_low[-i] <= min(c_low[-1: -i - c_room: -1]):
                                for item in depth:
                                    # щільність знаходиться між 9-ю спочатку, 9-ю з кінця та ціна щільності == хаю
                                    if d_room - 1 < depth.index(item) < len(depth) - d_room and c_low[-i] == item[0]:
                                        # сайзи між ціною щільності -10 та ціною щільності
                                        lower_sizes = [depth[k][1] for k in range(depth.index(item) - d_room, depth.index(item))]
                                        # сайзи між ціною щільності +10 та ціною щільності
                                        higher_sizes = [depth[k][1] for k in range(depth.index(item) + 1, depth.index(item) + d_room + 1)]
                                        # дистанція до ціни
                                        distance_per = abs(c_low[-i] - c_close[-1]) / (c_close[-1] / 100)
                                        distance_per = float('{:.2f}'.format(distance_per))

                                        if all(item[1] >= dom * size_mpl for dom in lower_sizes+higher_sizes) and distance_per <= atr_dis * avg_atr_per and item[1] >= avg_vol * vol_mpl:

                                            levels_dict = levels_f if market_type == "f" else levels_s
                                            static_dict = static_f if market_type == "f" else static_s

                                            direction = '🔼' if item[0] >= c_close[-1] else '🔽'

                                            if c_low[-i] not in levels_dict.keys():
                                                levels_dict.update({c_low[-i]: c_time[-i]})

                                            else:
                                                if levels_dict.get(c_low[-i]) == c_time[-i]:
                                                    message_for_screen = f"""
🐘 Size on extremum!
{market_type_verbose} #{symbol}

current price: {c_close[-1]}
average vol: {round(avg_vol/1000, 1)}K coins

size price: {item[0]} {direction} {round(distance_per, 2)}% from current price
size vol: {round(item[1]/1000, 1)}K coins

<b>size/avg.vol: {round(item[1] / avg_vol, 1)}</b>

<i>Повідомлення не є торговою рекомендацією.</i>
@UA_sizes_bot
"""
                                                    screenshoter_send(symbol, market_type, item[0], message_for_screen)
                                                    if c_low[-i] not in static_dict:
                                                        static_dict.append(c_low[-i])
                                        break

                        # пошук виключно сайзу
                        for i in range(110, len(depth) - 110):
                            current_vol = depth[i][1]
                            current_price = depth[i][0]
                            previous_b_values = [depth[j][1] for j in range(i - 20, i)]  # values 20 before
                            following_b_values = [depth[j][1] for j in range(i + 1, i + 21)]  # values 20 after

                            distance_to = abs(current_price - c_close[-1]) / (c_close[-1] / 100)
                            static_dict = static_f if market_type == "f" else static_s

                            if all(current_vol >= b * size_mpl for b in previous_b_values + following_b_values) and distance_to <= atr_dis * avg_atr_per and current_vol >= avg_vol * vol_mpl and current_price not in static_dict:

                                levels_volumes = levels_f_volumes if market_type == 'f' else levels_s_volumes

                                if current_price not in levels_volumes.keys():
                                    levels_volumes.update({current_price: current_vol})
                                else:
                                    direction = '🔼' if current_price >= c_close[-1] else '🔽'
                                    personal_message = f"""
🐋 Size only!
{market_type_verbose} #{symbol}

current price: {c_close[-1]}
average vol: {round(avg_vol / 1000, 1)}K coins

size price: {current_price} {direction} {round(distance_to, 2)}% from current price
size vol: {round(current_vol / 1000, 1)}K coins

<b>size/avg.vol: {round(current_vol / avg_vol, 1)}</b>

<i>Повідомлення не є торговою рекомендацією.</i>
@UA_sizes_bot
"""
                                    screenshoter_send_beta(symbol, market_type, current_price, personal_message)
                                    levels_volumes.pop(current_price)

                # elif market_type == "f" and (depth is None or the_klines is None):
                #     personal_message = f"⛔️ Main file. Error in {symbol} ({market_type}) data!"
                #     print(personal_message)
                #     personal_bot.send_message(personal_id, personal_message)

            time2 = time.perf_counter()
            time3 = time2 - time1
            time3 = float('{:.2f}'.format(time3))

            if time_log > 0:
                print(f"{datetime.now().strftime('%H:%M:%S')} {symbol}: {time3} + {float('{:.2f}'.format(reload_time))} s, levels: {len(levels_f)}/{len(levels_s)}")
                sys.stdout.flush()

            time.sleep(reload_time)


def clean_old_files(directory, prefix, extension='.png'):
    pattern = os.path.join(directory, f"{prefix}*{extension}")
    files_to_remove = glob.glob(pattern)
    for file_path in files_to_remove:
        try:
            os.remove(file_path)
        except Exception as e:
            personal_message = f"⚙️ Failed to remove file {file_path}: {e}"
            personal_bot.send_message(chat_id=personal_id, text=personal_message)
            print(personal_message)

    personal_message = (f"⚙️ {len(files_to_remove)} images ({prefix}) successfully removed...\n"
                        f"Alive threads: {len([thread.name for thread in threading.enumerate() if thread.is_alive()])}")
    personal_bot.send_message(chat_id=personal_id, text=personal_message)
    print(personal_message)


# ---------- NEW PROCESSOR ------------ #
def monitor_time_and_control_threads():
    global stop_event
    while True:
        current_minute = int(datetime.now().strftime('%M'))
        if current_minute != 59:
            personal_message = (f"⚙️ Current time is {datetime.now().strftime('%H:%M:%S')}. We starting...\n"
                                f"Alive threads: {len([thread.name for thread in threading.enumerate() if thread.is_alive()])}")

            personal_bot.send_message(chat_id=personal_id, text=personal_message)
            print(personal_message)

            stop_event.clear()

            clean_old_files('.', prefix='FT_')
            clean_old_files('.', prefix='FTbeta_')

            reload_time = 58
            time_log = 0

            pairs = get_pairs()
            personal_message = (f"⚙️ Sleep 30 seconds and starting calculation threads...\n"
                                f"Alive threads: {len([thread.name for thread in threading.enumerate() if thread.is_alive()])}")
            personal_bot.send_message(chat_id=personal_id, text=personal_message)
            print(personal_message)
            time.sleep(30)

            the_threads = []
            for pair in pairs:
                thread = Thread(target=search, args=(pair, reload_time, time_log,))
                thread.start()
                the_threads.append(thread)

            personal_message = (f"⚙️ Threads is running...\n"
                                f"Alive threads: {len([thread.name for thread in threading.enumerate() if thread.is_alive()])}")
            personal_bot.send_message(chat_id=personal_id, text=personal_message)
            print(personal_message)

            # Monitor until minutes reach 58
            while not int(datetime.now().strftime('%M')) == 59:
                time.sleep(1)

            # Signal threads to stop
            personal_message = (f"⚙️ Current time is {datetime.now().strftime('%H:%M:%S')}. Signal to stop threads sent...\n"
                                f"Alive threads: {len([thread.name for thread in threading.enumerate() if thread.is_alive()])}")
            personal_bot.send_message(chat_id=personal_id, text=personal_message)
            print(personal_message)
            stop_event.set()

            # Wait for threads to finish
            for thread in the_threads:
                thread.join()

            personal_message = ("⚙️ All thread have been stopped. Waiting to restart...\n"
                                f"Alive threads: {len([thread.name for thread in threading.enumerate() if thread.is_alive()])}")
            personal_bot.send_message(chat_id=personal_id, text=personal_message)
            print(personal_message)

            time.sleep(60)

        time.sleep(1)


if __name__ == '__main__':
    load_dotenv()

    bot_thread = Thread(target=start_bot)
    bot_thread.start()

    monitor_time_and_control_threads()
