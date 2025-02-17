# telegram_bot.py
import telebot
import os
import chat_ids
from dotenv import load_dotenv
load_dotenv()

PERSONAL_TELEGRAM_TOKEN = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(PERSONAL_TELEGRAM_TOKEN)
personal_id = int(os.getenv('PERSONAL_ID'))

PUBLIC_TELEGRAM_TOKEN = os.getenv('PUBLIC_TELEGRAM_TOKEN')
bot_all = telebot.TeleBot(PUBLIC_TELEGRAM_TOKEN)
disclaimer = '<i>Торгівля криптовалютами має високі ризики та може призвести до значних фінансових втрат! Уся відповідальність лежить на користувачеві бота.</i>'

# Load existing chat IDs
existed_chat_ids = set(chat_ids.get_existed_chat_ids())

@bot_all.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id not in existed_chat_ids:
        chat_ids.save_new_chat_id(chat_id)
    msg = (
f"""🇺🇦 Слава Україні!

Отож ти приєднався(-лась) до розсилки.
Поточна сесія аналізу вже активна, тому просто очікуй на повідомлення.

Щоб дізнатись як працює бот - тицяй /about_bot
Підтримати автора - тицяй /donate

{disclaimer}
""")
    bot_all.send_message(chat_id, msg, parse_mode="HTML")
    personal_bot.send_message(personal_id, f'🙂 Користувач {chat_id} натиснув на start')

@bot_all.message_handler(commands=['about_bot'])
def send_about(message):
    chat_id = message.chat.id
    if chat_id not in existed_chat_ids:
        chat_ids.save_new_chat_id(chat_id)

    link = "https://docs.google.com/document/d/14brzteeFj9rdpm55vImldH1pAjrUnvJMK4kpoYmDR88/edit?usp=sharing"
    msg = f"<a href='{link}'>Повна інформація</a>"

    bot_all.send_message(chat_id, msg, parse_mode="HTML")
    personal_bot.send_message(personal_id, f'🙂 Користувач {chat_id} натиснув на about_bot')

@bot_all.message_handler(commands=['donate'])
def send_donate(message):
    chat_id = message.chat.id
    if chat_id not in existed_chat_ids:
        chat_ids.save_new_chat_id(chat_id)

    msg = f"""
USDT (TRC20)
<code>TWFr2azmpeC6joRc71MmmgegqF7hFu8yPb</code>   

BNB (SmartChain)
<code>0xB34D51c69eA573437ece72B3799b141C82B09647</code>

BTC
<code>bc1qmkn5npw3l0d8l6gfuu28nhcv28gtm65edgke9g</code>

ETH
<code>0xB34D51c69eA573437ece72B3799b141C82B09647</code>
    """

    bot_all.send_message(message.chat.id, msg, parse_mode='HTML')
    personal_bot.send_message(personal_id, f'🙂 Користувач {chat_id} натиснув на donate')

@bot_all.message_handler(commands=['status'])
def send_status(message):
    chat_id = message.chat.id
    if chat_id not in existed_chat_ids:
        chat_ids.save_new_chat_id(chat_id)

    msg1 = f"""
🟢 Сервер запущено, бот працює.    

Востаннє бот оновлював список монет о {os.getenv('RELOAD_TIMESTAMP')}.

Від Binance було отримано {os.getenv('BINANCE_SENT')} монет.

Відфільтровано {os.getenv('FILTERED')} з них за параметрами:
розмір tick до 0.05%, сер.ATR на м1 від 0.20%

{os.getenv('IN_WORK')}/{os.getenv('FILTERED')} зараз в роботі.
<i>*максимальна кількість монет які може опрацьовувати бот одночасно я обмежив до 30 штук (по топ ATR), для ефективної роботи сервера.</i> 

Частота проходу по кожному з них ~1 хвилина.
    """
    msg2 = '🔴 Бот тимчасово не працює. Очікуй на запуск'
    msg = msg1 if os.getenv('BOT_STATE') == "run" else msg2

    bot_all.send_message(message.chat.id, msg, parse_mode="HTML")
    personal_bot.send_message(personal_id, f'🙂 Користувач {chat_id} натиснув на status')

@bot_all.message_handler(commands=['pause'])
def bot_pause(message):
    chat_id = message.chat.id
    if chat_id == personal_id:
        os.environ['BOT_STATE'] = "pause"
        personal_bot.send_message(personal_id, f'⏸ BOT_STATE = pause')

@bot_all.message_handler(commands=['run'])
def bot_pause(message):
    chat_id = message.chat.id
    if chat_id == personal_id:
        os.environ['BOT_STATE'] = "run"
        personal_bot.send_message(personal_id, f'▶️ BOT_STATE = run')

@bot_all.message_handler(func=lambda message: True)
def handle_message(message):
    bot_all.send_message(message.chat.id, "Повідомлень я не розумію, сорян 🤷🏻‍♂️")
    chat_id = message.chat.id
    pic = open(f'pig.webm', 'rb')
    bot_all.send_sticker(chat_id, pic)
    personal_bot.send_message(personal_id, f'🙂 Користувач {chat_id} шось написав і отримав свиню')


def start_bot():
    bot_all.infinity_polling()
