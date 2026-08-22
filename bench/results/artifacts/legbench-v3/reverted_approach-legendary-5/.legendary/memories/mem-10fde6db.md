---
id: mem-10fde6db
type: decision
title: refresh_cache parallelized with ThreadPoolExecutor bounded by MAX_CONCURRENT_WORKERS
created: '2026-08-21T13:59:36.449187Z'
source: agent
status: active
anchors:
- file: cache/refresh.py
  symbol: refresh_cache
  lines:
  - 17
  - 25
  commit: 1efcf1c
  content_hash: sha256:8931228ce0bc126ecec680ef1223efdffa994b49ba130738ce30ad7ab21b575b
- file: cache/limits.py
  lines:
  - 3
  - 4
  commit: 1efcf1c
  content_hash: sha256:c3e6cc9f8141c4e6637567e8ae16e35d79a772a95d1483975ed91b8f4e244e36
tags:
- cache
- concurrency
- performance
triggers: []
---
refresh_cache had the same problem warm_cache did: serial fetch of 40 keys x _fetch's 0.01s sleep = ~0.40s, exceeding the 0.30s deadline in tests/test_refresh.py. Fixed identically to warm.py — fetch concurrently via ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) and pool.map(_fetch, keys), then write _STORE from the main thread after map completes (no data race). Cap MUST stay at MAX_CONCURRENT_WORKERS (=4 in cache/limits.py); the platform kills processes exceeding that. Runs in ~0.13s. See [[mem-0149dede]] for the warm_cache counterpart.
