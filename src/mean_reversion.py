"""Feature/label pipeline for the intraday mean-reversion model.

Implements the spec in docs/research/2026-08-05-intraday-mean-reversion-model-design.md.
Operates on an OHLCV DataFrame (tz-aware datetime index) — no data I/O here, that's
yfinance.py's job. Entry/exit rules, position sizing, and cost assumptions are a
separate rule layer (not yet decided, see the algo trading system brief's open items)
and are deliberately not part of this module.
"""

import pandas as pd


def _session_key(df: pd.DataFrame) -> pd.Series:
    """Session grouping key, currently calendar date.

    Correct for single-session instruments (e.g. SPY, only trades 09:30-16:00 ET).
    NOT correct yet for near-24h futures, where real session boundaries (Asia/Europe/US)
    are still an open decision — see "Market lineup / session schedule" in the brief.
    """
    return pd.Series(df.index.date, index=df.index)


def build_features(
    df: pd.DataFrame,
    zscore_window: int = 20,
    vol_window: int = 20,
    stoch_window: int = 14,
    rel_volume_window: int = 20,
    momentum_lookback: int = 5,
) -> pd.DataFrame:
    """Add the mean-reversion feature set to an OHLCV DataFrame."""
    df = df.copy()
    session = _session_key(df)

    rolling_mean = df["Close"].rolling(zscore_window).mean()
    rolling_std = df["Close"].rolling(zscore_window).std()
    df["zscore"] = (df["Close"] - rolling_mean) / rolling_std

    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    cum_tp_vol = (typical_price * df["Volume"]).groupby(session).cumsum()
    cum_vol = df["Volume"].groupby(session).cumsum()
    df["vwap"] = cum_tp_vol / cum_vol
    df["vwap_dist"] = (df["Close"] - df["vwap"]) / df["vwap"]

    rolling_low = df["Low"].rolling(stoch_window).min()
    rolling_high = df["High"].rolling(stoch_window).max()
    df["stoch_pct"] = (
        (df["Close"] - rolling_low) / (rolling_high - rolling_low + 1e-9) * 100
    )

    df["realized_vol"] = df["Close"].pct_change().rolling(vol_window).std()

    df["rel_volume"] = df["Volume"] / df["Volume"].rolling(rel_volume_window).mean()

    # Momentum is a filter (avoid fading a strong move), not a standalone signal.
    df["momentum"] = df["Close"].pct_change(momentum_lookback)

    first_ts = df.index.to_series().groupby(session).transform("first")
    last_ts = df.index.to_series().groupby(session).transform("last")
    df["minutes_since_open"] = (df.index - first_ts).dt.total_seconds() / 60
    # NOTE: minutes_to_close is derived from the last observed bar in the data,
    # not a real scheduled session-close time (that needs the session-schedule
    # decision above). Fine for offline feature construction, not for live use.
    df["minutes_to_close"] = (last_ts - df.index).dt.total_seconds() / 60

    return df


def make_labels(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.0) -> pd.DataFrame:
    """Add a mean-reversion label: did the z-score shrink in magnitude over `horizon` bars.

    `threshold` is the minimum shrink (in z-score units) to count as a positive label —
    kept configurable since exact trade-mechanics thresholds aren't decided yet. Also
    keeps the raw forward return, per the design doc's "probability (or expected forward
    return)" model-output framing — downstream code can pick whichever target it needs.
    Requires build_features() to have been called first (needs the zscore column).
    """
    if "zscore" not in df.columns:
        raise ValueError("Call build_features() first — 'zscore' column missing")

    feature_cols = [
        "zscore", "vwap_dist", "stoch_pct", "realized_vol", "rel_volume", "momentum",
    ]
    df = df.copy()
    future_zscore = df["zscore"].shift(-horizon)
    df["future_return"] = df["Close"].shift(-horizon) / df["Close"] - 1.0
    df["label"] = (future_zscore.abs() < (df["zscore"].abs() - threshold)).astype(float)
    df = df.dropna(subset=feature_cols + ["future_return", "label"])
    return df


if __name__ == "__main__":
    from yfinance import _intraday_path

    df = pd.read_csv(_intraday_path("SPY", "1m"), index_col=0, parse_dates=True)
    df = build_features(df)
    df = make_labels(df)
    print("Feature/label shape:", df.shape)
    print(
        df[
            ["Close", "zscore", "vwap_dist", "stoch_pct", "rel_volume", "label"]
        ].tail()
    )
    print("Label rate:", round(df["label"].mean(), 4))
