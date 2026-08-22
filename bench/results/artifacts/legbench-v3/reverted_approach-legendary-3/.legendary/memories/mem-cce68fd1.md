---
id: mem-cce68fd1
type: episode
title: refresh_cache must fetch concurrently, capped at MAX_CONCURRENT_WORKERS
created: '2026-08-21T13:54:03.148833Z'
source: agent
status: active
anchors:
- file: cache/refresh.py
  symbol: refresh_cache
  lines:
  - 17
  - 25
  commit: 10e5013
  content_hash: sha256:a54e6dbe0afa59c78d8c7ba3bb602e40d9a666f2aacbc448520d26f55506e460
tags:
- cache
- concurrency
- deadline
triggers:
- test_refresh_cache_completes_before_deadline
- took 0.4
- deadline is 0.30s
---
test_refresh_cache_completes_before_deadline requires refreshing 40 keys within 0.30s. _fetch sleeps 0.01s, so serial refresh takes ~0.4s and fails. Fix: use ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) (=4) in refresh_cache and executor.map over keys — ~10 rounds x 0.01s ~= 0.1s (test observed 0.13s). Do NOT raise worker count above MAX_CONCURRENT_WORKERS; the platform kills processes that exceed it. Same fix pattern as cache/warm.py.
