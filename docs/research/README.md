# Research Log

Index of research notes for the algo trading system (futures/CFDs, no-overnight-positions, QuantConnect + IB). One file per topic/question, named `YYYY-MM-DD-short-slug.md`. Add an entry here when you add a note.

Each note starts with YAML frontmatter for machine-readable metadata:

```yaml
---
title: Short title
date: YYYY-MM-DD
tags: [session-scheduler, data]
status: draft   # draft | active | resolved
---
```

| Date | Note | Summary |
|------|------|---------|
| 2026-08-05 | [Algo Trading System Brief](2026-08-05-algo-trading-system-brief.md) | Repo's purpose: futures/CFD trading system, no-overnight-positions constraint, AFM/ESMA rules, QuantConnect+IB platform, open items |
| 2026-08-05 | [Ticker Data Inventory](2026-08-05-ticker-data-inventory.md) | 33 futures/ETF tickers cached at `/home/gerrit/Sync`, daily+1m+5m bars, basis for first models |
| 2026-08-05 | [Intraday Mean-Reversion Model — Design Notes](2026-08-05-intraday-mean-reversion-model-design.md) | Features (z-score, VWAP, RSI, rel. volume), walk-forward optimization, model returns probability not hard signal |
| 2026-08-05 | [Claude Memory Sync (Laptop/Desktop)](2026-08-05-claude-memory-sync.md) | Claude Code project memory now symlinked to a synced folder shared between Laptop and Desktop |
| 2026-08-05 | [Laptop/Desktop Machine Topology](2026-08-05-machine-topology.md) | Repo worked on from two machines, concurrent Claude Code sessions possible, SSH access pattern for reaching Desktop |
