import time

class CircuitBreaker:
    def __init__(self, failure_threshold, reset_timeout):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = {}
        self.last_failure = {}

    def allow(self, key):
        if key in self.failures:
            if self.failures[key] >= self.failure_threshold:
                if time.time() - self.last_failure[key] < self.reset_timeout:
                    return False
                self.failures[key] = 0
        return True

    def record_failure(self, key):
        self.failures[key] = self.failures.get(key, 0) + 1
        self.last_failure[key] = time.time()

    def record_success(self, key):
        if key in self.failures:
            self.failures[key] = max(0, self.failures[key] - 1)
