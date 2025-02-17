import telebot
import matplotlib
import os
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
import chat_ids
from dotenv import load_dotenv
load_dotenv()

# --- TELEGRAM ---
PERSONAL_TELEGRAM_TOKEN = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(PERSONAL_TELEGRAM_TOKEN)
personal_id = int(os.getenv('PERSONAL_ID'))

PUBLIC_TELEGRAM_TOKEN = os.getenv('PUBLIC_TELEGRAM_TOKEN')
bot_all = telebot.TeleBot(PUBLIC_TELEGRAM_TOKEN)

existed_chat_ids = set(chat_ids.get_existed_chat_ids())


def screenshoter_send_beta(symbol, market_type, level, message):
    r_length = 180

    futures_klines = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m&limit={r_length}'
    spot_klines = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit={r_length}'

    try:
        klines = requests.get(futures_klines) if market_type == 'f' else requests.get(spot_klines)
    except Exception as e:
        msg = f"⛔️ Failed download screenshot data for {symbol} ({market_type}): {e}"
        personal_bot.send_message(chat_id=personal_id, text=msg)
        print(msg)
        return None

    cOpen = []
    cHigh = []
    cLow = []
    cClose = []

    if klines.status_code == 200:
        response_length = len(klines.json()) if klines.json() is not None else 0
        if response_length == r_length:
            binance_candle_data = klines.json()
            cOpen = [float(entry[1]) for entry in binance_candle_data]
            cHigh = [float(entry[2]) for entry in binance_candle_data]
            cLow = [float(entry[3]) for entry in binance_candle_data]
            cClose = [float(entry[4]) for entry in binance_candle_data]
        else:
            msg = (f"⛔️ Empty screenshot data for {symbol} ({market_type}), status code {klines.status_code}\n"
                   f"{klines}")
            personal_bot.send_message(chat_id=personal_id, text=msg)
            print(msg)
            return None
    else:
        msg = (f"⛔️ No screenshot data for {symbol} ({market_type}), status code {klines.status_code}\n"
               f"{klines}")
        personal_bot.send_message(chat_id=personal_id, text=msg)
        print(msg)
        return None

    price_max = max(cOpen + cHigh + cLow + cClose) * 1.01
    price_min = min(cOpen + cHigh + cLow + cClose) * 0.99

    if len(cOpen) == len(cHigh) == len(cLow) == len(cClose) == r_length and 0 not in cOpen + cHigh + cLow + cClose and price_min <= level <= price_max:

        fig, ax = plt.subplots(figsize=(10, 4))
        fig.set_facecolor("#F0F0F0")
        bg_color = "#FFFFFF"
        ax.set_facecolor(bg_color)

        background_text = f'FUTURES' if market_type == "f" else f'SPOT'
        ax.text(0.5, 0.5, background_text, fontsize=100, color='grey', ha='center', va='center', alpha=0.2, transform=ax.transAxes)

        for i in range(len(cClose)):
            body_up = cClose[i] - cOpen[i] if cClose[i] != cOpen[i] else cOpen[i] * 0.0001
            body_dn = cOpen[i] - cClose[i] if cClose[i] != cOpen[i] else cClose[i] * 0.0001

            if cClose[i] >= cOpen[i]:
                # Up candles
                plt.bar(x=i, height=body_up, width=0.9, bottom=cOpen[i], color='#528c00')
                plt.bar(x=i, height=cHigh[i] - cClose[i], width=0.09, bottom=cClose[i], color='#528c00')
                plt.bar(x=i, height=cOpen[i] - cLow[i], width=0.09, bottom=cLow[i], color='#528c00')
            else:
                # Down candles
                plt.bar(x=i, height=body_dn, width=0.9, bottom=cClose[i], color='#842800')
                plt.bar(x=i, height=cHigh[i] - cOpen[i], width=0.09, bottom=cOpen[i], color='#842800')
                plt.bar(x=i, height=cClose[i] - cLow[i], width=0.09, bottom=cLow[i], color='#842800')

            plt.grid(color='grey', linestyle='-', linewidth=0.1)

        ax.axhline(level, color='red', linestyle='--', linewidth=1)

        left_pd = 0.1
        right_pd = 0.03
        top_pd = 0.09
        bottom_pd = 0.09

        plt.subplots_adjust(left=left_pd, right=1 - right_pd, top=1 - top_pd, bottom=bottom_pd)

        # Show the plot
        # plt.show()

        plt.savefig(f'FTbeta_{symbol}_{cOpen[-1]}_{cClose[-1]}.png', dpi=150, bbox_inches='tight', pad_inches=0.2)
        plt.close(fig)

        for chat_id in existed_chat_ids:
            try:
                with open(f'FTbeta_{symbol}_{cOpen[-1]}_{cClose[-1]}.png', 'rb') as pic:
                    bot_all.send_photo(chat_id, pic, message, parse_mode="HTML")
            except Exception as e:
                msg = f"⛔️ Failed to send photo to {chat_id}: {e}"
                personal_bot.send_message(chat_id=personal_id, text=msg)
                print(msg)

    else:
        msg = (f"⛔️ Failed screenshot data for {symbol} ({market_type}), status code {klines.status_code}\n"
               f"{klines}")
        personal_bot.send_message(chat_id=personal_id, text=msg)
        print(msg)
        return None

    # CLEANING
    # pic.close()
    # remove(f'FT{symbol}_{cOpen[-1]}_{cClose[-1]}.png')
    # plt.cla()
    # plt.clf()

# screenshoter_send_beta('FTMUSDT', 'f', 0.37, 'futures type')
