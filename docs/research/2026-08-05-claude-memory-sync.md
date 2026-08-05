---
title: Claude Code Memory Sync (Laptop/Desktop)
date: 2026-08-05
tags: [tooling, infra, claude-code]
status: active
---

# Claude Code Memory Sync (Laptop/Desktop)

Claude Code's persistent auto-memory for this project is now shared between Laptop and Desktop instead of living as two independent, diverging copies.

## Setup

Memory files physically live at `/home/gerrit/Sync/claude-memory/model-pipeline/` (synced folder). On each machine, Claude Code's per-project memory path is a symlink into that folder:

```
/home/gerrit/.claude/projects/-home-gerrit-PROJECTS-model-pipeline/memory -> /home/gerrit/Sync/claude-memory/model-pipeline
```

`/home/gerrit/Sync/claude-memory/README.md` documents the convention (one subdirectory per project, each holding per-topic `.md` memory files plus a `MEMORY.md` index).

## Why this matters

See [[machine-topology]] (Claude memory) — the repo can be worked on natively from either machine, sometimes with concurrent Claude Code sessions. Without a shared memory store, each machine's session would build up its own separate understanding of the project and drift apart. Symlinking both into the same synced folder keeps memory (user prefs, feedback, project context) consistent regardless of which machine a session runs on.
