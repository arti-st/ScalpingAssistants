import asyncio
import os
from asyncio import Event
from datetime import datetime

from new_version.bot_setup.bot_setup import bot
from new_version.klines import klines
from new_version.order_book import order_book

coin_updates = {}  # Shared updates storage
terminator = Event()

c_room = int(os.getenv("C_ROOM", 30))
d_room = int(os.getenv("D_ROOM", 10))

wiggle_room_perc = float(os.getenv("WIGGLE_ROOM_PERC", 0.005))
atr_dis = float(os.getenv("ATR_DIS", 4.0))
abs_dis = float(os.getenv("ABS_DIS", 0.7))

size_mpl = float(os.getenv("SIZE_MPL", 2.0))
vol_mpl_chart = float(os.getenv("VOL_MPL_CHART", 3.0))
vol_mpl_depth = float(os.getenv("VOL_MPL_DEPTH", 8.0))


async def restarter():
    refresh_hours = int(os.getenv('UPDATE_TIME_HOURS', '2'))
    while True:
        if datetime.now().hour % refresh_hours == 0 and datetime.now().minute == 0:
            terminator.set()
            break
        else:
            await asyncio.sleep(60)


async def distance_calculator(current_extremum, bar_close) -> float:
    distance_per = abs(current_extremum - bar_close) / (max(current_extremum, bar_close) / 100)
    distance_per = float('{:.2f}'.format(distance_per))
    return round(distance_per, 2)


async def extremum_verification(
        coin: str,
        current_extremum: float or None,
        bar_close: float,
        avg_atr_per: float,
        depth: list,
        avg_vol: float,
        update_lock,
):
    vol_mpl = vol_mpl_chart if current_extremum else vol_mpl_depth

    for item in depth:
        distance_per = await distance_calculator(item[0], bar_close)
        distances_verified = distance_per <= atr_dis * avg_atr_per and distance_per <= abs_dis

        if current_extremum:
            wiggle_high = current_extremum * (1 + wiggle_room_perc)
            wiggle_low = current_extremum * (1 - wiggle_room_perc)
            size_location_verified = wiggle_low <= item[0] <= wiggle_high
        else:
            size_location_verified = True

        size_withing_nines = d_room - 1 < depth.index(item) < len(depth) - d_room  # щільність знаходиться між 9-ю спочатку, 9-ю з кінця
        size_volume_verified = item[1] >= avg_vol * vol_mpl

        # щільність знаходиться між 9-ю спочатку, 9-ю з кінця та ціна щільності == лою
        if all([distances_verified, size_location_verified, size_withing_nines, size_volume_verified]):
            # сайзи між ціною щільності -10 та ціною щільності
            lower_sizes = [depth[k][1] for k in range(depth.index(item) - d_room, depth.index(item))]
            # сайзи між ціною щільності +10 та ціною щільності
            higher_sizes = [depth[k][1] for k in range(depth.index(item) + 1, depth.index(item) + d_room + 1)]

            if all(item[1] >= dom * size_mpl for dom in lower_sizes + higher_sizes):
                size_usdt = int((item[1] * item[0]) / 1000)
                gen_dir = 'up' if item[0] >= bar_close else 'dn'
                if current_extremum:
                    # print(f'{datetime.now()} {coin}, {market_type_verbose}, CHART size (${size_usdt}K) on {item[0]}!')
                    direction = '↗️' if item[0] >= bar_close else '↘️'
                else:
                    # print(f'{datetime.now()} {coin}, {market_type_verbose}, DOM size (${size_usdt}K) on {item[0]}!')
                    direction = '⬆️' if item[0] >= bar_close else '⬇️'

                # Ensure coin exists
                if coin not in coin_updates:
                    coin_updates[coin] = {}

                key = (item[0], gen_dir)

                if not current_extremum and key in coin_updates:
                    continue

                # If record exists — preserve min/max logic
                if key in coin_updates[coin]:
                    hist = coin_updates[coin][key]
                    current_min_dist = hist['min_dist'] if hist['min_dist'] < distance_per else distance_per
                    current_max_dist = hist['max_dist'] if hist['max_dist'] > distance_per else distance_per
                    current_min_size = hist['min_size'] if hist['min_size'] < size_usdt else size_usdt
                    current_max_size = hist['max_size'] if hist['max_size'] > size_usdt else size_usdt
                else:
                    # First time for this (price, direction)
                    current_min_dist = distance_per
                    current_max_dist = distance_per
                    current_min_size = size_usdt
                    current_max_size = size_usdt

                dynamic = '🔸' if current_min_dist != current_max_dist else '🔹'

                # Update without overwriting other entries
                async with update_lock:
                    coin_updates[coin][key] = {
                        'upd_time': datetime.now(),
                        'direction': direction,
                        'dynamic': dynamic,
                        'min_dist': current_min_dist,
                        'max_dist': current_max_dist,
                        'cur_dist': distance_per,
                        'min_size': current_min_size,
                        'max_size': current_max_size,
                        'cur_size': size_usdt
                    }

    if coin not in coin_updates:
        return

    async with update_lock:
        for key, values in list(coin_updates[coin].items()):
            price, gen_dir = key

            if gen_dir == 'up' and bar_close > price:
                coin_updates[coin][key]['dynamic'] = '🔻'

            if gen_dir == 'dn' and bar_close < price:
                coin_updates[coin][key]['dynamic'] = '🔻'


