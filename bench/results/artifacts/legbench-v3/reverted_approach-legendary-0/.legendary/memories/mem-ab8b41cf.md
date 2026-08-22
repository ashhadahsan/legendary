---
id: mem-ab8b41cf
type: decision
title: warm_cache must fetch concurrently within MAX_CONCURRENT_WORKERS
created: '2026-08-21T13:44:58.089359Z'
source: agent
status: active
anchors:
- file: cache/warm.py
  symbol: warm_cache
  lines:
  - 17
  - 27
  commit: 9c01ba1
  content_hash: sha256:ab4fc4e6a7f38b223beec4e29c69c60126e593b2737e0f29e032618d9bfa38ad
- file: cache/limits.py
  lines:
  - 3
  - 4
  commit: 9c01ba1
  content_hash: sha256:c3e6cc9f8141c4e6637567e8ae16e35d79a772a95d1483975ed91b8f4e244e36
tags:
- cache
- concurrency
- performance
triggers:
- test_warm_cache_completes_before_deadline
- took 0.40s, deadline is 0.30s
---
`warm_cache` originally fetched keys serially. With 40 keys × 0.01s `_fetch` sleep = 0.4s, it blew the 0.30s deadline in test_warm_cache_completes_before_deadline. Fix: use ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) and executor.map over keys. The 4-worker cap is a hard platform limit (cache/limits.py) — the process is killed if exceeded, so do NOT bump max_workers to beat the deadline; 4 workers already give ~0.1s.
