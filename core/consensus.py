import json
import time

class ConsensusTopK:
    def __init__(self, k):
        self.k = k
        self.scores = {}

    def merge_stream(self, files):
        now = time.time()
        for path in files:
            try:
                with open(path, "r") as f:
                    for line in f:
                        data = json.loads(line)
                        if data.get('expiry', 0) < now:
                            continue
                        key = f"{data['ip']}:{data['port']}"
                        self.scores[key] = self.scores.get(key, 0) + data['score']
            except:
                continue
        return self.result()

    def result(self):
        sorted_items = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for key, score in sorted_items[:self.k]:
            ip, port = key.split(":")
            results.append((ip, int(port), score))
        return results
