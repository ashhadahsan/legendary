---
id: mem-a45dbe96
type: episode
title: refresh_cache must fetch concurrently (capped at MAX_CONCURRENT_WORKERS) to
  beat deadline
created: '2026-08-21T13:51:20.780985Z'
source: agent
status: active
anchors:
- file: cache/refresh.py
  symbol: refresh_cache
  lines:
  - 17
  - 25
  commit: 4f814b5
  content_hash: sha256:a54e6dbe0afa59c78d8c7ba3bb602e40d9a666f2aacbc448520d26f55506e460
tags:
- cache
- concurrency
- deadline
triggers:
- test_refresh_cache_completes_before_deadline
- took 0.40s, deadline is 0.30s
---
test_refresh_cache_completes_before_deadline failed because refresh_cache fetched 40 keys serially: 40 x _fetch's 0.01s sleep = 0.40s, over the 0.30s deadline. Fix: fetch via ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) and executor.map(_fetch, keys), then zip(keys, values) into _STORE to preserve key order. Do NOT raise worker count above MAX_CONCURRENT_WORKERS (platform kills processes over the limit). Same fix as warm.py's warm_cache.
