import asyncio

coin_updates = {}  # Shared updates storage
confirmed_size_found = {'found': False}
starting_parameters = {'params': None, 'coins': None}

update_lock = asyncio.Lock()
