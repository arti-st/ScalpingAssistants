import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "params.env"))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "main.env"))

import asyncio
from charting.triangle_chart import save_triangle_chart

start_search = 5
search_window = 30


def validate_extremum(e_type: str, e_index: int, e_list: list) -> bool | None:
    try:
        if e_type == 'max':
            return e_list[-e_index] == max(e_list[-e_index - 10: -1])
        else:
            return e_list[-e_index] == min(e_list[-e_index - 10: -1])
    except Exception as e:
        print(e, e_type, e_index)


def hlhl_search(c_high, c_low):
    range_len = int(os.getenv('MIN_KLINES_LEN', 150))
    chart_range = max(c_high[-range_len:]) - min(c_low[-range_len:])

    for fourth_point_index in range(start_search, start_search + search_window):
        # 4th point (Low)
        if validate_extremum('min', fourth_point_index, c_low):
            # 3rd point (High) - має бути далі в минулому (більший індекс)
            for third_point_index in range(fourth_point_index + 1, fourth_point_index + search_window + 1):
                if validate_extremum('max', third_point_index, c_high):
                    # 2nd point (Low) - має бути ще далі в минулому
                    for second_point_index in range(third_point_index + 1, third_point_index + search_window + 1):
                        if validate_extremum('min', second_point_index, c_low):
                            # 1st point (High) - має бути найдалі в минулому
                            for first_point_index in range(second_point_index + 1, second_point_index + search_window + 1):
                                if validate_extremum('max', first_point_index, c_high):
                                    if c_high[-third_point_index] - c_low[-second_point_index] <= chart_range / 2:
                                        return True, [first_point_index, second_point_index, third_point_index, fourth_point_index]

    return False, []


def lhlh_search(c_high, c_low):
    range_len = int(os.getenv('MIN_KLINES_LEN', 150))
    chart_range = max(c_high[-range_len:]) - min(c_low[-range_len:])

    for fourth_point_index in range(start_search, start_search + search_window):
        # 4th point (High)
        if validate_extremum('max', fourth_point_index, c_high):
            # 3rd point (Low) - має бути далі в минулому (більший індекс)
            for third_point_index in range(fourth_point_index + 1, fourth_point_index + search_window + 1):
                if validate_extremum('min', third_point_index, c_low):
                    # 2nd point (High) - має бути ще далі в минулому
                    for second_point_index in range(third_point_index + 1, third_point_index + search_window + 1):
                        if validate_extremum('max', second_point_index, c_high):
                            # 1st point (Low) - має бути найдалі в минулому
                            for first_point_index in range(second_point_index + 1, second_point_index + search_window + 1):
                                if validate_extremum('min', first_point_index, c_low):
                                    if c_high[-second_point_index] - c_low[-third_point_index] <= chart_range / 2:
                                        return True, [first_point_index, second_point_index, third_point_index, fourth_point_index]

    return False, []


def no_breakouts(e_indexes, flag_type, c_high, c_low, atr) -> tuple[bool, str]:
    if not e_indexes:
        return False, ""
    # Лінії
    if e_indexes[0] == e_indexes[2]:
        falling_factor = 0
    else:
        if flag_type == 'hlhl':
            falling_factor = (c_high[-e_indexes[0]] - c_high[-e_indexes[2]]) / (e_indexes[0] - e_indexes[2])
        else:  # lhlh
            falling_factor = (c_high[-e_indexes[1]] - c_high[-e_indexes[3]]) / (e_indexes[1] - e_indexes[3])

    if e_indexes[1] == e_indexes[3]:
        rising_factor = 0
    else:
        if flag_type == 'hlhl':
            rising_factor = (c_low[-e_indexes[3]] - c_low[-e_indexes[1]]) / (e_indexes[1] - e_indexes[3])
        else:  # lhlh
            rising_factor = (c_low[-e_indexes[2]] - c_low[-e_indexes[0]]) / (e_indexes[0] - e_indexes[2])

    # Перевірка напрямку ліній
    if falling_factor < 0 or rising_factor < 0:
        return False, ""

    # Перевірка пробоїв
    if flag_type == 'hlhl':
        for h in range(1, e_indexes[0]):
            current_high = c_high[-h]
            current_line = c_high[-e_indexes[0]] - falling_factor * (e_indexes[0] - h)
            if current_high > current_line:
                return False, ""

        for l in range(1, e_indexes[1]):
            current_low = c_low[-l]
            current_line = c_low[-e_indexes[1]] + rising_factor * (e_indexes[1] - l)
            if current_low < current_line:
                return False, ""

    else:  # lhlh
        for l in range(1, e_indexes[0]):
            current_low = c_low[-l]
            current_line = c_low[-e_indexes[0]] + rising_factor * (e_indexes[0] - l)
            if current_low < current_line:
                return False, ""

        for h in range(1, e_indexes[1]):
            current_high = c_high[-h]
            current_line = c_high[-e_indexes[1]] - falling_factor * (e_indexes[1] - h)
            if current_high > current_line:
                return False, ""

    direction = f"FALLING" if falling_factor > rising_factor else "RISING"
    speed = f" {round((falling_factor / c_high[-1]) * 1000, 2)}/{round((rising_factor / c_low[-1]) * 1000, 2)}"
    return True, direction + speed


