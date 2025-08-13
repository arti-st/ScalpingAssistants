import asyncio
import copy
import os
from datetime import datetime
from bot_setup.bot_setup import bot
from search_for_levels import coin_updates, terminator

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
        # optionally log
    # DO NOT close bot.session here — close it once on graceful shutdown



async def update_message_every_x_seconds(update_lock):
    last_update = None

    while not terminator.is_set():

        async with update_lock:
            if coin_updates != last_update and coin_updates:
                last_update = copy.deepcopy(coin_updates)

                # Flatten all updates into one list
                all_updates = []
                for coin, params in coin_updates.items():
                    for (price, direction), numbers in params.items():
                        all_updates.append((coin, price, direction, numbers))

                # Sort by numbers['upd_time'] descending
                all_updates.sort(key=lambda x: x[3]['upd_time'], reverse=True)

                msg_lines = []
                for coin, price, direction, numbers in all_updates:
                    msg_lines.append(
                        f"{numbers['upd_time'].strftime('%H:%M'):^5} "
                        f"{coin[:-4]:^9} "
                        f"{price:^10} "
                        f"{numbers['direction']:^2} "
                        f"{numbers['dynamic']:^3} "
                        f"{numbers['cur_dist']:<4}% "
                        f"{f'({numbers['min_dist']}-{numbers['max_dist']})':<13} "
                        f"${numbers['cur_size']:<3}K "
                        f"{f'({numbers['min_size']}-{numbers['max_size']})':<9} "
                    )

                msg = "\n".join(msg_lines)

                await sender(f"Live Updates at {datetime.now().strftime('%H:%M:%S')}:\n\n{msg}")
                print(f'{datetime.now()} dict updated. {len(msg_lines)} items')
            elif coin_updates == last_update:
                print(f'{datetime.now()} no new updates')
            elif not coin_updates:
                print(f'{datetime.now()} coin dict is empty')

        await asyncio.sleep(60)
