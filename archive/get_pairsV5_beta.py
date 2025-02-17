import os
import requests
import time
from datetime import datetime
from threading import Thread
import telebot
import threading
from dotenv import load_dotenv
load_dotenv()

PERSONAL_TELEGRAM_TOKEN = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(PERSONAL_TELEGRAM_TOKEN)
personal_id = int(os.getenv('PERSONAL_ID'))

excluded = ['OMGUSDT', 'BTCUSDT', 'ETHUSDT', 'VANRYUSDT']

def calculate_pairs(pairs_dict, shared_results):
    for symbol, ts in pairs_dict.items():
        request_limit_length = 99
        frame = '1m'
        futures_klines = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={frame}&limit={request_limit_length}'
        try:
            klines = requests.get(futures_klines)
        except Exception as e:
            personal_message = f"⛔️ Error in downloading klines (get_pairs) for {symbol}: {e}"
            print(personal_message)
            personal_bot.send_message(personal_id, personal_message)

        if klines.status_code == 200:
            response_length = len(klines.json()) if klines.json() is not None else 0
            if response_length == request_limit_length:
                binance_candle_data = klines.json()
                high = [float(i[2]) for i in binance_candle_data]
                low = [float(i[3]) for i in binance_candle_data]
                close = [float(i[4]) for i in binance_candle_data]

                x_atr_per = [(high[-c] - low[-c]) / (close[-c] / 100) for c in range(request_limit_length)]
                x_atr_per = sum(x_atr_per) / len(x_atr_per)
                ts_percent = float(ts) / (close[-1] / 100)

                result = [symbol, ts_percent, x_atr_per]
                shared_results.append(result)

        time.sleep(0.5)  # Throttle API requests to avoid overloading the system


def split_dict(input_dict, num_parts):
    avg = len(input_dict) // num_parts
    remainder = len(input_dict) % num_parts
    result = []
    start = 0

    for i in range(num_parts):
        end = start + avg + (1 if i < remainder else 0)
        result.append({k: input_dict[k] for k in list(input_dict)[start:end]})
        start = end

    return result


def get_pairs():
    ts_dict = {}
    futures_exchange_info_url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    response = requests.get(futures_exchange_info_url)
    response_data = response.json().get("symbols")

    for data in response_data:
        symbol = data['symbol']
        tick_size = data['filters'][0]['tickSize']
        if data['quoteAsset'] == "USDT" and symbol not in excluded:
            ts_dict[symbol] = tick_size

    list_of_dicts = split_dict(ts_dict, 5)  # Split ts dict into 10 parts

    shared_results = []
    pairs_threads = []

    for dict_of_pairs in list_of_dicts:
        pair_thread = Thread(target=calculate_pairs, args=(dict_of_pairs, shared_results))
        pairs_threads.append(pair_thread)
        pair_thread.start()

    personal_message = f"⚙️ Getting pairs...\nAlive threads: {len([thread.name for thread in threading.enumerate() if thread.is_alive()])}"
    personal_bot.send_message(chat_id=personal_id, text=personal_message)
    print(personal_message)

    for pair_thread in pairs_threads:
        pair_thread.join()  # Ensure all threads have finished

    sorted_res = [res for res in shared_results if res[1] <= 0.05 and res[2] >= 0.2]
    sorted_res = sorted(sorted_res, key=lambda x: x[2], reverse=True)

    pairs_limit = 30
    result = [res[0] for res in sorted_res[:pairs_limit]]
    pairs_to_message = "".join(f"{i[0]} - {round(i[2], 2)}%\n" for i in sorted_res[:pairs_limit])

    os.environ['BINANCE_SENT'] = str(len(ts_dict))
    os.environ['FILTERED'] = str(len(sorted_res))
    os.environ['IN_WORK'] = str(len(result))
    os.environ['RELOAD_TIMESTAMP'] = str(datetime.now().strftime('%H:%M:%S'))

    msg = f"""
⚙️ Pairs got: {len(result)}/{len(sorted_res)}/{len(ts_dict)}.

{pairs_to_message}
"""
    personal_bot.send_message(chat_id=personal_id, text=msg, parse_mode="HTML")

    return result

#
# if __name__ == '__main__':
#     get_pairs()
