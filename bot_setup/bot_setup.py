import os
from aiogram import Bot, Dispatcher

bot = Bot(token=os.getenv('BOT_TOKEN'))
sent_message_id = None

bot_dispatcher = Dispatcher()