---
id: mem-8d5f292c
type: episode
title: report.py bypassed the activation gate that had already rejected every trial
created: '2026-08-23T12:46:29.349129Z'
source: agent
status: active
anchors:
- file: bench/report.py
  symbol: _failures
  lines:
  - 25
  - 48
  commit: 4ccbafc
  content_hash: sha256:53a8d0423e10adb03f6dad1e5325f48de2ec4d4f3ff03a13ce8713c4e9632497
tags:
- benchmark
- method
triggers:
- ARM_ORDER
- EXCLUDED
---
The harness flagged all ten invalid trials, but ARM_ORDER listed only two arms, so ablation arms never passed through _failures(). The median was computed by hand, outside the gate. Every arm must be in ARM_ORDER, and the reporter must be the only sanctioned analysis path.
