---
title: Intraday Mean-Reversion Model — Design Notes
date: 2026-08-05
tags: [model-design, mean-reversion, features, intraday]
status: active
---

# Intraday Mean-Reversion Model — Design Notes

First model to build: intraday, single-session mean reversion. Chosen as the starting strategy (over trend/momentum or stat arb/pairs, see [Algo Trading System Brief](2026-08-05-algo-trading-system-brief.md)) because it needs no roll-adjustment (short lookback windows), no cross-asset correlation work (single instrument), and fits the no-overnight constraint naturally as a same-session round-trip.

## Features

Built from OHLCV only (no order book/bid-ask available):

- **Z-score of price vs. rolling mean** — `(close - rolling_mean_N) / rolling_std_N`, the core mean-reversion signal
- **Distance from session VWAP** — computed from typical price × volume; more meaningful than a simple MA intraday
- **RSI / stochastic-oscillator-style feature** — where close sits in the recent high/low range
- **Rolling realized volatility** — both a feature and a regime filter (mean reversion works better range-bound, poorly in trending/breakout vol)
- **Relative volume** — current vs. rolling average volume; spikes often mark exhaustion points worth fading
- **Short lookback momentum** (e.g. last 5-bar return) — used as a *filter*, not a signal, to avoid fading a strong move
- **Time-since-session-open / time-to-session-close** — needed because of the no-overnight rule; model must know it can't hold near close

## Volume data

Confirmed volume is usable as-is: zero-volume bars are rare (~7 out of ~7,600–7,700 rows, <0.1%, checked on 6E=F, ES=F, GC=F 1m data) and not concentrated in any particular session/hour. Caveat: yfinance futures volume is CME's consolidated Globex volume, not true order flow — fine for relative/rolling-average features, not precise enough for execution/slippage modeling later.

## Optimization method

Intraday data is thin (7 days of 1m bars, 60 days of 5m — a few thousand rows per ticker), so avoid anything deep-learning-sized. Start with a simple classifier (logistic regression or shallow gradient-boosted trees) predicting reversion probability.

- **Validation**: walk-forward, not random k-fold — random splits leak badly on time series. Folds should respect session boundaries (never train and validate on bars from the same session).
- **Tuning objective**: optimize a P&L-based metric on validation folds, not classification accuracy — accuracy doesn't capture risk-adjusted return or stop/target asymmetry.

## Performance metrics (decision 2026-08-05)

Track all three on every backtest/walk-forward run, not Sharpe alone:

- **Sharpe** — `(mean_return / std_return) × √252` (annualized) — standard risk-adjusted return, but penalizes upside and downside volatility symmetrically
- **Sortino** — same idea, but denominator uses only downside deviation — more appropriate here since mean-reversion P&L is typically negatively skewed (frequent small wins, occasional sharp losses when reversion fails)
- **Calmar** — `annualized return / max drawdown` — captures tail/drawdown risk that Sharpe and Sortino both under-weight

Rough Sharpe read for context: <0 losing, 0–0.5 weak, 0.5–1.0 mediocre-but-plausible, 1.0–2.0 good, >2.5–3 excellent or a sign of overfitting/lookahead bias if it's from a backtest. Given the strategy is competing against professional market makers on liquid futures with retail-grade delayed data, expect realistic live Sharpe (if any edge survives) toward the low end of that range.

## Model output

Model returns a **probability (or expected forward return)**, not a hard buy/sell signal. Entry/exit thresholds and position sizing stay as a separate rule layer on top of the model output. This keeps threshold backtesting decoupled from retraining, and keeps the no-overnight exit logic (flatten near session close regardless of signal) outside the model itself.

## Framework reuse (decision 2026-08-05)

This model's pipeline structure — features → probability/expected-return output → separate entry/exit rule layer → walk-forward validation → Sharpe/Sortino/Calmar evaluation — is the template for subsequent strategies (trend/momentum, stat arb/pairs), not a one-off. Future strategy notes should describe what changes (features, label definition, session scope) relative to this framework rather than re-deriving it from scratch.

## Implementation status (updated 2026-08-10)

`src/mean_reversion.ipynb` implements the feature set (`build_features()`) and a first label definition (`make_labels()`, z-score-shrink reversion target + raw forward return), plus matplotlib/seaborn visualization of the features and label/forward-return distributions. Verified clean (no NaNs) against both SPY (1m, single-session) and ES=F (5m, near-24h). Converted from an initial `.py` module to a notebook (2026-08-10) so features/windows/labels can be iterated on interactively — the module version is no longer in the repo.

- **Session grouping is calendar-date**, correct for single-session ETFs but a placeholder for futures until real session boundaries (Asia/Europe/US) are decided (see brief's "Market lineup / session schedule" open item). VWAP and time-since-open/to-close currently reset on calendar-date boundaries, not true session boundaries.
- **Rolling-window features are NOT session-scoped** (global `.rolling()` on the full series) — near session/day boundaries this can leak a few bars of the prior day into a window. Acceptable for now, revisit once session boundaries are formalized.
- **Plots break the line at data gaps >20min** (overnight, weekends, CME's daily maintenance break) rather than interpolating across them — an initial version silently drew a fake flat line from Friday's close straight to Monday's open before this was caught by inspecting the rendered chart.

**Not yet built**: model training, walk-forward validation, and the Sharpe/Sortino/Calmar evaluation — still blocked on trade mechanics (entry/exit thresholds, position sizing) and cost/roll methodology, both still open per the brief.

## Feature screening (added 2026-08-10)

Extended `build_features()` with 8 more candidates: `atr_pct` (true-range vol), `return_autocorr` (rolling lag-1 return autocorrelation, a trending-vs-range-bound regime feature), `bb_width` (Bollinger band width, volatility regime distinct from `zscore`'s price-position), `time_sin`/`time_cos` (cyclical time-of-day), and `dist_from_open`/`dist_from_high`/`dist_from_low` (session-relative price levels).

Added a univariate AUC-vs-label screen (`src/mean_reversion.ipynb`, scored via `abs()` for symmetric features) to check empirically which features carry signal before investing in a real model. Results (SPY / ES=F): `zscore` ~0.83-0.84, `momentum` ~0.65, `bb_width` ~0.58-0.60, `rel_volume` ~0.56-0.58, everything else ≤0.53 (near-random). **`zscore`'s dominance is largely mechanical** — the label is defined as "did `|zscore|` shrink," so a feature built from the same quantity the label is derived from is partly circular, not necessarily real edge. `momentum` is the more informative result since it's independent of the label's construction. None of the 8 new candidates showed meaningful univariate signal against this label — kept in the feature set for now (cheap to compute, may matter more once trade mechanics/labels are refined) but not something to lean on as-is.
