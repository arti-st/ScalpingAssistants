import os
from datetime import datetime

from bot_setup.bot_setup import bot
from mutual_variables.dictionaries import coin_updates


async def distance_calculator(size_price, current_price, direction) -> float:
    if direction == 'up':
        distance_per = (size_price - current_price) / (max(size_price, current_price) / 100)
    else:
        distance_per = (current_price - size_price) / (min(size_price, current_price) / 100)

    round_precision = 2 if distance_per >= 0 else 1
    return round(distance_per, round_precision)


status_colors = {
    "orange": "🟧",
    "yellow": "🟨",
    "green": "🟩",
    "red": "🟥",
    "checked": "☑️",  # emoji version
    "empty": "▪️"  # black square same width
}


async def size_color_picker(size, max_size):
    if size < max_size * 0.5:
        return status_colors["empty"]
    elif max_size * 0.5 <= size < max_size * 0.75:
        return status_colors["yellow"]
    else:
        return status_colors["green"]


async def distance_color_picker(distance, abs_dis) -> str:
    if distance < 0:
        return status_colors["red"]
    if 0 <= distance <= abs_dis * 0.33:
        return status_colors["green"]
    elif abs_dis * 0.33 < distance <= abs_dis * 0.66:
        return status_colors["yellow"]
    elif abs_dis * 0.66 < distance <= abs_dis * 1.00:
        return status_colors["orange"]
    else:
        return status_colors["empty"]


async def update_values(size_price, direction, params, current_price, depth):
    if params.get('deprecated', False): return

    abs_dis = float(os.getenv("ABS_DIS"))
    params['updated'] = datetime.now()

    # Distance parameters
    previous_distance = params.get('distance_value', None)
    current_distance = await distance_calculator(size_price, current_price, direction)
    distance_color = await distance_color_picker(current_distance, abs_dis)

    params['distance_min'] = current_distance if previous_distance is None else min(previous_distance, current_distance)
    params['distance_max'] = current_distance if previous_distance is None else max(previous_distance, current_distance)
    params['distance_value'] = current_distance
    params['distance_color'] = distance_color

    # Size parameters
    previous_size = params.get('size_value', None)
    current_size = int((depth.get(size_price, 0.00) * size_price) / 1000)

    if not previous_size:
        params['size_min'] = current_size
        params['size_max'] = current_size
    else:
        params['size_max'] = max(params['size_max'], current_size)
        params['size_min'] = min(params['size_min'], current_size)

    params['size_value'] = current_size
    params['size_color'] = await size_color_picker(params['size_value'], params['size_max'])

    # Turn off the deprecated sizes
    if any([
        current_distance < 0,
        current_distance > abs_dis,
        current_size < params['size_max'] * 0.5
    ]):
        params['deprecated'] = True
        params['distance_color'] = status_colors['empty']
        params['size_color'] = status_colors['empty']
    else:
        params['deprecated'] = False

    # send message if some updated size is close enough
    if all([
        params['size_max'] != params['size_min'], # updated
        not params['deprecated'], # not deprecated
        current_distance <= abs_dis * 0.4 # close enough
    ]):
        return current_distance
    return

async def update_manager(new_sizes: list, coin: str, current_price: float, depth: dict):
    # print(f'{datetime.now()} Update manager for {coin} is started. New sizes: {len(new_sizes)}, overall sizes: {len(coin_updates)}')

    # adding new values
    for size in new_sizes:
        new_key = coin, size['price'], size['direction']
        if new_key not in coin_updates:
            coin_updates[new_key] = {'deprecated': False}
        else:
            coin_updates[new_key]['deprecated'] = False

    # iterating through existing values
    for key, params in coin_updates.items():
        symbol, size_price, direction = key
        if symbol != coin: continue
        if params['deprecated'] is True: continue

        print(f'{datetime.now()} Found an existing non-deprecated record for {coin}. Updating process has been started.')
        signal = await update_values(size_price, direction, params, current_price, depth)
        if signal is not None:
            dir_verb = 'above' if direction == 'up' else 'below'
            msg = f"Size on {coin} is in {signal}% {dir_verb}. Click /list"
            await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)

