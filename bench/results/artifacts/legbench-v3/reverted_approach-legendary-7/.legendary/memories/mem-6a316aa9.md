---
id: mem-6a316aa9
type: decision
title: warm_cache must fan out fetches across a bounded thread pool
created: '2026-08-21T14:05:34.008533Z'
source: agent
status: active
anchors:
- file: cache/warm.py
  symbol: warm_cache
  lines:
  - 17
  - 29
  commit: 433ae9e
  content_hash: sha256:6ec5afb7b763c363aa75f7eea806a9d5a79b719119539beb6960be17e93c261f
- file: cache/limits.py
  lines:
  - 4
  - 4
  commit: 433ae9e
  content_hash: sha256:346d9140c14d4a5dbf4cb19adbd11cce13d69891d50b7a5f14b598c2f9f99b02
tags:
- concurrency
- cache
- performance
triggers: []
---
warm_cache in cache/warm.py fetches all keys, each via _fetch() which sleeps 0.01s (I/O-bound). Sequential fetch of 40 keys = 0.40s, over the 0.30s test deadline (tests/test_warm.py). Fix: use ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) and pool.map to fetch concurrently — gives ~0.10s. max_workers MUST stay capped at MAX_CONCURRENT_WORKERS from cache/limits.py (currently 4); the platform kills processes exceeding it, so do not raise it for speed. Empty keys list is short-circuited to avoid spinning up a pool.
