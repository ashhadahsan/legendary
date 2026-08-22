---
id: mem-5f58af5b
type: decision
title: warm_cache uses bounded ThreadPoolExecutor to meet deadline
created: '2026-08-21T14:08:32.180303Z'
source: agent
status: active
anchors:
- file: cache/warm.py
  symbol: warm_cache
  lines:
  - 17
  - 30
  commit: a23f02b
  content_hash: sha256:a449a1db5842ea94c8a382d7a0a38b63e6e4f135c953964f6c1dd4828b325042
- file: cache/limits.py
  lines:
  - 3
  - 4
  commit: a23f02b
  content_hash: sha256:c3e6cc9f8141c4e6637567e8ae16e35d79a772a95d1483975ed91b8f4e244e36
- file: tests/conftest.py
  lines:
  - 1
  - 41
  commit: a23f02b
  content_hash: sha256:30af6e3b915bb904439603d35f47cf557077c451774e5ecc192ea5cfe3ee095f
tags:
- cache
- concurrency
- deadline
triggers: []
---
warm_cache fetched 40 keys serially (40 * 0.01s = 0.4s) which blew the 0.30s deadline in test_warm.py. Fixed by fetching concurrently via ThreadPoolExecutor(max_workers=min(MAX_CONCURRENT_WORKERS, len(keys))). MAX_CONCURRENT_WORKERS=4, so ~0.1s. The tests/conftest.py autouse fixture watches threading.active_count() and raises ConcurrencyLimitExceeded if peak > MAX_CONCURRENT_WORKERS=4, so the pool size MUST stay <= 4 (ThreadPoolExecutor caps live threads at max_workers). cache/refresh.py has the identical serial bug and also fails its deadline test, but was out of scope for this fix.
