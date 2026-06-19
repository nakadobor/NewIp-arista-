import json
import time
import os
from core.consensus import ConsensusTopK

def main():
    cfg = json.load(open("config.json"))

    merger = ConsensusTopK(cfg["keep_top"])
    files = [f"output/stream_{i}.log" for i in range(cfg["shard_total"])]

    result = merger.merge_stream(files)

    result = sorted(result, key=lambda x: x[2], reverse=True)

    result = result[:4000]

    now = time.time()

    os.makedirs("output", exist_ok=True)

    with open("global_best.txt", "w") as f:
        for ip, port, score in result:
            f.write(f"{ip}:{port}:{score}:{now + (7 * 24 * 3600)}\n")

    with open("output/global_best.txt", "w") as f:
        for ip, port, score in result:
            f.write(f"{ip}:{port}:{score}:{now + (7 * 24 * 3600)}\n")

if __name__ == "__main__":
    main()
