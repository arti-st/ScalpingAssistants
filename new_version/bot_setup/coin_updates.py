import asyncio

coin_updates = {}  # Shared updates storage
update_lock = asyncio.Lock()  # Lock to prevent race conditions