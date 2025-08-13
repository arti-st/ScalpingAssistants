import os
from aiogram import Bot

bot = Bot(token=os.getenv('BOT_TOKEN'))
sent_message_id = None
