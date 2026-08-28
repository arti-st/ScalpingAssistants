import asyncio
import os
from datetime import datetime
from binance.klines import get_klines
from binance.order_book import order_book
from .colors_values_update import update_manager, distance_calculator
from mutual_variables.dictionaries import update_lock, coins_to_ignore
from mutual_variables.terminator import terminator

d_room = int(os.getenv("D_ROOM", 3))
c_room = int(os.getenv("C_ROOM", 15))
abs_dis = float(os.getenv("ABS_DIS", 0.9))
size_mpl = float(os.getenv("SIZE_MPL", 5))
vol_mpl_depth = float(os.getenv("VOL_MPL_DEPTH", 2.0))
wiggle_room_perc = float(os.getenv("WIGGLE_ROOM_PERC", 0.005))


async def extremum_verification(
        coin: str,
        bar_close: float,
        depth: list,
        avg_vol: float,
        extremums: list,
):
    new_sizes = []

    for item in depth:
        item_price = item[0]
        item_volume = item[1]
        direction = 'up' if item_price >= bar_close else 'dn'

        # дистанція від поточної ціни до сайзу
        distance_per = await distance_calculator(item_price, bar_close, direction)
        distances_verified = 0 < distance_per <= abs_dis

        # сайз не повинен бути занадто близько до краю стакану
        size_withing_nines = (d_room - 1 < depth.index(item) < len(depth) - d_room)

        # сайз має бути більшим за середній об'єм
        size_volume_verified = item_volume >= avg_vol * vol_mpl_depth

        if not all([distances_verified, size_withing_nines, size_volume_verified]):
            continue

        # шукаємо відповідний екстремум графіка
        extremum_verified = False

        for extremum in extremums:
            extremum_price = extremum['price']
            extremum_direction = extremum['direction']

            # High підтверджує тільки up-сайз,
            # Low підтверджує тільки dn-сайз
            if extremum_direction != direction:
                continue

            price_difference_perc = (abs(item_price - extremum_price) / (extremum_price / 100))

            if price_difference_perc <= wiggle_room_perc:
                extremum_verified = True
                break

        if not extremum_verified:
            continue

        # сусідні сайзи нижче
        lower_sizes = [depth[k][1] for k in range(depth.index(item) - d_room, depth.index(item))]

        # сусідні сайзи вище
        higher_sizes = [depth[k][1] for k in range(depth.index(item) + 1, depth.index(item) + d_room + 1)]

        # сайз має бути більшим за всі сусідні сайзи
        if not all(item_volume >= dom * size_mpl for dom in lower_sizes + higher_sizes):
            continue

        new_sizes.append({'price': item_price, 'direction': direction})

    depth_values = {item[0]: item[1] for item in depth}

    async with update_lock:
        await update_manager(new_sizes, coin, bar_close, depth_values)


async def search(coin):
    while not terminator.is_set():
        if datetime.now().second <= 2:
            depth = await order_book(coin, "s")
            the_klines = await get_klines(
                coin,
                "1m",
                "s"
            )

            if len(depth) <= 0 or len(the_klines) <= 0:
                terminator.set()
                continue

            (
                c_time,
                c_open,
                c_high,
                c_low,
                c_close,
                avg_vol,
                buy_vol,
                sell_vol,
                cumulative_delta,
                cd_sma
            ) = the_klines

            depth = depth[1]  # [ціна, об'єм]
            extremums = []

            # пошук екстремумів на графіку
            for i in range(2, len(c_low) - c_room):

                # High extremum
                if c_high[-i] >= max(c_high[-1: -i - c_room: -1]):
                    extremums.append({'price': c_high[-i], 'direction': 'up'})

                # Low extremum
                if c_low[-i] <= min(c_low[-1: -i - c_room: -1]):
                    extremums.append({'price': c_low[-i], 'direction': 'dn'})

            await extremum_verification(coin, c_close[-1], depth, avg_vol, extremums)
            await asyncio.sleep(50)
        else:
            await asyncio.sleep(1)
    return