async def triangle_found(coin, tf, klines, li=None) -> tuple[bool, str, str]:
    c_time, c_open, c_high, c_low, c_close, avg_vol, buy_vol, sell_vol, cumulative_delta, cd_sma = klines
    if li is not None:
        c_time, c_open, c_high, c_low, c_close, avg_vol, buy_vol, sell_vol, cumulative_delta, cd_sma = (
            c_time[:li + 1], c_open[:li + 1], c_high[:li + 1], c_low[:li + 1], c_close[:li + 1],
            avg_vol, buy_vol[:li + 1], sell_vol[:li + 1], cumulative_delta[:li + 1], cd_sma[:li + 1])

    avg_atr = sum([(c_high[-c] - c_low[-c]) / (c_close[-c] / 100) for c in range(1, 61)]) / 60

    hlhl_found, hlhl_indexes = hlhl_search(c_high, c_low)
    no_breaks, direction = no_breakouts(hlhl_indexes, 'hlhl', c_high, c_low, avg_atr)
    if hlhl_found and no_breaks:
        # msg = (f'{datetime.fromtimestamp(float(c_time[-1]) / 1000)} \n'
        #        f'H-L-H-L triangle found! \n'
        #        f'First high: {c_high[-hlhl_indexes[0]]}\n'
        #        f'Second low: {c_low[-hlhl_indexes[1]]}\n'
        #        f'Third high: {c_high[-hlhl_indexes[2]]}\n'
        #        f'Fourth low: {c_low[-hlhl_indexes[3]]}\n'
        #        f'{hlhl_indexes}')
        img_path = save_triangle_chart(coin, c_time, c_open, c_high, c_low, c_close, hlhl_indexes, "hlhl", tf.upper(), direction)
        return True, direction, img_path

    lhlh_found, lhlh_indexes = lhlh_search(c_high, c_low)
    no_breaks, direction = no_breakouts(lhlh_indexes, 'lhlh', c_high, c_low, avg_atr)
    if lhlh_found and no_breaks:
        # msg = (f'{datetime.fromtimestamp(float(c_time[-1]) / 1000)} \n'
        #        f'L-H-L-H triangle found! \n'
        #        f'First low: {c_low[-lhlh_indexes[0]]}\n'
        #        f'Second high: {c_high[-lhlh_indexes[1]]}\n'
        #        f'Third low: {c_low[-lhlh_indexes[2]]}\n'
        #        f'Fourth high: {c_high[-lhlh_indexes[3]]}\n'
        #        f'{lhlh_indexes}')
        img_path = save_triangle_chart(coin, c_time, c_open, c_high, c_low, c_close, lhlh_indexes, "lhlh", tf.upper(), direction)
        return True, direction, img_path

    return False, 'Not found', ''


# if __name__ == '__main__':
#
#     import aiohttp
#
#
#     async def main():
#         # k_lines = await get_klines('ALPINEUSDT', '1m', 'f')
#         # res = await triangle_found(coin='ALPINEUSDT', klines=k_lines)
#         # print(res)
#         #
#
#         async with aiohttp.ClientSession() as session:
#             # Отримуємо всі торгові символи через уніфіковану функцію
#             ts_dict = await get_trading_symbols(session, 'USDT')
#             coins = list(ts_dict.keys())
#
#         for coin in coins:
#             k_lines = await get_klines(coin, '1m', 'f')
#             print(coin, ':')
#             res = await triangle_found(coin=coin, tf='1m', klines=k_lines)
#             if res[0]:
#                 print(res[1])
#                 print(res[2])
#                 print('')
#             await asyncio.sleep(0.5)

            # for i in range(120, len(k_lines[0])):
            #     res = await triangle_found(coin=coin, tf='1m', klines=k_lines, li=i)
            #     if res[0]:
            #         print(res[1])
            #         print(res[2])
            #         print('')
            #         break

            # break


    asyncio.run(main())
