---
id: mem-c4c8fa16
type: episode
title: asking agents for verbatim error strings produced triggers that never recur
created: '2026-08-23T12:46:29.317244Z'
source: agent
status: active
anchors:
- file: src/legendary/mcp_server.py
  lines:
  - 1
  - 98
  commit: 4ccbafc
  content_hash: sha256:122678c5da2c2f6b007c1ccbe8d23f228399ffd5635e1b1fdadb337f8ae14197
tags:
- triggers
- prompt
triggers:
- triggers
- trigger_warnings
---
The remember docstring asked for 'verbatim error strings or failing test names'. Agents complied exactly and stored test_billing_reconciliation and assert 0.0 == 25.0 - keys guaranteed not to repeat, since the next failure is a different test with different numbers. Ask for the invariant part: exception type and message.
