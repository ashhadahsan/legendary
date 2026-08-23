---
id: mem-cbb1460c
type: decision
title: no knowledge graph, no embeddings - retrieval is where the gains are
created: '2026-08-23T12:46:29.376764Z'
source: agent
status: active
anchors:
- file: src/legendary/index.py
  lines:
  - 1
  - 238
  commit: 4ccbafc
  content_hash: sha256:8e986223c08222b5cfc3ec27b971d4c2fb959bb38a4cab7d1b379ea9b64d74c7
tags:
- architecture
triggers: []
---
arXiv 2603.02473 measured ~20 points of accuracy across retrieval methods but only 3-8 across write strategies, with raw chunking matching LLM fact extraction at zero LLM cost. A graph is a large investment on the axis that moves least. This is why storage stays markdown + FTS5.
