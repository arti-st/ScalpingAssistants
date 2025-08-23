import asyncio
import os
from datetime import datetime
from aiogram.types import FSInputFile
from binance.klines import get_klines
from bot_setup.bot_setup import bot
from mutual_variables.terminator import terminator
from main_logic.triangle_pattern_finder import triangle_found


async def search(coin):
    while not terminator.is_set():
        if datetime.now().second <= 2:
            for tf in ['1m', '5m', '15m', '30m', '1h']:
                the_klines = await get_klines(coin, tf, "f")

                if not the_klines or len(the_klines[0]) <= 150:
                    await asyncio.sleep(62)
                    continue

                res = await triangle_found(coin=coin, tf=tf, klines=the_klines)
                if res[0]:
                    img_path = res[2]
                    photo = FSInputFile(path=img_path)
                    await bot.send_photo(chat_id=os.getenv('CHAT_ID'), photo=photo, caption=coin)

            await asyncio.sleep(50)
        else:
            await asyncio.sleep(1)

    return