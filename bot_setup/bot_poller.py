import asyncio
from aiogram import types
from aiogram.filters import Command
from bot_setup.bot_setup import bot, bot_dispatcher
from mutual_variables.dictionaries import coin_updates, starting_parameters


@bot_dispatcher.message(Command(commands=("params")))
async def logged_user(message: types.Message):
    p = starting_parameters['params']
    msg = 'Params is not ready yet!' if p is None else p
    # Remove the html import and pre tags
    text = f"`\n{msg}\n`"
    await message.answer(text, parse_mode='MarkdownV2')

@bot_dispatcher.message(Command(commands=("coins")))
async def logged_user(message: types.Message):
    c = starting_parameters['coins']
    msg = 'Coins is not ready yet!' if c is None else c
    # Remove the html import and pre tags
    text = f"`\n{msg}\n`"
    await message.answer(text, parse_mode='MarkdownV2')

@bot_dispatcher.message(Command(commands=("list")))
async def logged_user(message: types.Message):

    # Flatten all updates into one list
    all_updates = []
    for key, params in coin_updates.items():
        coin, price, direction = key
        all_updates.append((coin, price, direction, params))

    # Sort by numbers['upd_time'] descending
    all_updates.sort(key=lambda x: x[3]['updated'], reverse=True)

    msg_lines = []
    for coin, price, direction, numbers in all_updates[:20]:
        dir_veb = "🔼" if direction == 'up' else "🔽"
        msg_lines.append(
            f"{numbers['updated'].strftime('%H:%M'):^5}"
            f"{coin[:-4]:^8} "
            f"{numbers['counter']:<2} {numbers['signal']}"
            f"{price:^9}"
            f"{dir_veb} {numbers.get('distance_color', 'n/a')} "
            f"{numbers['distance_value']:<5}% {f'{numbers['distance_min']}-{numbers['distance_max']}':<9} "
            f"{numbers.get('size_color', 'n/a')} "
            f"${numbers['size_value']:<3}K {f'{numbers['size_min']}-{numbers['size_max']}':<7}"
        )

    msg = "\n".join(msg_lines) if len(msg_lines) != 0 else 'No recent updates'

    # Remove the html import and pre tags
    text = f"```\n{msg}\n```"
    await message.answer(text, parse_mode='MarkdownV2')


async def poll():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot_dispatcher.start_polling(bot, polling_timeout=10, )

    except Exception as e:
        await asyncio.sleep(5)
        await poll()
