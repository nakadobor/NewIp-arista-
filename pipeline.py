import asyncio
import os
import random
import sys
import time

from downloader import Downloader
from exporter import Exporter
from core.cidr_stream import CIDRStream
from core.tcp_worker import TCPWorker
from core.https_worker import HTTPSWorker
from core.https_cache import HTTPSCache
from core.topk import TopK
from core.checkpoint import Checkpoint
from core.rate_limiter import RateLimiter
from core.cache import Cache
from core.logger import get_logger, Metrics
from core.backpressure import Backpressure
from core.adaptive import AdaptiveWorkers
from core.circuit_breaker import CircuitBreaker
from core.dedup import DedupStore

async def pipeline(cfg):
    logger = get_logger("v18.2")
    metrics = Metrics()

    shard_id = int(os.getenv("SHARD_ID", "0"))

    print(f"[DEBUG] ===== STARTING SHARD {shard_id} =====")
    print(f"[DEBUG] Timeout: {cfg['timeout']}s")
    print(f"[DEBUG] Ports: {cfg['ports']}")
    print(f"[DEBUG] SNI Hosts: {cfg['sni_hosts']}")

    ckpt = Checkpoint(shard_id, cfg["checkpoint_every"])
    cache = Cache()
    https_cache = HTTPSCache()
    dedup = DedupStore()

    rate = RateLimiter(cfg["rate_limit_per_subnet"])

    cb = CircuitBreaker(
        cfg["circuit_breaker_failures"],
        cfg["circuit_breaker_reset_sec"]
    )

    print("[DEBUG] Downloading sources...")
    data = await Downloader.fetch_all(cfg["sources"])

    cidrs = []
    total_sources = 0
    for url, ips in data.items():
        if ips:
            total_sources += 1
            print(f"[DEBUG] Source {url.split('/')[-1]}: {len(ips)} CIDRs")
            cidrs.extend(ips)
        else:
            print(f"[WARN] Source {url.split('/')[-1]}: EMPTY or failed")

    print(f"[DEBUG] Total CIDRs collected: {len(cidrs)} from {total_sources} sources")

    if not cidrs:
        print("[ERROR] No CIDRs found from any source!")
        sys.exit(1)

    stream = CIDRStream(cidrs, cfg["sample_per_source"])

    ip_count = 0
    for _ in stream.stream():
        ip_count += 1
        if ip_count >= 100:
            break
    print(f"[DEBUG] Sample IP generation test: first 100 IPs generated successfully")

    stream = CIDRStream(cidrs, cfg["sample_per_source"])

    q = asyncio.Queue(maxsize=cfg["queue_size"])
    back = Backpressure(q, 0.75)

    tcp = TCPWorker(cfg["timeout"], cb, cache)
    https = HTTPSWorker(cfg["timeout"], cb, cache, https_cache)
    topk = TopK(cfg["keep_top"])

    quality_total = 0
    quality_ok = 0
    workers = set()
    processed_ips = 0

    async def producer():
        nonlocal ip_count
        i = ckpt.load()
        produced = 0

        for ip in stream.stream():
            i += 1
            produced += 1
            metrics.inc("produced")

            if produced % 1000 == 0:
                print(f"[DEBUG] Produced {produced} IPs so far")

            if dedup.seen(ip):
                continue

            subnet = ".".join(ip.split(".")[:3])

            if not rate.allow(subnet):
                metrics.inc("fail")
                continue

            await back.wait()
            await q.put((i, ip))

            if i % cfg["checkpoint_every"] == 0:
                ckpt.save(i)

            if cfg.get("random_delay_ms"):
                await asyncio.sleep(random.uniform(0, cfg["random_delay_ms"] / 1000))

        print(f"[DEBUG] Producer finished. Total produced: {produced}")

    async def worker():
        nonlocal quality_total, quality_ok, processed_ips

        while True:
            i, ip = await q.get()
            try:
                processed_ips += 1
                metrics.inc("consumed")

                if processed_ips % 100 == 0:
                    print(f"[DEBUG] Processed {processed_ips} IPs, found {len(topk.heap)} valid")

                tcp_res = await tcp.probe(ip, cfg["ports"])

                if not tcp_res:
                    if processed_ips % 500 == 0:
                        print(f"[DEBUG] No TCP response from {ip}")
                    continue

                tcp_res = sorted(tcp_res, key=lambda x: x[2])
                top_half = tcp_res[:max(1, len(tcp_res)//2)]

                found = False
                for ip2, port, tcp_latency in top_half:
                    for sni in cfg["sni_hosts"]:
                        r = await https.test(ip2, port, sni)
                        if r:
                            quality_ok += 1
                            topk.push(r)
                            print(f"[FOUND] {ip2}:{port} latency: {r[2]:.2f}ms")
                            found = True
                            break
                    if found:
                        break
                    quality_total += 1
            finally:
                q.task_done()

    async def worker_manager():
        adaptive = AdaptiveWorkers(
            cfg["worker_pool_min"],
            cfg["worker_pool_max"],
            q
        )

        while True:
            desired = adaptive.compute()

            while len(workers) < desired:
                t = asyncio.create_task(worker())
                workers.add(t)

            while len(workers) > desired:
                t = workers.pop()
                t.cancel()

            await asyncio.sleep(1)

    async def checkpoint_loop():
        while True:
            dedup.cleanup()
            await asyncio.sleep(300)

    async def monitor():
        while True:
            await asyncio.sleep(5)
            print(f"[MONITOR] Queue: {q.qsize()}, Workers: {len(workers)}, "
                  f"TopK: {len(topk.heap)}, Quality: {quality_ok}/{quality_total}, "
                  f"Processed: {processed_ips}")

    prod = asyncio.create_task(producer())
    manager = asyncio.create_task(worker_manager())
    ckpt_task = asyncio.create_task(checkpoint_loop())
    monitor_task = asyncio.create_task(monitor())

    await prod
    await q.join()

    for w in workers:
        w.cancel()

    manager.cancel()
    ckpt_task.cancel()
    monitor_task.cancel()

    await asyncio.gather(*workers, return_exceptions=True)
    await asyncio.gather(manager, ckpt_task, monitor_task, return_exceptions=True)

    print(f"[RESULT] Final: Found {len(topk.heap)} IPs, Quality: {quality_ok}/{quality_total}")
    
    if len(topk.heap) == 0:
        print("[ERROR] No valid IPs found! Creating empty file to debug.")

    Exporter.save(topk.items(), shard_id)

    logger.info({
        "quality_score": quality_ok / max(1, quality_total),
        "buffer": 0
    })