async def search(coin, update_lock):
    while not terminator.is_set():
        # result = {}
        # for market_type in ["f", "s"]:
        market_type = "s"
        depth = await order_book(coin, 500, market_type)
        klines_len = int(os.getenv('KLINES_LEN', 1000))
        the_klines = await klines(coin, "1m", klines_len, market_type)

        if len(depth) <= 0 or len(the_klines) <= 0:
            await asyncio.sleep(62)
            continue

        c_time, c_open, c_high, c_low, c_close, avg_vol, buy_vol, sell_vol, cumulative_delta, cd_sma = the_klines
        depth = depth[1]  # [ціна, об'єм]
        avg_atr_per = [(c_high[-c] - c_low[-c]) / (c_close[-c] / 100) for c in range(30)]
        avg_atr_per = float('{:.2f}'.format(sum(avg_atr_per) / len(avg_atr_per)))

        # пошук екстремуму, а потім сайзу на ньому
        for i in range(2, len(c_low) - c_room):
            if c_high[-i] >= max(c_high[-1: -i - c_room: -1]):
                await extremum_verification(
                    coin, c_high[-i], c_close[-1],
                    avg_atr_per, depth, avg_vol, update_lock
                )

            if c_low[-i] <= min(c_low[-1: -i - c_room: -1]):
                await extremum_verification(
                    coin, c_low[-i], c_close[-1],
                    avg_atr_per, depth, avg_vol, update_lock
                )

        # пошук тільки сайзу
        await extremum_verification(
            coin, None, c_close[-1],
            avg_atr_per, depth, avg_vol, update_lock
        )

        await asyncio.sleep(62)


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
        klines_len = 480
        risk_usdt = 1
        the_klines = await klines(coin, "5m", klines_len, market_type)
        if len(the_klines) > 0 and market_type == 'f':
            c_time, c_open, c_high, c_low, c_close, avg_vol, buy_vol, sell_vol, cumulative_delta, cd_sma = the_klines

            upper_extremum_index, upper_distance = await last_extremum('high', c_high, c_close)
            lower_extremum_index, lower_distance = await last_extremum('low', c_low, c_close)

            if upper_extremum_index != 0:
                highest_cumdelta = max(cumulative_delta[-1: -4: -1]) == max(cumulative_delta[-1: -upper_extremum_index - 1: -1])
                cumdelta_sma_relation = all(cd >= sma for cd, sma in zip(cumulative_delta[-1:-10:-1], cd_sma[-1:-10:-1]))

                if highest_cumdelta and cumdelta_sma_relation:
                    usdt_size = (risk_usdt / upper_distance) * 100
                    coin_size = usdt_size / c_high[-upper_extremum_index]

                    msg = f"\n{coin} SELL-DIV. {upper_extremum_index} cndl / {upper_distance:.2f}% / ${usdt_size:.2f}"
                    await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
                    print(msg)

            if lower_extremum_index != 0:
                lowest_cumdelta = min(cumulative_delta[-1: -4: -1]) == min(cumulative_delta[-1: -lower_extremum_index - 1: -1])
                cumdelta_sma_relation = all(cd <= sma for cd, sma in zip(cumulative_delta[-1:-10:-1], cd_sma[-1:-10:-1]))

                if lowest_cumdelta and cumdelta_sma_relation:
                    usdt_size = (risk_usdt / lower_distance) * 100
                    coin_size = usdt_size / c_high[-lower_extremum_index]

                    msg = f"\n{coin} BUY-DIV. {lower_extremum_index} cndl / {lower_distance:.2f}% / ${usdt_size:.2f}"
                    await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
                    print(msg)

        while True:
            await asyncio.sleep(0.5)
            if datetime.now().minute % 5 == 0 and datetime.now().second == 15:
                break
