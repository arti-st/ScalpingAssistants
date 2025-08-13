import logging
import os
from bot_setup.bot_setup import bot


async def send_sevice_message(msg):
    try:
        await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
    except Exception as e:
        logging.error(e)
    finally:
        await bot.session.close()