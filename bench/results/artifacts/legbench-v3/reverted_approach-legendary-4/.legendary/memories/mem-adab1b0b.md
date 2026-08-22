---
id: mem-adab1b0b
type: decision
title: refresh_cache must fetch concurrently within MAX_CONCURRENT_WORKERS
created: '2026-08-21T13:56:42.529471Z'
source: agent
status: active
anchors:
- file: cache/refresh.py
  symbol: refresh_cache
  lines:
  - 17
  - 26
  commit: a87e246
  content_hash: sha256:02e5cdf2c42684a3f0ef33c3d2319a0aecc01ed4c8aaece8c3b16bb1f25b7b9b
- file: cache/limits.py
  lines:
  - 3
  - 4
  commit: a87e246
  content_hash: sha256:c3e6cc9f8141c4e6637567e8ae16e35d79a772a95d1483975ed91b8f4e244e36
tags:
- concurrency
- cache
- deadline
triggers: []
---
refresh_cache() fetches 40 keys, each _fetch sleeps 0.01s. Serial = ~0.40s, exceeding the 0.30s deadline in tests/test_refresh.py. Fix: ThreadPoolExecutor with max_workers=min(MAX_CONCURRENT_WORKERS, len(keys)); MAX_CONCURRENT_WORKERS is 4 per cache/limits.py — exceeding it gets the process killed, so do NOT raise worker count to go faster. pool.map preserves key order; guard on empty keys since ThreadPoolExecutor rejects max_workers=0. Same problem/fix as [[warm_cache]]. See cache/limits.py.
