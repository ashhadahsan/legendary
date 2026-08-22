---
id: mem-6391fed4
type: episode
title: warm_cache must fetch concurrently (capped at MAX_CONCURRENT_WORKERS) to beat
  deadline
created: '2026-08-21T13:50:35.437785Z'
source: agent
status: active
anchors:
- file: cache/warm.py
  symbol: warm_cache
  lines:
  - 17
  - 26
  commit: 4f814b5
  content_hash: sha256:437b94356087a2a12e2ef9121386d97a22b25ee0201ab59b1f745409a60a2af4
- file: cache/limits.py
  lines:
  - 3
  - 4
  commit: 4f814b5
  content_hash: sha256:c3e6cc9f8141c4e6637567e8ae16e35d79a772a95d1483975ed91b8f4e244e36
tags:
- cache
- concurrency
- performance
triggers:
- test_warm_cache_completes_before_deadline
- took 0.40s, deadline is 0.30s
---
test_warm_cache_completes_before_deadline failed because warm_cache fetched 40 keys serially: 40 x _fetch's 0.01s sleep = 0.40s, over the 0.30s deadline. Fix: fetch via ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) using executor.map to preserve key order. Do NOT raise worker count above MAX_CONCURRENT_WORKERS (=4 in cache/limits.py) — the comment notes the platform kills processes exceeding it. 4 workers => ~10 batches x 0.01s = ~0.10s, under deadline.
