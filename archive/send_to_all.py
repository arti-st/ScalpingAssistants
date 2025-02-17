import telebot
import os
import chat_ids
from dotenv import load_dotenv
load_dotenv()

PUBLIC_TELEGRAM_TOKEN = os.getenv('PUBLIC_TELEGRAM_TOKEN')
public_bot = telebot.TeleBot(PUBLIC_TELEGRAM_TOKEN)
disclaimer = '<i>Торгівля криптовалютами має високі ризики та може призвести до значних фінансових втрат! Уся відповідальність лежить на користувачеві бота.</i>'

# Load existing chat IDs
existed_chat_ids = set(chat_ids.get_existed_chat_ids())


def work_is_started():
    for chat_id in existed_chat_ids:
        try:
            msg = 'Доброго ранку! Бот запущено. Очікуй на повідомлення.'
            public_bot.send_message(chat_id, msg)
        except Exception as e:
            print(f"Failed to send message to {chat_id}: {e}")


def work_is_ended():
    for chat_id in existed_chat_ids:
        try:
            msg = 'На сьогодні робота завершена. Бот зупинено. Надобраніч 🥱'
            public_bot.send_message(chat_id, msg)
        except Exception as e:
            print(f"Failed to send message to {chat_id}: {e}")


def maintance():
    for chat_id in existed_chat_ids:
        try:
            msg = 'Технічні роботи на сервері...'
            public_bot.send_message(chat_id, msg)
            pic = open(f'tech_start.webm', 'rb')
            public_bot.send_sticker(chat_id=chat_id, sticker=pic)
        except Exception as e:
            print(f"Failed to send message to {chat_id}: {e}")


def maintance_end():
    for chat_id in existed_chat_ids:
        try:
            msg = 'Налаштування завершені. Запускаємось...'
            public_bot.send_message(chat_id, msg)
            pic = open(f'tech_end.webm', 'rb')
            public_bot.send_sticker(chat_id=chat_id, sticker=pic)
        except Exception as e:
            print(f"Failed to send message to {chat_id}: {e}")


def send_message_to_all():
    for chat_id in existed_chat_ids:
        try:
            msg = "Бот запущено."
            public_bot.send_message(chat_id, msg)
        except Exception as e:
            print(f"Failed to send message to {chat_id}: {e}")


if __name__ == '__main__':
    # pass
    # work_is_started()
    # work_is_ended()
    # maintance()
    # maintance_end()
    send_message_to_all()
