import asyncio
from aiogram import types
from aiogram.filters import Command
from bot_setup.bot_setup import bot, bot_dispatcher
from mutual_variables.dictionaries import coin_updates, starting_parameters


@bot_dispatcher.message(Command(commands=("params")))
async def logged_user(message: types.Message):
    await message.answer(starting_parameters['params'], parse_mode='HTML')

@bot_dispatcher.message(Command(commands=("coins")))
async def logged_user(message: types.Message):
    await message.answer(starting_parameters['coins'], parse_mode='HTML')

@bot_dispatcher.message(Command(commands=("list")))
async def logged_user(message: types.Message):

    # Flatten all updates into one list
    all_updates = []
    for key, params in coin_updates.items():
        coin, price, gen_dir = key
        all_updates.append((coin, price, params))

    # Sort by numbers['upd_time'] descending
    all_updates.sort(key=lambda x: x[2]['upd_time'], reverse=True)

    msg_lines = []
    for coin, price, numbers in all_updates[:15]:
        msg_lines.append(
            f"{numbers['upd_time'].strftime('%H:%M'):^5}"
            f"{coin[:-4]:^8}"
            f"{price:^9}"
            f"{numbers['direction']} {numbers.get('dynamic', 'n/a')} "
            f"{numbers['cur_dist']:<4}% {f'({numbers['min_dist']}-{numbers['max_dist']})':<11} "
            f"{numbers['stable']} "
            f"${numbers['cur_size']:<3}K {f'({numbers['min_size']}-{numbers['max_size']})':<9}"
        )

    msg = "\n".join(msg_lines) if len(msg_lines) != 0 else 'No recent updates'

    import html
    text = f"<pre>{html.escape(msg)}</pre>"  # preserves spacing + monospace

    await message.answer(text, parse_mode='HTML')


async def poll():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot_dispatcher.start_polling(bot, polling_timeout=10, )

    except Exception as e:
        await asyncio.sleep(5)
        await poll()
