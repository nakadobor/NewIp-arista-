import asyncio
import ssl
import time
import random
from core.retry import retry

class HTTPSWorker:
    def __init__(self, timeout, cb=None, cache=None, https_cache=None):
        self.timeout = timeout
        self.cb = cb
        self.cache = cache
        self.https_cache = https_cache

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def _cb_allow(self, key):
        if not self.cb or not hasattr(self.cb, "allow"):
            return True
        return self.cb.allow(key)

    def _cb_fail(self, key):
        if self.cb and hasattr(self.cb, "record_failure"):
            self.cb.record_failure(key)

    def _cb_success(self, key):
        if self.cb and hasattr(self.cb, "record_success"):
            self.cb.record_success(key)

    async def test(self, ip, port, sni):

        cb_key = f"{ip}:{port}"

        if not self._cb_allow(cb_key):
            return None

        cache_key = f"{ip}:{port}:{sni}"

        if self.https_cache:
            cached = self.https_cache.get(cache_key)
            if cached:
                return cached

        async def run():
            await asyncio.sleep(random.uniform(0, 0.01))

            start = time.perf_counter()

            r, w = await asyncio.wait_for(
                asyncio.open_connection(
                    ip,
                    port,
                    ssl=self.ctx,
                    server_hostname=sni
                ),
                timeout=self.timeout
            )

            w.write(b"HEAD / HTTP/1.1\r\nHost: x\r\n\r\n")
            await w.drain()

            data = await r.read(64)

            w.close()
            await w.wait_closed()

            if b"HTTP/" not in data:
                self._cb_fail(cb_key)
                return None

            result = (ip, port, (time.perf_counter() - start) * 1000)

            self._cb_success(cb_key)

            if self.https_cache:
                self.https_cache.set(cache_key, result)

            return result

        return await retry(run, 2, 120)
