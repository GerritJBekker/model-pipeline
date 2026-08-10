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

Added a univariate AUC-vs-label screen (`src/mean_reversion.ipynb`, scored via `abs()` for symmetric features) to check empirically which features carry signal before investing in a real model. Initial results against `make_labels()` (SPY / ES=F): `zscore` ~0.83-0.84, `momentum` ~0.65, `bb_width` ~0.58-0.60, `rel_volume` ~0.56-0.58, everything else ≤0.53 (near-random). **This screen turned out to be misleading** — see below.

### Re-screened against a non-circular label — nothing survives (2026-08-10)

`make_labels()`'s label ("did `|zscore|` shrink over the horizon") is derived from the same statistic the top-ranked feature measures, so `zscore`'s high AUC was largely circular, not real edge. Added `make_return_labels()` — labels on realized forward return in the reversion direction (opposite the current zscore's sign) instead, a genuine future price outcome independent of the feature set's construction — and re-ran the same screen against it.

**Result: every feature, including `zscore` and `momentum`, lands within ~0.03 of 0.5 (AUC) — no better than random.** The `momentum` ~0.65 result from the first screen doesn't survive either. None of the 14 features (6 original + 8 candidates from this session) show meaningful univariate predictive power against actual forward price movement at this horizon (5 bars) and threshold (any positive move, `threshold_return=0.0`).

**Implication**: this doesn't prove there's no edge — interactions between features, a proper (non-univariate) model, different horizons/thresholds, or regime/session filtering could still reveal something a single-feature screen can't. But it means there's currently no cheap, obvious signal to lean on, and the feature set as designed shouldn't be assumed to work before those are tried. Worth doing before sinking time into model training: sweep `horizon`/`threshold_return` in `make_return_labels()` to check if the null result is horizon-specific, and/or try a simple multivariate model (the univariate screen can't see interaction effects).

### Horizon/threshold sweep — null result confirmed, not horizon-specific (2026-08-10)

Swept `horizon` (1-30 bars) × `threshold_return` (0-0.003) for both tickers, taking the *best* feature's `|AUC-0.5|` per combo (heatmap in `src/mean_reversion.ipynb`). A "hot corner" appeared at short horizon + high threshold (SPY: AUC=0.998 at `horizon=1, threshold=0.002`; ES=F: AUC=0.888 at `horizon=1, threshold=0.0015`) — **but this is a class-imbalance artifact, not signal.** SPY's best cell has ~5 positive examples out of 4814; ES=F's has ~162 out of 14754. AUC is unreliable at that few positives, and testing ~40 label configs × 14 features (280 tests) makes finding a noisy standout by chance likely regardless. The heatmap's smooth gradient (edge growing as the positive class shrinks) is exactly what shrinking sample size alone predicts, independent of any real predictability.

**The well-populated, roughly balanced label at `horizon=5, threshold=0.0` remains the trustworthy read: no real signal in this feature set.** Next step per the original implication above — try a simple multivariate model instead of continuing to search univariate/label-definition space, since that's now been swept without finding anything real.

### Multivariate model (LightGBM, walk-forward) — null result confirmed (2026-08-10)

Before training: fixed a session-boundary label leak (`make_return_labels()`'s `shift(-horizon)` ran on the full concatenated series, so the last `horizon` rows of every session picked up a forward return crossing into the *next* session — not achievable by a same-session, no-overnight strategy). Added `mask_session_leakage()` plus session-based expanding-window walk-forward folds (`src/mean_reversion.ipynb`): SPY got 4 folds (12 clean sessions, single-session test blocks), ES=F got 6 folds (~weekly, 6-fragment test blocks over 64 calendar-date fragments) — kept separate, not pooled, since ES=F's calendar-date grouping is a placeholder that fragments each real trading week around the CME daily maintenance break.

Trained a shallow, regularized LightGBM classifier (`max_depth=3`, `num_leaves=7`, row/column subsampling, L1+L2) per fold on all 14 features against `make_return_labels()` at `horizon=5, threshold_return=0.0`. **Test AUC is essentially 0.5 for both tickers** (SPY 0.524 ± 0.058, one fold below 0.5; ES=F 0.520 ± 0.027), while train AUC is much higher (SPY 0.824, ES=F 0.725) — a large train-test gap showing the model overfits even under conservative regularization, since 200 trees have enough capacity to fit noise in a few thousand training rows when there's no real pattern to find. Feature importance shows no dominant feature and doesn't rank `zscore`/`momentum` (the features that looked strongest in the earlier flawed univariate screens) any higher than the rest.

**Implication**: the hypothesis that a multivariate model would surface feature interactions the univariate screen couldn't see does not pan out with this feature set, data volume, and horizon/threshold — this confirms rather than overturns the univariate null result. Continuing to try model classes on the same OHLCV-derived features is low expected value. Higher-value next steps: real order-flow features aren't available from yfinance OHLCV; session boundaries are still a placeholder (particularly costly for ES=F, where six calendar-date fragments per week may be artificially splitting real continuous price action); or the feature set may simply not contain exploitable signal at this horizon regardless of model complexity.
