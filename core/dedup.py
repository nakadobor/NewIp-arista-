import time

class DedupStore:
    def __init__(self):
        self.store = {}

    def seen(self, ip):
        now = time.time()
        if ip in self.store:
            if now - self.store[ip] < 48 * 3600:
                return True
        self.store[ip] = now
        return False

    def cleanup(self):
        now = time.time()
        self.store = {
            k: v for k, v in self.store.items()
            if now - v < 48 * 3600
        }
