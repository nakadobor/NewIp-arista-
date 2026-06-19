import os
import json
import time

class Exporter:
    @staticmethod
    def save(items, shard_id):
        os.makedirs("output", exist_ok=True)
        path = f"output/stream_{shard_id}.log"
        now = time.time()
        
        print(f"[EXPORT] Saving {len(items)} items to {path}")
        
        with open(path, "w") as f:
            if not items:
                f.write(json.dumps({"error": "no_items", "shard": shard_id, "time": now}) + "\n")
            else:
                for ip, port, score in items:
                    f.write(json.dumps({
                        "ip": ip, 
                        "port": port, 
                        "score": score,
                        "expiry": now + (7 * 24 * 3600)
                    }) + "\n")
        
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"[EXPORT] File created: {path} ({size} bytes)")
        else:
            print(f"[ERROR] Failed to create {path}")
