import asyncio
import os
from datetime import datetime

from binance.klines import get_klines
from bot_setup.bot_setup import bot
from mutual_variables.terminator import terminator


async def last_extremum(extr_type: str, extr_list: list, close_list: list) -> tuple[int, float]:
    # div_dist = float(os.getenv('divergence_distance'))

    div_dist = 0.5
    min_window = 15
    max_window = 120
    room_to_the_left = 10

    if extr_type == 'high':
        for i in range(min_window, max_window):
            relative_extremum = max(extr_list[-i: -i - room_to_the_left - 1: -1]) <= extr_list[-i]

            if relative_extremum:

                dist = abs(extr_list[-i] - close_list[-1]) / (max(extr_list[-i], close_list[-1]) / 100)
                rising = close_list[-1] > close_list[-2] > close_list[-3]
                if extr_list[-i] > close_list[-1] and rising and dist >= div_dist:
                    return i, dist

    else:
        for i in range(min_window, max_window):
            relative_extremum = min(extr_list[-i: -i - room_to_the_left - 1: -1]) >= extr_list[-i]

            if relative_extremum:

                dist = abs(extr_list[-i] - close_list[-1]) / (min(extr_list[-i], close_list[-1]) / 100)
                falling = close_list[-1] < close_list[-2] < close_list[-3]
                if extr_list[-i] < close_list[-1] and falling and dist >= div_dist:
                    return i, dist
    return 0, 0.0


async def divergences_search(coin):
    while not terminator.is_set():
        market_type = 'f'
        risk_usdt = 1
        the_klines = await get_klines(coin, "5m", market_type)
        if len(the_klines) > 0 and market_type == 'f':
            c_time, c_open, c_high, c_low, c_close, avg_vol, buy_vol, sell_vol, cumulative_delta, cd_sma = the_klines

            upper_extremum_index, upper_distance = await last_extremum('high', c_high, c_close)
            lower_extremum_index, lower_distance = await last_extremum('low', c_low, c_close)

            if upper_extremum_index != 0:
                highest_cumdelta = max(cumulative_delta[-1: -4: -1]) == max(cumulative_delta[-1: -upper_extremum_index - 1: -1])
                cumdelta_sma_relation = all(cd >= sma for cd, sma in zip(cumulative_delta[-1:-10:-1], cd_sma[-1:-10:-1]))

                if highest_cumdelta and cumdelta_sma_relation:
                    usdt_size = (risk_usdt / upper_distance) * 100

                    msg = f"\n{coin} SELL-DIV. {upper_extremum_index} cndl / {upper_distance:.2f}% / ${usdt_size:.2f}"
                    await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
                    print(msg)

            if lower_extremum_index != 0:
                lowest_cumdelta = min(cumulative_delta[-1: -4: -1]) == min(cumulative_delta[-1: -lower_extremum_index - 1: -1])
                cumdelta_sma_relation = all(cd <= sma for cd, sma in zip(cumulative_delta[-1:-10:-1], cd_sma[-1:-10:-1]))

                if lowest_cumdelta and cumdelta_sma_relation:
                    usdt_size = (risk_usdt / lower_distance) * 100

                    msg = f"\n{coin} BUY-DIV. {lower_extremum_index} cndl / {lower_distance:.2f}% / ${usdt_size:.2f}"
                    await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
                    print(msg)

        while True:
            await asyncio.sleep(0.5)
            if datetime.now().minute % 5 == 0 and datetime.now().second == 15:
                break
