import os

import aiohttp
import asyncio


async def fetch_klines(session, url):
    async with session.get(url) as response:
        w = int(response.headers.get('x-mbx-used-weight-1m', 1000))
        if w > 2000:
            raise ConnectionError('Too close to the limit. 429')

        return await response.json() if response.status == 200 else None


async def get_trading_symbols(session, asset):
    """Отримує список торгових символів з futures та spot ринків для заданого активу"""
    try:
        excluded = os.getenv('EXCLUDED')
        excluded = list(excluded.replace(" ", "").split(','))

        # Отримуємо інформацію з обох ринків паралельно
        futures_info, spot_info = await asyncio.gather(
            fetch_klines(session, "https://fapi.binance.com/fapi/v1/exchangeInfo"),
            fetch_klines(session, "https://api.binance.com/api/v3/exchangeInfo")
        )

        if not futures_info or not spot_info:
            return {}

        # Створюємо set активних спот символів для швидкого пошуку
        spot_symbols = {
            d['symbol'] for d in spot_info['symbols']
            if d['quoteAsset'] == asset and d['status'] == 'TRADING'
        }

        # Фільтруємо ф'ючерси, залишаючи тільки ті, що мають спотовий відповідник
        spot_verified = os.getenv('SPOT_VERIFIED', 'off') == 'on'
        if spot_verified:
            trading_symbols = {
                d['symbol']: d['filters'][0]['tickSize']
                for d in futures_info['symbols']
                if (d['quoteAsset'] == asset and
                    d['symbol'] in spot_symbols and
                    d['symbol'] not in excluded)
            }
        else:
            trading_symbols = {
                d['symbol']: d['filters'][0]['tickSize']
                for d in futures_info['symbols']
                if (d['quoteAsset'] == asset and
                    d['symbol'] not in excluded)
            }

        return trading_symbols

    except Exception as e:
        print(f"⚠️ Error fetching trading symbols: {e}")
        return {}


async def calculate_pairs(session, pairs_dict, shared_results):
    request_limit_length = 99
    frame = '1m'
    for symbol, ts in pairs_dict.items():
        url = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={frame}&limit={request_limit_length}'
        try:
            binance_candle_data = await fetch_klines(session, url)
            if binance_candle_data:
                close = [float(i[4]) for i in binance_candle_data]
                high = [float(i[2]) for i in binance_candle_data]
                low = [float(i[3]) for i in binance_candle_data]

                x_atr_per = sum([(h - l) / (c / 100) for h, l, c in zip(high, low, close)]) / request_limit_length
                ts_percent = float(ts) / (close[-1] / 100)
                shared_results.append([symbol, ts_percent, x_atr_per])
        except Exception as e:
            print(f"⛔️ Error downloading klines for {symbol}: {e}")


async def split_dict(input_dict, num_parts):
    keys = list(input_dict)
    avg, remainder = divmod(len(keys), num_parts)
    return [{k: input_dict[k] for k in keys[i * avg + min(i, remainder):(i + 1) * avg + min(i + 1, remainder)]} for i in range(num_parts)]


async def get_pairs(asset):
    ticksize_filter = float(os.getenv("TICKSIZE_FILTER", 0.05))
    atr_filter = float(os.getenv("ATR_FILTER", 0.3))
    pairs_limit = int(os.getenv("PAIRS_LIMIT", 60))

    async with aiohttp.ClientSession() as session:
        # Отримуємо всі торгові символи через уніфіковану функцію
        ts_dict = await get_trading_symbols(session, asset)

        shared_results = []
        await asyncio.gather(*[calculate_pairs(session, chunk, shared_results) for chunk in await split_dict(ts_dict, 10)])

        sorted_res = sorted([r for r in shared_results if r[1] <= ticksize_filter and r[2] >= atr_filter], key=lambda x: x[2], reverse=True)
        result = [r[0] for r in sorted_res[:pairs_limit]]

        pairs_to_message = ''.join(f"{r[0]} - {round(r[2], 2)}%\n" for r in sorted_res[:pairs_limit])
        coins_verb = f"⚙️ Pairs got: {len(result)}/{len(sorted_res)}/{len(ts_dict)} (spot-validated).\n\n{pairs_to_message}"
        return result, coins_verb