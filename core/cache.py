import time

class Cache:
    def __init__(self):
        self.store = {}
        self.expiry = {}

    def get(self, key):
        if key in self.expiry and time.time() < self.expiry[key]:
            return self.store.get(key)
        return None

    def set(self, key, value, ttl=300):
        self.store[key] = value
        self.expiry[key] = time.time() + ttl
