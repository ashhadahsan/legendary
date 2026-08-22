---
id: mem-d784f4c8
type: decision
title: warm_cache must fetch concurrently within MAX_CONCURRENT_WORKERS
created: '2026-08-21T13:55:55.111456Z'
source: agent
status: active
anchors:
- file: cache/warm.py
  symbol: warm_cache
  lines:
  - 17
  - 27
  commit: a87e246
  content_hash: sha256:098129ab910f0848e042fb34e020f5fe1657cbd4760f734ec496bc7813a40834
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
warm_cache() fetches 40 keys, each _fetch sleeps 0.01s. Serial = ~0.40s, exceeding the 0.30s deadline in tests/test_warm.py. Fix: use ThreadPoolExecutor with max_workers=min(MAX_CONCURRENT_WORKERS, len(keys)) (cap is 4 per cache/limits.py — exceeding it gets the process killed). pool.map preserves key order. Do not raise worker count above MAX_CONCURRENT_WORKERS to go faster.
