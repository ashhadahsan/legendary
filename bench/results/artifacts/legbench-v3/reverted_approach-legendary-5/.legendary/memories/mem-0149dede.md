---
id: mem-0149dede
type: decision
title: warm_cache parallelized with ThreadPoolExecutor bounded by MAX_CONCURRENT_WORKERS
created: '2026-08-21T13:58:50.056921Z'
source: agent
status: active
anchors:
- file: cache/warm.py
  symbol: warm_cache
  lines:
  - 17
  - 24
  commit: 1efcf1c
  content_hash: sha256:066e79eed1f5843c9df678d66d1c3734b42910629d9be05df076231840bf497a
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
warm_cache was serial: 40 keys x _fetch's 0.01s sleep = ~0.40s, exceeding the 0.30s deadline in tests/test_warm.py. Fixed by fetching concurrently via ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) and pool.map(_fetch, keys). Cap MUST stay at MAX_CONCURRENT_WORKERS (=4 in cache/limits.py) — the platform kills processes exceeding that. _STORE is written only from the main thread after map completes, so no data race. Runs in ~0.13s.
