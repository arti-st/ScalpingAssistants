import asyncio
import os
from datetime import datetime
from new_version.bot_setup.bot_setup import bot
from new_version.search_for_levels import coin_updates

sent_message_id = None

async def sender(msg):
    """Send a new message, deleting the old one if it exists."""
    global sent_message_id
    try:
        # If a previous message exists, delete it first
        if sent_message_id:
            await bot.delete_message(chat_id=os.getenv('CHAT_ID'), message_id=sent_message_id)

        # Send the new message and store the message_id
        message = await bot.send_message(chat_id=os.getenv('CHAT_ID'), text=msg)
        sent_message_id = message.message_id
    finally:
        await bot.session.close()


async def update_message_every_5_seconds(update_lock):
    """Update the message every 5 seconds with the latest coin_updates."""
    last_update = None  # Variable to track when the updates have changed

    while True:
        # Lock the dictionary to ensure safe access to coin_updates
        async with update_lock:
            if coin_updates != last_update and coin_updates and datetime.now().hour > 7:  # If the updates have changed
                last_update = coin_updates.copy()  # Store the new updates

                # Prepare the message to display
                all_updates = "\n".join([u for u in coin_updates.values()])
                await sender(f"Live Updates at {datetime.now().strftime('%H:%M:%S')}:\n\n{all_updates}")

        await asyncio.sleep(5)
