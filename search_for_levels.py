import asyncio
import os
from datetime import datetime
from binance.klines import klines
from binance.order_book import order_book
from colors_values_update import update_manager, distance_calculator
from mutual_variables.dictionaries import update_lock
from mutual_variables.terminator import terminator

c_room = int(os.getenv("C_ROOM"))
d_room = int(os.getenv("D_ROOM"))

wiggle_room_perc = float(os.getenv("WIGGLE_ROOM_PERC"))
abs_dis = float(os.getenv("ABS_DIS"))

size_mpl = float(os.getenv("SIZE_MPL"))
vol_mpl_chart = float(os.getenv("VOL_MPL_CHART"))
vol_mpl_depth = float(os.getenv("VOL_MPL_DEPTH"))


async def extremum_verification(
        coin: str,
        extremums: list,
        bar_close: float,
        depth: list,
        avg_vol: float,
):
    new_sizes = []
    for current_extremum in extremums:
        vol_mpl = vol_mpl_chart if current_extremum else vol_mpl_depth

        for item in depth:
            item_price = item[0]
            item_volume = item[1]

            if current_extremum:
                wiggle_high = current_extremum * (1 + wiggle_room_perc)
                wiggle_low = current_extremum * (1 - wiggle_room_perc)
                size_location_verified = wiggle_low <= item_price <= wiggle_high
                # direction = '↗️' if item_price >= bar_close else '↘️'
            else:
                size_location_verified = True
                # direction = '⬆️' if item_price >= bar_close else '⬇️'

            direction = 'up' if item_price >= bar_close else 'dn'
            distance_per = await distance_calculator(item_price, bar_close, direction)
            distances_verified = 0 < distance_per <= abs_dis

            # щільність знаходиться між 9-ю спочатку, 9-ю з кінця
            size_withing_nines = d_room - 1 < depth.index(item) < len(depth) - d_room
            # щільність більше за середній об'єм
            size_volume_verified = item_volume >= avg_vol * vol_mpl

            if not all([distances_verified, size_location_verified,
                        size_withing_nines, size_volume_verified]): continue

            # сайзи між ціною щільності -10 та ціною щільності
            lower_sizes = [depth[k][1] for k in range(depth.index(item) - d_room, depth.index(item))]
            # сайзи між ціною щільності +10 та ціною щільності
            higher_sizes = [depth[k][1] for k in range(depth.index(item) + 1, depth.index(item) + d_room + 1)]
            # сайз більше за усі сусідні сайзи вгору та вниз
            if not all(item_volume >= dom * size_mpl for dom in lower_sizes + higher_sizes): continue

            new_sizes.append({'price': item_price, 'direction': direction})

    depth_values = {item[0]: item[1] for item in depth}
    async with update_lock:
        await update_manager(new_sizes, coin, bar_close, depth_values)


async def search(coin):
    while not terminator.is_set():
        if datetime.now().second <= 2:
            depth = await order_book(coin, "s")
            the_klines = await klines(coin, "1m", "s")

            if len(depth) <= 0 or len(the_klines) <= 0:
                print(f'Depth of klines are empty!')
                await asyncio.sleep(62)
                continue

            c_time, c_open, c_high, c_low, c_close, avg_vol, buy_vol, sell_vol, cumulative_delta, cd_sma = the_klines
            depth = depth[1]  # [ціна, об'єм]
            # avg_atr_per = [(c_high[-c] - c_low[-c]) / (c_close[-c] / 100) for c in range(30)]
            # avg_atr_per = float('{:.2f}'.format(sum(avg_atr_per) / len(avg_atr_per)))

            extremums = [None]

            # пошук екстремуму, а потім сайзу на ньому
            for i in range(2, len(c_low) - c_room):
                if c_high[-i] >= max(c_high[-1: -i - c_room: -1]):
                    extremums.append(c_high[-i])

                if c_low[-i] <= min(c_low[-1: -i - c_room: -1]):
                    extremums.append(c_low[-i])

            await extremum_verification(coin, extremums, c_close[-1], depth, avg_vol)
            await asyncio.sleep(50)
        else:
            await asyncio.sleep(1)

    return

# async def last_extremum(extr_type: str, extr_list: list, close_list: list) -> tuple[int, float]:
#     # div_dist = float(os.getenv('divergence_distance'))
#
#     div_dist = 0.5
#     min_window = 15
#     max_window = 120
#     room_to_the_left = 10
#
#     if extr_type == 'high':
#         for i in range(min_window, max_window):
#             relative_extremum = max(extr_list[-i: -i - room_to_the_left - 1: -1]) <= extr_list[-i]
#
#             if relative_extremum:
#
#                 dist = abs(extr_list[-i] - close_list[-1]) / (max(extr_list[-i], close_list[-1]) / 100)
#                 rising = close_list[-1] > close_list[-2] > close_list[-3]
#                 if extr_list[-i] > close_list[-1] and rising and dist >= div_dist:
#                     return i, dist
#
#     else:
#         for i in range(min_window, max_window):
#             relative_extremum = min(extr_list[-i: -i - room_to_the_left - 1: -1]) >= extr_list[-i]
#
#             if relative_extremum:
#
#                 dist = abs(extr_list[-i] - close_list[-1]) / (min(extr_list[-i], close_list[-1]) / 100)
#                 falling = close_list[-1] < close_list[-2] < close_list[-3]
#                 if extr_list[-i] < close_list[-1] and falling and dist >= div_dist:
#                     return i, dist


# async def divergences_search(coin):
#     while not terminator.is_set():
#         market_type = 'f'
#         risk_usdt = 1
#         the_klines = await klines(coin, "5m", market_type)
#         if len(the_klines) > 0 and market_type == 'f':
#             c_time, c_open, c_high, c_low, c_close, avg_vol, buy_vol, sell_vol, cumulative_delta, cd_sma = the_klines
#
#             upper_extremum_index, upper_distance = await last_extremum('high', c_high, c_close)
#             lower_extremum_index, lower_distance = await last_extremum('low', c_low, c_close)
#
#             if upper_extremum_index != 0:
#                 highest_cumdelta = max(cumulative_delta[-1: -4: -1]) == max(cumulative_delta[-1: -upper_extremum_index - 1: -1])
#                 cumdelta_sma_relation = all(cd >= sma for cd, sma in zip(cumulative_delta[-1:-10:-1], cd_sma[-1:-10:-1]))
#
#                 if highest_cumdelta and cumdelta_sma_relation:
#                     usdt_size = (risk_usdt / upper_distance) * 100
#
#                     msg = f"\n{coin} SELL-DIV. {upper_extremum_index} cndl / {upper_distance:.2f}% / ${usdt_size:.2f}"
#                     await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
#                     print(msg)
#
#             if lower_extremum_index != 0:
#                 lowest_cumdelta = min(cumulative_delta[-1: -4: -1]) == min(cumulative_delta[-1: -lower_extremum_index - 1: -1])
#                 cumdelta_sma_relation = all(cd <= sma for cd, sma in zip(cumulative_delta[-1:-10:-1], cd_sma[-1:-10:-1]))
#
#                 if lowest_cumdelta and cumdelta_sma_relation:
#                     usdt_size = (risk_usdt / lower_distance) * 100
#
#                     msg = f"\n{coin} BUY-DIV. {lower_extremum_index} cndl / {lower_distance:.2f}% / ${usdt_size:.2f}"
#                     await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
#                     print(msg)
#
#         while True:
#             await asyncio.sleep(0.5)
#             if datetime.now().minute % 5 == 0 and datetime.now().second == 15:
#                 break
