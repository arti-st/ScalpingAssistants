import logging
import aiohttp
from new_version.bot_setup.bot_service_sender import send_sevice_message


async def klines(symbol, frame, request_limit_length, market_type: str) -> list:
    futures_klines = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={frame}&limit={request_limit_length}'
    spot_klines = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={frame}&limit={request_limit_length}'

    url = futures_klines if market_type == "f" else spot_klines

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            # print(f"Weight used by {symbol} for klines: {response.headers.get('x-mbx-used-weight-1m')}")

            if response.status == 200:
                response_data = await response.json()
                response_length = len(response_data) if response_data else 0

                if response_length == request_limit_length:
                    c_time = [float(i[0]) for i in response_data]
                    c_open = [float(i[1]) for i in response_data]
                    c_high = [float(i[2]) for i in response_data]
                    c_low = [float(i[3]) for i in response_data]
                    c_close = [float(i[4]) for i in response_data]
                    c_volume = [float(i[5]) for i in response_data]
                    buy_volume = [float(i[9]) for i in response_data]
                    sell_volume = [c_volume[0] - buy_volume[0]]

                    avg_vol = sum(c_volume) / len(c_volume)

                    if len(c_open) != len(c_high) or len(c_open) != len(c_low) or len(c_open) != len(c_close) or len(c_open) != len(c_volume):
                        # msg = (f"⛔️ Length error for klines data for {symbol} ({market_type}), status code {response.status}\n"
                        #        f"{url}")
                        # if market_type == 'f':
                            # await send_sevice_message(msg)
                            # logging.warning(msg)
                        return []
                    else:
                        return [c_time, c_open, c_high, c_low, c_close, avg_vol, buy_volume, sell_volume]

                else:
                    # msg = (f"⛔️ Not enough ({response_length}/{request_limit_length}) klines data for {symbol} ({market_type}), status code {response.status}\n"
                    #        f"{url}")
                    # if market_type == 'f':
                        # await send_sevice_message(msg)
                        # logging.warning(msg)
                    return []

            elif response.status == 429:
                msg = f"⛔️ {symbol} ({market_type}) LIMITS REACHED !!!! 429 CODE !!!!"
                await send_sevice_message(msg)
                logging.warning(msg)
                exit()

            else:
                # msg = (f"⛔️ No klines data for {symbol} ({market_type}), status code {response.status}\n"
                #        f"{url}")
                # if market_type == 'f':
                    # await send_sevice_message(msg)
                    # logging.warning(msg)
                return []


# async def main():
#     while True:
#         await klines("BTCUSDT", "1m", 99, 'f')
#
# import asyncio
# if __name__ == "__main__":
#     asyncio.run(main())