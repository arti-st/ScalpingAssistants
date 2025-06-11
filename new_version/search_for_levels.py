import asyncio
import os
from asyncio import Event
from datetime import datetime
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
    while True:
        if datetime.now().hour % 2 == 0 and datetime.now().minute == 0:
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
        market_type: str,
        current_extremum: float or None,
        bar_close: float,
        avg_atr_per: float,
        depth: list,
        avg_vol: float,
        result: dict
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
            market_type_verbose = 'FUTURES' if market_type == 'f' else 'SPOT'

            # сайзи між ціною щільності -10 та ціною щільності
            lower_sizes = [depth[k][1] for k in range(depth.index(item) - d_room, depth.index(item))]
            # сайзи між ціною щільності +10 та ціною щільності
            higher_sizes = [depth[k][1] for k in range(depth.index(item) + 1, depth.index(item) + d_room + 1)]

            if all(item[1] >= dom * size_mpl for dom in lower_sizes + higher_sizes):
                if current_extremum:
                    print(f'{coin} {market_type_verbose} found CHART extr! {item[0]}!')
                    direction = '↗️' if item[0] >= bar_close else '↘️'
                else:
                    print(f'{coin} {market_type_verbose} found DEPTH extr! {item[0]}!')
                    direction = '⬆️' if item[0] >= bar_close else '⬇️'

                result[distance_per] = (
                    f"{datetime.now().strftime('%H:%M:%S')} "
                    f"{coin} "
                    f"{market_type_verbose}: "
                    f"{direction} {distance_per}% "
                    f"{item[0]}, "
                    f"x{round(item[1] / avg_vol, 1)}, ${round((item[1] * item[0]) / 1000, 2)}K"
                )


async def search(coin, update_lock):
    while not terminator.is_set():
        result = {}
        for market_type in ["f", "s"]:
            depth = await order_book(coin, 500, market_type)
            klines_len = int(os.getenv('KLINES_LEN', 240))
            the_klines = await klines(coin, "1m", klines_len, market_type)
            if len(depth) > 0 and len(the_klines) > 0:
                c_time, c_open, c_high, c_low, c_close, avg_vol = the_klines[0], the_klines[1], the_klines[2], the_klines[3], the_klines[4], the_klines[5]
                depth = depth[1]  # [ціна, об'єм]
                avg_atr_per = [(c_high[-c] - c_low[-c]) / (c_close[-c] / 100) for c in range(30)]
                avg_atr_per = float('{:.2f}'.format(sum(avg_atr_per) / len(avg_atr_per)))

                # пошук екстремуму, а потім сайзу на ньому
                for i in range(2, len(c_low) - c_room):
                    if c_high[-i] >= max(c_high[-1: -i - c_room: -1]):
                        await extremum_verification(
                            coin,
                            market_type,
                            c_high[-i],
                            c_close[-1],
                            avg_atr_per,
                            depth,
                            avg_vol,
                            result
                        )

                    if c_low[-i] <= min(c_low[-1: -i - c_room: -1]):
                        await extremum_verification(
                            coin,
                            market_type,
                            c_low[-i],
                            c_close[-1],
                            avg_atr_per,
                            depth,
                            avg_vol,
                            result
                        )

                await extremum_verification(
                    coin,
                    market_type,
                    None,
                    c_close[-1],
                    avg_atr_per,
                    depth,
                    avg_vol,
                    result
                )

        if len(result) == 0:
            async with update_lock:
                if coin_updates.get(coin):
                    coin_updates.pop(coin)
        elif len(result) == 1:
            async with update_lock:
                coin_updates[coin] = next(iter(result.values()))  # Returns the only value in the dictionary
        else:
            async with update_lock:
                smallest_key = min(result.keys())
                coin_updates[coin] = result[smallest_key]  # Return the value associated with the smallest key
        await asyncio.sleep(62)
