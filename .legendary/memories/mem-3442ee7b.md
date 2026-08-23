---
id: mem-3442ee7b
type: episode
title: guard could never match a trigger containing a quote or newline
created: '2026-08-23T12:46:29.247114Z'
source: agent
status: active
anchors:
- file: src/legendary/cli.py
  symbol: _haystack
  lines:
  - 230
  - 248
  commit: 4ccbafc
  content_hash: sha256:9980b315127f93d6de90da4fbc050998e1816ba2c29a827996aebc7191c28d0f
tags:
- guard
- matching
triggers:
- json.dumps
- haystack
---
json.dumps() escapes " and \n while the stored trigger is compared raw, so any trigger containing one was unmatchable even when it appeared verbatim in the output. Two of four triggers in a real memory were dead. Build the haystack from raw leaf strings, never from a JSON encoding.
