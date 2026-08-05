---
title: Ticker Data Inventory
date: 2026-08-05
tags: [data, yfinance, tickers]
status: active
---

# Ticker Data Inventory

Cached ticker data used as the basis for the first models. Fetched via `src/yfinance.py` (yfinance wrapper), cached to `DATA_DIR` — currently `/home/gerrit/Sync` (not the repo's `data/` folder, which is empty; not git-tracked).

## Tickers (33)

- **FX futures**: 6B (GBP), 6E (EUR), 6J (JPY)
- **Index futures**: ES, NQ, RTY, YM, NIY, NKD
- **Energy futures**: CL, BZ, NG, HO
- **Metals futures**: GC, SI, HG, PL
- **Ags/softs futures**: ZC, ZS, ZW, KC, SB
- **Rates futures**: ZB, ZN
- **Country/regional ETFs**: ASHR, EWG, EWH, EWJ, EWQ, EWU, FEZ, INDO, SPY

## File generations

Two naming conventions present, same 33 tickers, from the yfinance caching refactor (commits `15b8643`, `c15b796`):

1. **Dated snapshots** (one-off pulls, 2026-08-03): `0803_daily_{ticker}_1d_max.csv`, `0803_intraday_{ticker}_1m_7d.csv`, `0803_intraday_{ticker}_5m_60d.csv`
2. **Rolling history** (current append/update cache): `daily_{ticker}.csv`, `intraday_{ticker}_1m_history.csv`, `intraday_{ticker}_5m_history.csv`

## Content

- **Columns**: `datetime, Close, High, Low, Open, Volume`
- **Daily**: full history where available — SPY back to 1993 (~8,400 rows)
- **Intraday 1m**: last ~7 trading days
- **Intraday 5m**: last ~60 days
- Timestamps are tz-aware (e.g. `-04:00`)
- Total ~89MB across 198 files

## Session coverage (resolved 2026-08-05)

Checked hour-of-day coverage in the 1m intraday files for futures vs ETFs:

- **Futures** (checked 6E=F, ES=F, GC=F; presumably holds for the rest): near-24h coverage, hours 00–23 except 17 (standard CME Globex daily maintenance break, 17:00–18:00 ET). **Asia/Europe/US session data is already present** — no gap for the follow-the-sun design.
- **ETFs** (checked SPY, representative of the group): only 09:30–16:00 ET, US regular session. This is inherent to how ETFs trade (only when their US listing exchange is open), not a yfinance limitation — no fix available by switching data source.

**Implication**: the regional ETFs (ASHR, EWG, EWH, EWJ, EWQ, EWU, FEZ, INDO) cannot stand in for genuine Asia/Europe session price action — they only show the US-hours reaction to those regions.

**Decision (2026-08-05)**: session-rotation models don't need to trade the same ticker across all three sessions — each session can use region-native instruments. Regional ETFs stay for daily-bar strategies; Asia/Europe session models use futures (e.g. 6J/NIY/NKD for Asia, 6E/6B/ZB for Europe). More Europe- and Japan-specific futures tickers can be added later to round out session-native coverage — not needed for the first models.

## Open questions

- Confirm coverage/gaps per ticker (some may have shorter history than SPY)
- Decide whether `data/` (repo) should stay empty/gitignored with `/home/gerrit/Sync` as the real cache, or whether the two should be reconciled
- Dated snapshot files vs rolling history files — keep both, or prune the one-off snapshots now that rolling history supersedes them?
- **Roll-adjustment**: current `=F` tickers are raw front-month, not roll-adjusted — will show fake price jumps at contract rollover dates, corrupting momentum/trend signals. Ties to the "cost/roll methodology" open item in the [Algo Trading System Brief](2026-08-05-algo-trading-system-brief.md).
- Which additional Europe/Japan futures tickers to add for session-native coverage, and when (deferred — not needed for first models)
