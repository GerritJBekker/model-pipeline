---
title: Algo Trading System Brief
date: 2026-08-05
tags: [project-brief, regulatory, platform, architecture]
status: active
---

# Algo Trading System Brief

This repo builds an algorithmic trading system trading **futures and CFDs**, aimed at stable daily profits via multiple strategies (trend/momentum, mean reversion, statistical/pairs arbitrage). Built in Python.

Full project brief lives at `C:\Users\GerritBekker\algo-trading-system\project-brief.md` (Windows path — not present on the laptop/desktop Linux checkouts) — read that file for complete details (regulatory constraints, platform decision, strategy models, open items, next steps) rather than duplicating it here.

## Key decisions locked in so far

- **Netherlands-based, retail client** under AFM/ESMA — CFD leverage capped (30:1 down to 2:1 by asset class), forced liquidation at 50% margin. Professional client status (removes caps) not currently met, revisit later.
- **Futures are the default/primary instrument** (not subject to ESMA CFD caps); CFDs only used where no viable futures contract exists.
- **Platform: QuantConnect (LEAN engine) for research/backtesting + Interactive Brokers for live execution.** LEAN CLI supports fully local Python model training, pushed to QuantConnect Object Store for cloud inference.
- **Hard constraint: no overnight positions** — system rotates across sessions (Asia → Europe → US) opening/closing similar trades per session ("follow-the-sun"), never holding overnight. This drives extra required infrastructure: session scheduler, regime classifier, cross-market handoff model, execution/slippage-near-boundary model, per-session risk/kill-switch, cross-session capital allocation.

## Open items / not yet decided

- Market lineup / session schedule
- Trade mechanics
- Validation methodology
- Numeric success criteria
- Cost/roll methodology
- News filter
- Rollout plan

## Why this matters for this repo

The yfinance data fetching and caching work already in the repo is groundwork for this system. Data/infra choices (e.g. yfinance caching, session scheduling) should be evaluated against these constraints (no overnight positions, futures-first, QuantConnect/IB platform).
