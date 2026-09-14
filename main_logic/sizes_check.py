import asyncio
import os
from datetime import datetime

from database_v2 import create_renew_size, change_size_status
from mutual_variables.terminator import send_alert

d_room = int(os.getenv("D_ROOM"))
c_room = int(os.getenv("C_ROOM"))
size_dom_mpl = float(os.getenv("SIZE_VS_DOM_MPL"))
size_avg_mpl = float(os.getenv("SIZE_VS_AVG_MPL"))
wiggle_room_perc = float(os.getenv("WIGGLE_ROOM_PERC"))


class SizesManager:

    def __init__(self, coin):

        self.coin = coin
        self.tick_size = None
        self.avg_atr = None
        self.depth = dict()
        self.current_price = None
        self.c_high = None
        self.c_low = None
        self.c_close = None
        self.avg_vol = None
        self.new_sizes = dict()
        self.new_extremums = set()
        self.existing_sizes = set()
        self.alerts = dict()

    async def size_comparison(self, size_price):

        min_price = min(self.depth[0][0], self.depth[-1][0])
        max_price = max(self.depth[0][0], self.depth[-1][0])

        if not min_price <= size_price <= max_price:
            return "too_far"

        price_index = next((i for i, item in enumerate(self.depth) if item[0] == size_price), None)
        size_volume = next((item[1] for item in self.depth if item[0] == size_price), None)

        if price_index is None or size_volume is None:
            return "removed"

        lower_start = max(0, price_index - d_room)
        lower_sizes = [self.depth[k][1] for k in range(lower_start, price_index)]

        higher_end = min(len(self.depth), price_index + d_room + 1)
        higher_sizes = [self.depth[k][1] for k in range(price_index + 1, higher_end)]

        neighbors = lower_sizes + higher_sizes

        if not neighbors:
            raise Exception(f'No neighbors in {self.coin} depth!')

        max_neighbor_volume = max(neighbors)

        size_vs_dom = size_volume / max_neighbor_volume
        size_vs_avg = size_volume / self.avg_vol

        return round(size_vs_dom, 2), round(size_vs_avg, 2)

    async def new_sizes_search(self) -> float:
        """
        Сайз:
        - більший за сусідні в Х разів
        - більший за середній об'єм в Х разів

        Оновлюємо словник.
        """
        self.new_sizes.clear()

        for price_index, item in enumerate(self.depth):

            size_price = item[0]

            size_comparison = await self.size_comparison(size_price)

            if isinstance(size_comparison, str):
                continue

            size_vs_dom, size_vs_avg = size_comparison

            if size_vs_dom >= size_dom_mpl and size_vs_avg >= size_avg_mpl:
                self.new_sizes[size_price] = {'size_vs_dom': size_vs_dom, 'size_vs_avg': size_vs_avg}

    async def new_extremums_search(self):
        """
        Екстремуми:
        - перебили останні Х свічок.

        Оновлюємо сет.
        """
        self.new_extremums.clear()

        # пошук екстремумів на графіку
        for i in range(2, len(self.c_close) - c_room):

            # High extremum
            if self.c_high[-i] >= max(self.c_high[-1: -i - c_room: -1]):
                self.new_extremums.add(self.c_high[-i])

            # Low extremum
            if self.c_low[-i] <= min(self.c_low[-1: -i - c_room: -1]):
                self.new_extremums.add(self.c_low[-i])

    async def new_two_dim_verification(self) -> list:
        """
        Звіряємо екстремуми з сайзами.
        Видаляємо непідтверджені сайзи
        """
        verified_sizes = {}

        for size_price, params in self.new_sizes.items():
            for extr in self.new_extremums:

                lowest_wiggle = extr - extr * (wiggle_room_perc / 100)
                highest_wiggle = extr + extr * (wiggle_room_perc / 100)

                if lowest_wiggle <= size_price <= highest_wiggle:
                    params['chart_price'] = extr
                    verified_sizes[size_price] = params
                    break

        self.new_sizes = verified_sizes

    async def calc_distance(self, size_dir, size_price):
        if size_dir == 1:
            distance_per = (size_price - self.current_price) / (max(size_price, self.current_price) / 100)
        else:
            distance_per = (self.current_price - size_price) / (min(size_price, self.current_price) / 100)

        round_precision = 2 if distance_per >= 0 else 1
        return round(distance_per, round_precision)

    async def new_size_decision(self) -> float:
        for size_price, params in self.new_sizes.items():
            size_vs_dom = params['size_vs_dom']
            size_vs_avg = params['size_vs_avg']
            chart_price = params['chart_price']

            size_dir = 1 if size_price >= self.current_price else 0

            size_dist = await self.calc_distance(size_dir, size_price)
            distances_verified = 0 < size_dist <= self.avg_atr * 3

            if distances_verified and size_price not in self.existing_sizes:
                await asyncio.to_thread(
                    create_renew_size,
                    self.coin,  # колонка coin
                    size_price,  # колонка dom
                    chart_price,  # колонка chart
                    self.current_price,  # колонка current_price
                    size_dir,  # колонка direction
                    size_dist,  # колонка distance
                    size_vs_dom,  # колонка size_vs_dom
                    size_vs_avg,  # колонка size_vs_dom
                )

    async def is_crossed(self, size_dir: int, size_price: float) -> bool:
        if size_dir == 1:
            if size_price >= self.current_price:
                return False
        else:
            if size_price <= self.current_price:
                return False
        return True

    async def update_existing(self, current_sizes: dict, repeat_rate: int):
        """
        1-Open
        2-Open/Crossed
        3-Too far
        4-Removed
        5-Crossed
        6-Not listed
        """
        for size_price, params in current_sizes.items():
            # size_date = params['date']
            # size_chart = params['chart']
            size_dir = params['direction']
            continuous_count = params['continuous_count']
            total_count = params['total_count']
            # status = params['status']

            size_dist = await self.calc_distance(size_dir, size_price)

            is_crossed = await self.is_crossed(size_dir, size_price)
            if is_crossed:
                await asyncio.to_thread(change_size_status, self.coin, size_price, 5)
                continue

            size_comparison = await self.size_comparison(size_price)
            if isinstance(size_comparison, str):
                if size_comparison == "removed":
                    await asyncio.to_thread(change_size_status, self.coin, size_price, 4)
                else:
                    await asyncio.to_thread(change_size_status, self.coin, size_price, 3)
                continue

            if size_dist > self.avg_atr * 3:
                await asyncio.to_thread(change_size_status, self.coin, size_price, 3)
                continue

            size_vs_dom, size_vs_avg = size_comparison
            if size_vs_dom >= size_dom_mpl and size_vs_avg >= size_avg_mpl:

                await asyncio.to_thread(
                    create_renew_size,
                    self.coin,  # колонка coin
                    size_price,  # колонка dom
                    None,  # колонка chart
                    self.current_price,  # колонка current_price
                    size_dir,  # колонка direction
                    size_dist,  # колонка distance
                    size_vs_dom,  # колонка size_vs_dom
                    size_vs_avg,  # колонка size_vs_dom
                )

                minute = datetime.now().strftime("%H:%M")
                continuous_count += 1
                total_count += 1

                repeated_enough_times = continuous_count >= repeat_rate
                didnt_alerted_this_minute = self.alerts.get(size_price) != minute
                distance_within_atr = size_dist <= self.avg_atr

                if repeated_enough_times and didnt_alerted_this_minute and distance_within_atr:
                    send_alert.set()
                    # starting_parameters['alert_updates'][self.coin] = (
                    #     f"{self.coin}\n"
                    #     f"counter={continuous_count}/{total_count} (repeat rate={repeat_rate})\n"
                    #     f"size_price={size_price}\n"
                    #     f"size_dist={round(size_dist, 2)}%\n"
                    #     f"size_dir={'📈' if size_dir == 1 else '📉'}"
                    # )
                    self.alerts[size_price] = minute
            else:
                await asyncio.to_thread(change_size_status, self.coin, size_price, 4)
