---
id: mem-befe1a38
type: episode
title: refresh_cache must fetch concurrently to beat 0.30s deadline
created: '2026-08-21T14:12:03.597094Z'
source: agent
status: active
anchors:
- file: cache/refresh.py
  symbol: refresh_cache
  lines:
  - 17
  - 27
  commit: '4029510'
  content_hash: sha256:62743d316b9209d5111ea6ce2cec22fa998f72a58b587c87930f5ed914e08085
tags:
- concurrency
- cache
- threadpool
triggers:
- test_refresh_cache_completes_before_deadline
- deadline is 0.30s
---
test_refresh_cache_completes_before_deadline fetches 40 keys with a 0.30s deadline. _fetch sleeps 0.01s each, so the sequential loop took ~0.4s and failed. Fix: fetch via ThreadPoolExecutor with max_workers=min(MAX_CONCURRENT_WORKERS, len(keys)), preserving order by zipping keys with executor.map results. MAX_CONCURRENT_WORKERS=4 (cache/limits.py). Same pattern as warm_cache.
