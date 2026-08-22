---
id: mem-5d3735ad
type: decision
title: warm_cache must fan out fetches under MAX_CONCURRENT_WORKERS
created: '2026-08-21T14:02:31.172963Z'
source: agent
status: active
anchors:
- file: cache/warm.py
  symbol: warm_cache
  lines:
  - 17
  - 32
  commit: 4102ce8
  content_hash: sha256:5176410b26e8bd0fe3372b1532a24ef911ce601d3389dd3324a4dbc445a94972
- file: cache/limits.py
  lines:
  - 3
  - 4
  commit: 4102ce8
  content_hash: sha256:c3e6cc9f8141c4e6637567e8ae16e35d79a772a95d1483975ed91b8f4e244e36
tags:
- concurrency
- cache
- deadline
triggers: []
---
`warm_cache` in cache/warm.py fetches keys via `_fetch`, which sleeps 10ms each. Serial fetching of 40 keys = 400ms, exceeding the 300ms deadline asserted by tests/test_warm.py::test_warm_cache_completes_before_deadline. Fix: use a ThreadPoolExecutor capped at MAX_CONCURRENT_WORKERS (=4 in cache/limits.py) — the platform kills processes exceeding that many concurrent workers, so do NOT raise the worker count above it. `_fetch` is I/O-bound (time.sleep releases the GIL) so threads give the wall-clock speedup. Result: ~100ms.
