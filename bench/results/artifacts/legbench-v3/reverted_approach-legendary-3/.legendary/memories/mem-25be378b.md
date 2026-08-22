---
id: mem-25be378b
type: episode
title: warm_cache must fetch concurrently, capped at MAX_CONCURRENT_WORKERS
created: '2026-08-21T13:53:21.514756Z'
source: agent
status: active
anchors:
- file: cache/warm.py
  symbol: warm_cache
  lines:
  - 17
  - 26
  commit: 10e5013
  content_hash: sha256:ba29ec0bef5b016dbfe558ce6a273e971993c87d74a4d177f698eb5bbb07a8c0
tags:
- cache
- concurrency
- performance
triggers:
- test_warm_cache_completes_before_deadline
- deadline is 0.3s
---
test_warm_cache_completes_before_deadline requires warming 40 keys within 0.30s. _fetch sleeps 0.01s, so serial warming takes ~0.4s and fails. Fix: use ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) (=4) in warm_cache — ~10 rounds x 0.01s ~= 0.1s. Do NOT raise worker count above MAX_CONCURRENT_WORKERS: the platform kills processes exceeding it (cache/limits.py). _fetch is sleep/IO-bound so threads parallelize despite the GIL.
