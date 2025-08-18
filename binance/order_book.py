import logging
import os

import aiohttp

from bot_setup.bot_setup import bot


async def order_book(symbol, request_limit_length, market_type: str) -> list:
    futures_order_book = f"https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit={request_limit_length}"
    spot_order_book = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit={request_limit_length}"

    url = futures_order_book if market_type == "f" else spot_order_book

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            # print(f"Weight used by {symbol} for book: {response.headers.get('x-mbx-used-weight-1m')}")

            w = int(response.headers.get('x-mbx-used-weight-1m', 1000))
            if w > 2000:
                raise ConnectionError('Too close to the limit. 429')

            if response.status == 200:
                response_data = await response.json()

                if len(response_data['bids']) >= request_limit_length * 0.8:
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
                        # msg = (f"⛔️ bids=0 or asks=0 for depth data for {symbol} ({market_type}), status code {response.status}\n"
                        #        f"{url}")
                        # if market_type == 'f':
                            # await send_sevice_message(msg)
                            # logging.warning(msg)
                        return []
                    else:
                        return [close, combined_list, combined_list_sorted, max_decimal]

                else:
                    # msg = (f"⛔️ Not enough ({len(response_data['bids'])}/{request_limit_length}) depth data for {symbol} ({market_type}), status code {response.status}\n"
                    #        f"{url}")
                    # if market_type == 'f':
                        # await send_sevice_message(msg)
                        # logging.warning(msg)
                    return []

            elif response.status == 429:
                msg = f"⛔️ {symbol} ({market_type}) LIMITS REACHED !!!! 429 CODE !!!!"
                await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
                logging.warning(msg)
                exit()

            else:
                # msg = (f"⛔️ No depth data for {symbol} ({market_type}), status code {response.status}\n"
                #        f"{url}")
                # if market_type == 'f':
                    # await send_sevice_message(msg)
                    # logging.warning(msg)
                return []

# async def main():
#     while True:
#         await order_book("BTCUSDT", 199, 's')
#         await asyncio.sleep(3)
# import asyncio
# if __name__ == "__main__":
#     asyncio.run(main())
