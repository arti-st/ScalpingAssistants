import asyncio
import copy
import os
from datetime import datetime
from bot_setup.bot_setup import bot
from mutual_variables.dictionaries import coin_updates, confirmed_size_found
from mutual_variables.terminator import terminator

sent_message_id = None

async def sender(msg):
    """Send a new message, deleting the old one if it exists."""
    global sent_message_id
    try:
        if sent_message_id:
            await bot.delete_message(chat_id=os.getenv('CHAT_ID'), message_id=sent_message_id)

        import html
        text = f"<pre>{html.escape(msg)}</pre>"   # preserves spacing + monospace

        message = await bot.send_message(
            chat_id=os.getenv('CHAT_ID'),
            text=text,
            parse_mode='HTML'
        )
        sent_message_id = message.message_id

    except Exception as e:
        print("send error:", e)


async def update_message_every_x_seconds(update_lock):
    last_update = None

    while not terminator.is_set():
        if 15 < datetime.now().second < 30:

            async with update_lock:
                if coin_updates != last_update and coin_updates and confirmed_size_found['found'] == True:
                    last_update = copy.deepcopy(coin_updates)

                    # Flatten all updates into one list
                    all_updates = []
                    for coin, params in coin_updates.items():
                        for (price, direction), numbers in params.items():
                            all_updates.append((coin, price, direction, numbers))

                    # Sort by numbers['upd_time'] descending
                    all_updates.sort(key=lambda x: x[3]['upd_time'], reverse=True)

                    filtered_updates = []
                    coin_seen = {}
                    for i in all_updates:
                        coin = i[0]
                        if coin_seen.get(coin, 0) < 5:  # strictly less than 5
                            filtered_updates.append(i)
                            coin_seen[coin] = coin_seen.get(coin, 0) + 1

                    msg_lines = []
                    for coin, price, direction, numbers in filtered_updates:
                        msg_lines.append(
                            f"{numbers['upd_time'].strftime('%H:%M'):^5}"
                            f"{coin[:-4]:^8}"
                            f"{price:^9}"
                            f"{numbers['direction']} {numbers.get('dynamic', 'n/a')} "
                            f"{numbers['cur_dist']:<4}% {f'({numbers['min_dist']}-{numbers['max_dist']})':<11}"
                            f"{numbers['stable']}"
                            f"${numbers['cur_size']:<3}K {f'({numbers['min_size']}-{numbers['max_size']})':<9}"
                        )

                    msg = "\n".join(msg_lines)

                    await sender(f"Live Updates at {datetime.now().strftime('%H:%M:%S')}:\n\n{msg}")
                    print(f'{datetime.now()} dict updated. {len(msg_lines)} items')

                    confirmed_size_found['found'] = False
                elif coin_updates == last_update:
                    print(f'{datetime.now()} no new updates')
                elif not coin_updates:
                    print(f'{datetime.now()} coin dict is empty')
                elif confirmed_size_found['found'] != True:
                    print(f'{datetime.now()} no new confirmed size')
            await asyncio.sleep(20)

        await asyncio.sleep(1)

