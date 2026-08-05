# Project instructions

Model and data frameworks for algo trading systems. Full project purpose and constraints: `docs/research/2026-08-05-algo-trading-system-brief.md`.

## Data

Cached market data (yfinance daily/intraday bars) lives under `/home/gerrit/Sync`, not in this repo.

## Research log

Before making architecture or strategy decisions, check `docs/research/` (indexed in `docs/research/README.md`). Add a note there for non-trivial decisions — one file per topic, `YYYY-MM-DD-short-slug.md`, with YAML frontmatter (see README for the template).

## Machine awareness

This repo is worked on from two machines: **Laptop** (`/home/gerrit/PROJECTS/model-pipeline`) and **Desktop** (SSH alias `desktop`, reachable via `ssh gerrit@desktop`). Claude Code can also run natively on Desktop as its own session.

At the start of a session, if it's not already clear which machine you're on, run `hostname` before taking actions that depend on machine identity (paths, running processes, uncommitted changes) — don't assume Laptop by default. See the `machine-topology` memory for fuller context.
