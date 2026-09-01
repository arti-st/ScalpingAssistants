import asyncio
import os
from datetime import datetime, timedelta

from binance.klines import get_klines
from bot_setup.bot_setup import bot
from mutual_variables.terminator import terminator

EXTREMUM_WINDOW = int(os.getenv("EXTREMUM_WINDOW"))
EXTREMUM_ROOM_LEFT = int(os.getenv("EXTREMUM_ROOM_LEFT"))
PRICE_RANGE_WINDOW = int(os.getenv("PRICE_RANGE_WINDOW"))
PRICE_RANGE_PART = int(os.getenv("PRICE_RANGE_PART"))
DELTA_WINDOW = int(os.getenv("DELTA_WINDOW"))


async def simple_sender(msg):
    await bot.send_message(
        chat_id=os.getenv('CHAT_ID'),
        text=msg,
    )


async def divergences_search(coin):
    last_check_minute = datetime.now().replace(second=0, microsecond=0)

    while not terminator.is_set():

        current_minute = datetime.now().replace(second=0, microsecond=0)

        if last_check_minute == current_minute:
            await asyncio.sleep(0.1)
            continue

        last_check_minute = current_minute

        for tf_verb, mins in {'5m': 5, '15m': 15, '30m': 30, '1h': 60}.items():
            if datetime.now().minute % mins == 0:

                the_klines = await get_klines(coin, tf_verb, "s")

                if len(the_klines) <= 0:
                    terminator.set()
                    continue

                (c_time, c_open, c_high, c_low, c_close, avg_vol, buy_vol, sell_vol, cumulative_delta,
                 cd_sma) = the_klines
                range_high = max(c_high[-PRICE_RANGE_WINDOW:])
                range_low = min(c_low[-PRICE_RANGE_WINDOW:])
                price_range = range_high - range_low
                range_part = price_range / PRICE_RANGE_PART

                # LONG SETUP
                upper_extremum_index, upper_extremum_price = None, None

                for i in range(3, EXTREMUM_WINDOW):

                    if c_high[-i] >= max(c_high[-i - EXTREMUM_ROOM_LEFT:]):
                        upper_extremum_index = i
                        upper_extremum_price = c_high[-i]
                        break

                if upper_extremum_index:

                    current_price = c_close[-1]
                    price_in_upper_range = current_price >= range_high - range_part

                    # Поточна cumulative delta зробила перелой останнього DELTA_WINDOW
                    delta_broke_low = (cumulative_delta[-1] <= min(cumulative_delta[-DELTA_WINDOW:-1]))

                    if price_in_upper_range and delta_broke_low:
                        await simple_sender(
                            f"BUY divergence on {coin} spot ({tf_verb}):\n"
                            f"Extremum {upper_extremum_price} ({upper_extremum_index} candles ago)"
                        )
                    # else:
                    #     print(f"No confirmed bullish divergence found for {coin} ({tf_verb})")
                # else:
                #     print(f"No upper extremum found for {coin} ({tf_verb})")

                # SHORT SETUP
                lower_extremum_index, lower_extremum_price = None, None

                for i in range(3, EXTREMUM_WINDOW):

                    if c_low[-i] <= min(c_low[-i - EXTREMUM_ROOM_LEFT:]):
                        lower_extremum_index = i
                        lower_extremum_price = c_low[-i]
                        break

                if lower_extremum_index:

                    current_price = c_close[-1]
                    price_in_lower_range = current_price <= range_low + range_part

                    # Поточна cumulative delta зробила перехай останнього DELTA_WINDOW
                    delta_broke_high = (cumulative_delta[-1] >= max(cumulative_delta[-DELTA_WINDOW:-1]))

                    if price_in_lower_range and delta_broke_high:
                        await simple_sender(
                            f"SELL divergence on {coin} spot ({tf_verb}):\n"
                            f"Extremum {lower_extremum_price} ({lower_extremum_index} candles ago)"
                        )
                    # else:
                    #     print(f"No confirmed bearish divergence found for {coin} ({tf_verb})")
                # else:
                #     print(f"No lower extremum found for {coin} ({tf_verb})")
    return
