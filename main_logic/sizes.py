import asyncio
import os
from datetime import datetime
from binance.klines import get_klines
from binance.order_book import order_book
from colors_values_update import update_manager, distance_calculator
from mutual_variables.dictionaries import update_lock
from mutual_variables.terminator import terminator

d_room = int(os.getenv("D_ROOM"))
abs_dis = float(os.getenv("ABS_DIS"))
size_mpl = float(os.getenv("SIZE_MPL"))
vol_mpl_depth = float(os.getenv("VOL_MPL_DEPTH"))


async def extremum_verification(
        coin: str,
        bar_close: float,
        depth: list,
        avg_vol: float,
):
    new_sizes = []

    for item in depth:
        item_price = item[0]
        item_volume = item[1]
        direction = 'up' if item_price >= bar_close else 'dn'

        # дистанція від 0 до абсолютного фільтра
        distance_per = await distance_calculator(item_price, bar_close, direction)
        distances_verified = 0 < distance_per <= abs_dis
        # щільність знаходиться між 9-ю спочатку, 9-ю з кінця
        size_withing_nines = d_room - 1 < depth.index(item) < len(depth) - d_room
        # щільність більше за середній об'єм
        size_volume_verified = item_volume >= avg_vol * vol_mpl_depth

        if not all([distances_verified, size_withing_nines, size_volume_verified]): continue

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
            the_klines = await get_klines(coin, "1m", "s")

            if len(depth) <= 0 or len(the_klines) <= 0:
                print(f'Depth of klines are empty!')
                await asyncio.sleep(62)
                continue

            c_time, c_open, c_high, c_low, c_close, avg_vol, buy_vol, sell_vol, cumulative_delta, cd_sma = the_klines
            depth = depth[1]  # [ціна, об'єм]

            # avg_atr_per = [(c_high[-c] - c_low[-c]) / (c_close[-c] / 100) for c in range(30)]
            # avg_atr_per = float('{:.2f}'.format(sum(avg_atr_per) / len(avg_atr_per)))

            # extremums = [None]
            #
            # # пошук екстремуму, а потім сайзу на ньому
            # for i in range(2, len(c_low) - c_room):
            #     if c_high[-i] >= max(c_high[-1: -i - c_room: -1]):
            #         extremums.append(c_high[-i])
            #
            #     if c_low[-i] <= min(c_low[-1: -i - c_room: -1]):
            #         extremums.append(c_low[-i])

            await extremum_verification(coin, c_close[-1], depth, avg_vol)
            await asyncio.sleep(50)
        else:
            await asyncio.sleep(1)

    return