# How legendary compares

| | Graphify / Serena | mem0 / Zep | legendary |
|---|---|---|---|
| Models code structure | yes | no | anchors only |
| Remembers failed attempts | no | partly | yes (`episode` + triggers) |
| Memories tied to code entities | n/a | no | yes |
| **Detects when a memory goes stale** | n/a | **no** | **yes** |
| **Pushes memory without being asked** | no | no | **yes (hooks)** |
| Team-shared via git | graph committed | no (hosted service) | yes |
| Retrieval needs an LLM | no | embeddings | no (FTS5) |
| Runs fully local | yes | partly | yes |

The last two rows are the whole product. Everything above them is table
stakes or someone else's job.

## Code-graph tools

Tools like Graphify and Serena build a structural map of your codebase. They
answer *"what is this code?"* extremely well.

They do not remember anything. A graph cannot tell you that the obvious fix was
tried in March and deadlocked under WAL.

**These are complementary.** Running a code-graph tool alongside legendary is
the recommended setup: one knows the shape of the code, the other knows the
history of your decisions about it.

## Memory frameworks

mem0, Zep/Graphiti, and Letta remember conversations well and have genuinely
good ideas - Graphiti's bi-temporal model and invalidate-don't-delete
philosophy directly influenced legendary's `supersedes` design.

Their structural gap is that memories are not tied to code. A memory about
`auth.py` stays confidently in the store after `auth.py` is rewritten, and
there is no mechanism to notice. Fixing that requires anchoring memories to
code entities at a commit, which is a data-model change, not a feature.

legendary also gets temporality for free where they had to build for it: since
memories are git-tracked files, `git log .legendary/` *is* the ingestion
history and `git checkout` *is* a point-in-time query.

## Why we did not build a knowledge graph

The retrieval-vs-utilization literature reports accuracy moving ~20 points
across retrieval methods but only 3-8 across write strategies, with raw
chunking matching LLM-based fact extraction at zero LLM cost. A knowledge graph
is a large investment on the axis that moves the least. v0.2 went the other
way: we deleted our own LLM write-side feature and spent the effort on
delivery.
