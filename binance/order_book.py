import logging
import os

import aiohttp

from bot_setup.bot_setup import bot
from mutual_variables.dictionaries import coins_to_ignore


async def order_book(symbol, market_type: str) -> list:
    perfect_depth_len = int(os.getenv('DEPTH_LEN', 500))
    min_depth_len = int(os.getenv('MIN_DEPTH_LEN', 100))

    futures_order_book = f"https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit={perfect_depth_len}"
    spot_order_book = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit={perfect_depth_len}"

    url = futures_order_book if market_type == "f" else spot_order_book

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            # print(f"Weight used by {symbol} for book: {response.headers.get('x-mbx-used-weight-1m')}")

            w = int(response.headers.get('x-mbx-used-weight-1m', 1000))
            if w > 2000:
                raise ConnectionError('Too close to the limit. 429')

            if response.status == 200:
                response_data = await response.json()

                if len(response_data['bids']) >= min_depth_len:
                    bids = response_data.get('bids')
                    asks = response_data.get('asks')
                    close = float(asks[0][0])

                    combined_list = [[float(item[0]), float(item[1])] for item in reversed(asks)]
                    for item in bids:
                        combined_list.append([float(item[0]), float(item[1])])
                    combined_list_sorted = sorted(combined_list, key=lambda x: x[1])

                    decimal_1 = len(str(combined_list[12][0]).split('.')[-1].rstrip('0'))
                    decimal_2 = len(str(combined_list[34][0]).split('.')[-1].rstrip('0'))
                    decimal_3 = len(str(combined_list[23][0]).split('.')[-1].rstrip('0'))
                    max_decimal = max([decimal_1, decimal_2, decimal_3])

                    if len(bids) == 0 or len(asks) == 0:
                        print(f'Missing bids/asks for {symbol}: bids={len(bids)}, asks={len(asks)}')
                        return []
                    else:
                        return [close, combined_list, combined_list_sorted, max_decimal]

                else:
                    print(f'Not full order book for {symbol}: bids={len(response_data['bids'])}, asks={len(response_data['asks'])}')
                    coins_to_ignore.add(symbol)
                    print(f'Added {symbol} to ignore list')
                    return []

            elif response.status == 429:
                msg = f"⛔️ {symbol} ({market_type}) LIMITS REACHED !!!! 429 CODE !!!!"
                await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
                logging.warning(msg)
                exit()


            else:
                response_data = await response.json()
                print(
                    f'Something went wrong while we requested depth for {symbol} '
                    f'({market_type}): status={response.status}, response={response_data}'
                )
                return []

# async def main():
#     while True:
#         await order_book("BTCUSDT", 199, 's')
#         await asyncio.sleep(3)
# import asyncio
# if __name__ == "__main__":
#     asyncio.run(main())
