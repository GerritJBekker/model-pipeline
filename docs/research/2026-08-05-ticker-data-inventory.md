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

## Automated daily fetch (added 2026-08-10)

`update_all_tickers()` (`src/yfinance.py`) now runs automatically once a day via a systemd user timer, **Laptop only** — not set up on Desktop:

- Unit files: `~/.config/systemd/user/yfinance-update.{service,timer}`
- Schedule: daily ~18:00 CEST (`Persistent=true`, so a missed run catches up when the laptop wakes; `RandomizedDelaySec=10min`)
- Runs as `ml_env` (`/home/gerrit/.pyenv/versions/miniconda3-latest/envs/ml_env/bin/python3`)
- Logs: `/home/gerrit/Sync/logs/yfinance-update.log`
- `loginctl enable-linger gerrit` was set so the timer fires even without an active login session

**Why daily:** Yahoo only serves ~7 days of 1m intraday history — the previous manual/occasional cadence risked permanent gaps whenever more than 7 days passed between runs. Daily gives a buffer against missed days (laptop off/asleep, travel) without hitting that ceiling. Laptop was chosen over Desktop because it's on far more consistently ("always on when not traveling" vs. Desktop's "only on when working on the project") — see [Machine Topology](2026-08-05-machine-topology.md).

**Residual gap:** if Laptop is powered off (not just asleep) for longer than ~5-6 days (e.g. an extended trip), the missed window can still exceed Yahoo's 7-day 1m retention. No automated fallback for this yet — mitigate by triggering `systemctl --user start yfinance-update.service` manually (locally or via SSH) before/during a long trip.

## 5m history bug found + fixed, rolling cache backfilled (2026-08-10)

Comparing earliest timestamps between the `0803_*` dated snapshots and the current rolling-history files surfaced two data-retention issues:

- **5m intraday, all 33 tickers**: rolling cache only ever held ~7 days of 5m bars instead of Yahoo's actual ~60-day allowance. Root cause: `_intraday_start_end()` in `src/yfinance.py` used a single `INTRADAY_HISTORY_DAYS = 7` constant for both 1m and 5m, so the very first (cold-start) fetch for 5m was clamped to 7 days and every subsequent run only ever moved that window forward — the deeper history was never captured, not just lost afterward.
- **1m intraday, the 9 ETF tickers only** (SPY, FEZ, EWG, EWU, EWQ, EWJ, EWH, ASHR, INDO): rolling cache was missing ~4 days of history that the 0803 snapshot had. Futures 1m matched exactly. Consistent with the now-fixed cache-overwrite bug from commit `a538b43` (`get_intraday_data()` used to write straight to the cache file before the append step read it back).
- **Daily**: matched exactly on all 33 tickers — no issue.

**Fix**: `INTRADAY_HISTORY_DAYS` is now a per-interval dict (`{"1m": 7, "5m": 60}`, `src/yfinance.py:71`), used in `_intraday_start_end()` (`src/yfinance.py:214`). Going forward, cold-start 5m fetches will correctly request 60 days.

**Backfill**: the fix alone doesn't recover already-lost history — since a cache file already exists for every ticker, `_intraday_start_end()` takes the "cache exists" branch and only ever fetches forward from the last cached timestamp, never revisiting the older window. Instead, ran a one-off local merge of all `0803_*` snapshot files into the rolling cache via the existing `append_daily_data`/`append_intraday_data` functions (same dedupe/sort logic already in use, so no new code path). Verified afterward across all 33 tickers: rolling-cache earliest timestamp now matches or precedes the 0803 snapshot's earliest for both 1m and 5m, no duplicate index entries, indices monotonic.

**Resolves the "prune 0803 snapshots" open question below**: the `0803_*` files are now fully redundant — everything they held is merged into the rolling cache. Deleted (all 99 files) later the same day.

## Per-ticker date-range log (added 2026-08-10)

`update_all_tickers()` now ends each run by calling `write_ticker_dates_log()` (`src/yfinance.py`), which writes `/home/gerrit/Sync/logs/yfinance-dates.log` — a plain-text table of min/max cached timestamp per ticker × dataset (daily, intraday_1m, intraday_5m; 99 rows for the 33-ticker universe). Purpose: a quick sanity check of data freshness/coverage without opening every CSV (e.g. confirms ETF daily bars lag futures by a day since their cash session hasn't closed yet, or would flag a ticker silently falling behind).

Before overwriting, the previous log is copied to `yfinance-dates.bak` (one generation of history, not a full timestamped archive) — for audit purposes, so the log from the prior run isn't just clobbered silently.

## Open questions

- Confirm coverage/gaps per ticker (some may have shorter history than SPY)
- Decide whether `data/` (repo) should stay empty/gitignored with `/home/gerrit/Sync` as the real cache, or whether the two should be reconciled
- **Roll-adjustment**: current `=F` tickers are raw front-month, not roll-adjusted — will show fake price jumps at contract rollover dates, corrupting momentum/trend signals. Ties to the "cost/roll methodology" open item in the [Algo Trading System Brief](2026-08-05-algo-trading-system-brief.md).
- Which additional Europe/Japan futures tickers to add for session-native coverage, and when (deferred — not needed for first models)
