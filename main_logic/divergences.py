import asyncio
import os
from datetime import datetime

from binance.klines import get_klines
from bot_setup.bot_sender import sender
from mutual_variables.terminator import terminator

TF = int(os.getenv("TF"))
EXTREMUM_WINDOW = int(os.getenv("EXTREMUM_WINDOW"))
EXTREMUM_ROOM_LEFT = int(os.getenv("EXTREMUM_ROOM_LEFT"))
PRICE_RANGE_WINDOW = int(os.getenv("PRICE_RANGE_WINDOW"))
PRICE_RANGE_PART = int(os.getenv("PRICE_RANGE_PART"))
DELTA_WINDOW = int(os.getenv("DELTA_WINDOW"))


async def divergences_search(coin):
    while not terminator.is_set():
        if datetime.now().minute % TF == 0:
            the_klines = await get_klines(coin, f"{TF}m", "s")

            if len(the_klines) <= 0:
                terminator.set()
                continue

            (c_time, c_open, c_high, c_low, c_close, avg_vol, buy_vol, sell_vol, cumulative_delta, cd_sma) = the_klines
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
                    await sender(f"BUY divergence on {coin} spot. Extremum - {upper_extremum_price}")
                else:
                    print(f"No confirmed upper extremum found for {coin}")

            else:
                print(f"No upper extremum found for {coin}")

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
                    await sender(f"SELL divergence on {coin} spot. Extremum - {lower_extremum_price}")
                else:
                    print(f"No confirmed lower extremum found for {coin}")

            else:
                print(f"No lower extremum found for {coin}")

            await asyncio.sleep(int(TF * 60 * 0.9))

    return
