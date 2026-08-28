import asyncio

coin_updates = {}  # Shared updates storage
coins_to_ignore = set()
confirmed_size_found = {'found': False}
starting_parameters = {'params': None, 'coins': None, 'upd_time': None}

update_lock = asyncio.Lock()
