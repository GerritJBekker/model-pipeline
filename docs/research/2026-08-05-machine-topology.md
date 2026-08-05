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
