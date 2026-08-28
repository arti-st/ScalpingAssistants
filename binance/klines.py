import logging
import os

import aiohttp

from bot_setup.bot_setup import bot
from mutual_variables.dictionaries import coins_to_ignore


async def get_klines(symbol, frame, market_type: str) -> tuple:
    perfect_klines_len = int(os.getenv('KLINES_LEN', 240))
    min_klines_len = int(os.getenv('MIN_KLINES_LEN', 60))

    futures_klines = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={frame}&limit={perfect_klines_len}'
    spot_klines = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={frame}&limit={perfect_klines_len}'

    url = futures_klines if market_type == "f" else spot_klines

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            # print(f"Weight used by {symbol} for klines: {response.headers.get('x-mbx-used-weight-1m')}")

            if response.status == 200:
                response_data = await response.json()
                response_length = len(response_data) if response_data else 0

                w = int(response.headers.get('x-mbx-used-weight-1m', 1000))
                if w > 2000:
                    raise ConnectionError('Too close to the limit. 429')

                if response_length >= min_klines_len:
                    c_time = [float(i[0]) for i in response_data]
                    c_open = [float(i[1]) for i in response_data]
                    c_high = [float(i[2]) for i in response_data]
                    c_low = [float(i[3]) for i in response_data]
                    c_close = [float(i[4]) for i in response_data]
                    c_volume = [float(i[5]) for i in response_data]
                    buy_volume = [float(i[9]) for i in response_data]

                    sell_volume = [t - b for t, b in zip(c_volume, buy_volume)]
                    delta_volume = [b - s for b, s in zip(buy_volume, sell_volume)]

                    cumulative_delta = []
                    cumsum = 0
                    for d in delta_volume:
                        cumsum += d
                        cumulative_delta.append(cumsum)

                    sma_len = 20
                    sma20 = []
                    for i in range(len(cumulative_delta)):
                        if i < (sma_len - 1):
                            sma20.append(None)  # not enough data for SMA20
                        else:
                            window = cumulative_delta[i - (sma_len - 1):i + 1]
                            sma = sum(window) / sma_len
                            sma20.append(sma)

                    avg_vol = sum(c_volume) / len(c_volume)

                    if len(c_open) != len(c_high) or len(c_open) != len(c_low) or len(c_open) != len(c_close) or len(c_open) != len(c_volume):
                        print(f'Broken klines for {symbol}: len(c_open)={len(c_open)}, len(c_volume)={len(c_volume)}\n{url}')
                        return ()
                    else:
                        return c_time, c_open, c_high, c_low, c_close, avg_vol, buy_volume, sell_volume, cumulative_delta, sma20

                else:
                    print(f'Not full klines for {symbol}: {response_length}/{int(os.getenv('MIN_KLINES_LEN', 150))}\n{url}')
                    coins_to_ignore.add(symbol)
                    return ()

            elif response.status == 429:
                msg = f"⛔️ {symbol} ({market_type}) LIMITS REACHED !!!! 429 CODE !!!!"
                await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
                logging.warning(msg)
                exit()
            else:
                print(f'Something went wrong while we requested klines for {symbol}:\n{response}\n{url}')
                return ()

# async def main():
#     while True:
#         await klines("BTCUSDT", "1m", 99, 'f')
#
# import asyncio
# if __name__ == "__main__":
#     asyncio.run(main())
