import asyncio

async def retry(func, attempts, backoff):
    last_exc = None
    for attempt in range(attempts):
        try:
            return await func()
        except Exception as e:
            last_exc = e
            if attempt < attempts - 1:
                await asyncio.sleep(backoff / 1000)
    raise last_exc
