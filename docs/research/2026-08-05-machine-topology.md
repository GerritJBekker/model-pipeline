---
title: Laptop/Desktop Machine Topology
date: 2026-08-05
tags: [tooling, infra, claude-code]
status: active
---

# Laptop/Desktop Machine Topology

This repo is worked on from two machines: **Laptop** (`/home/gerrit/PROJECTS/model-pipeline`) and **Desktop**, reachable via `ssh gerrit@desktop`. Claude Code can run natively on either machine, and both can have their own concurrent session on the same repo — a Laptop session should not assume it has exclusive control of the Desktop checkout, since a native Desktop session may hold uncommitted changes it can't see.

Reaching Desktop from Laptop: `ssh gerrit@desktop 'cd ~/PROJECTS/model-pipeline && <command>'`. Check `git status` there first every time before pulling or discarding changes.

See `2026-08-05-claude-memory-sync.md` for how memory stays consistent across the two.

## Environment drift between machines (2026-08-10)

Laptop and Desktop have different conda layouts for the same `ml_env` environment — Laptop: `/home/gerrit/.pyenv/versions/miniconda3-latest/envs/ml_env`; Desktop: `/home/gerrit/anaconda3/envs/ml_env`. A commit made from Desktop once hardcoded Desktop's path into the repo-tracked `.vscode/settings.json`, which broke VS Code's Python interpreter on Laptop after pulling. When touching `.vscode/settings.json` or any absolute conda/python path, verify it's correct for the current machine (`hostname` first) before committing.

**Resolved (2026-08-10):** verifying-before-committing wasn't enough — a correct path for whichever machine committed it still broke the other machine on the next pull, and this happened repeatedly (Laptop's path got committed, broke Desktop; fixing it for Desktop would have broken Laptop again). The actual fix is to not commit an absolute interpreter path at all: `.vscode/settings.json` now contains just `{}`. Each machine selects its `ml_env` interpreter locally via VS Code's "Python: Select Interpreter" picker, which VS Code retains outside the tracked workspace file — so neither machine's selection gets overwritten by the other's commits/pulls anymore.
