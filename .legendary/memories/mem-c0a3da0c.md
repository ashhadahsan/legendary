---
id: mem-c0a3da0c
type: decision
title: the benchmark runs the working tree, not the published wheel
created: '2026-08-23T12:46:29.363935Z'
source: agent
status: active
anchors:
- file: bench/run_bench.py
  lines:
  - 1
  - 522
  commit: 4ccbafc
  content_hash: sha256:b56588b98ead659693effd4e1787e5b20b14ce968e2113d02749223aa5075444
tags:
- benchmark
triggers: []
---
Hooks executed uvx --from legendary-mcp (PyPI) while the harness asserted on local behaviour, so a local fix could never affect the benchmark and guard_fired was False by construction in ~70 trials. Pin --from to the repo path.
