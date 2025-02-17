import asyncio
from asyncio import Event
from datetime import datetime
from new_version.klines import klines
from new_version.order_book import order_book


coin_updates = {}  # Shared updates storage
terminator = Event()

async def restarter():
    while True:
        if datetime.now().hour % 4 == 0 and datetime.now().minute == 0:
            terminator.set()
            break
        else:
            await asyncio.sleep(60)

async def search(coin, update_lock):
    while not terminator.is_set():

        c_room = 95  # кімната зліва
        d_room = 10  # вікно зверху і знизу стакану

        wiggle_room_perc = 0.004
        atr_dis = 4.0  # мультиплікатор відстані до сайзу в ATR
        abs_dis = 0.5  # мультиплікатор відстані до сайзу %

        size_mpl = 2.0  # мультиплікатор максимального сайзу
        vol_mpl = 5.0 # мультиплікатор відносності об'єму

        result = {}

        for market_type in ["f", "s"]:
            market_type_verbose = 'FUTURES' if market_type == 'f' else 'SPOT'

            depth = await order_book(coin, 500, market_type)
            the_klines = await klines(coin, "1m", 100, market_type)

            if len(depth) > 0 and len(the_klines) > 0:

                c_time, c_open, c_high, c_low, c_close, avg_vol = the_klines[0], the_klines[1], the_klines[2], the_klines[3], the_klines[4], the_klines[5]
                depth = depth[1]  # [ціна, об'єм]

                avg_atr_per = [(c_high[-c] - c_low[-c]) / (c_close[-c] / 100) for c in range(30)]
                avg_atr_per = float('{:.2f}'.format(sum(avg_atr_per) / len(avg_atr_per)))

                # пошук екстремуму, а потім сайзу на ньому
                for i in range(2, len(c_low) - c_room):

                    # дистанція до ціни
                    distance_per = abs(c_high[-i] - c_close[-1]) / (c_close[-1] / 100)
                    distance_per = float('{:.2f}'.format(distance_per))

                    if c_high[-i] >= max(c_high[-1: -i - c_room: -1]) and distance_per <= atr_dis * avg_atr_per and distance_per <= abs_dis:
                        for item in depth:
                            wiggle_high = c_high[-i] * (1 + wiggle_room_perc)
                            wiggle_low = c_high[-i] * (1 - wiggle_room_perc)
                            # щільність знаходиться між 9-ю спочатку, 9-ю з кінця та ціна щільності == хаю
                            if d_room - 1 < depth.index(item) < len(depth) - d_room and wiggle_low <= item[0] <= wiggle_high:
                                # сайзи між ціною щільності -10 та ціною щільності
                                lower_sizes = [depth[k][1] for k in range(depth.index(item) - d_room, depth.index(item))]
                                # сайзи між ціною щільності +10 та ціною щільності
                                higher_sizes = [depth[k][1] for k in range(depth.index(item) + 1, depth.index(item) + d_room + 1)]

                                if all(item[1] >= dom * size_mpl for dom in lower_sizes + higher_sizes) and item[1] >= avg_vol * vol_mpl:
                                    print(f'{coin} {market_type_verbose} found high extr: {c_high[-i]}!')
                                    direction = '🔼' if item[0] >= c_close[-1] else '🔽'
                                    result[round(distance_per, 2)] = (
                                        f"{datetime.now().strftime('%H:%M:%S')} "
                                        f"{coin} "
                                        f"{market_type_verbose}: "
                                        f"{direction} {round(distance_per, 2)}% "
                                        f"{item[0]}, "
                                        f"x{round(item[1] / avg_vol, 1)}"
                                    )
                                # break

                    # дистанція до ціни
                    distance_per = abs(c_low[-i] - c_close[-1]) / (c_close[-1] / 100)
                    distance_per = float('{:.2f}'.format(distance_per))

                    if c_low[-i] <= min(c_low[-1: -i - c_room: -1]) and distance_per <= atr_dis * avg_atr_per and distance_per <= abs_dis:
                        for item in depth:
                            wiggle_high = c_low[-i] * (1 + wiggle_room_perc)
                            wiggle_low = c_low[-i] * (1 - wiggle_room_perc)
                            # щільність знаходиться між 9-ю спочатку, 9-ю з кінця та ціна щільності == лою
                            if d_room - 1 < depth.index(item) < len(depth) - d_room and wiggle_low <= item[0] <= wiggle_high:
                                # сайзи між ціною щільності -10 та ціною щільності
                                lower_sizes = [depth[k][1] for k in range(depth.index(item) - d_room, depth.index(item))]
                                # сайзи між ціною щільності +10 та ціною щільності
                                higher_sizes = [depth[k][1] for k in range(depth.index(item) + 1, depth.index(item) + d_room + 1)]

                                if all(item[1] >= dom * size_mpl for dom in lower_sizes + higher_sizes) and item[1] >= avg_vol * vol_mpl:
                                    print(f'{coin} {market_type_verbose} found low extr: {c_low[-i]}!')
                                    direction = '🔼' if item[0] >= c_close[-1] else '🔽'
                                    result[round(distance_per, 2)] = (
                                        f"{datetime.now().strftime('%H:%M:%S')} "
                                        f"{coin} "
                                        f"{market_type_verbose}: "
                                        f"{direction} {round(distance_per, 2)}% "
                                        f"{item[0]}, "
                                        f"x{round(item[1] / avg_vol, 1)}"
                                    )
                                # break
            # else:
            #     logging.warning(f'{symbol} {market_type}-data  is empty')

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
