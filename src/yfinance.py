import datetime as dt
import importlib
import os
import re
import sys
from pathlib import Path

import pandas as pd


def _import_yfinance_package() -> object:
    local_dir = str(Path(__file__).resolve().parent)
    removed = False
    if local_dir in sys.path:
        sys.path.remove(local_dir)
        removed = True
    try:
        return importlib.import_module("yfinance")
    finally:
        if removed:
            sys.path.insert(0, local_dir)


yf = _import_yfinance_package()

# Directory to store cached/downloaded data (can be overridden with DATA_DIR env var)
DATA_DIR = Path(os.getenv("DATA_DIR", "/home/gerrit/Sync"))
if not DATA_DIR.is_absolute():
    DATA_DIR = Path(__file__).resolve().parent.parent / DATA_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)

ALL_TICKERS = [
    "6B=F",
    "6E=F",
    "6J=F",
    "BZ=F",
    "CL=F",
    "ES=F",
    "GC=F",
    "HG=F",
    "HO=F",
    "KC=F",
    "NG=F",
    "NQ=F",
    "PL=F",
    "RTY=F",
    "SB=F",
    "SI=F",
    "SPY",
    "YM=F",
    "ZN=F",
    "ZB=F",
    "ZC=F",
    "ZS=F",
    "ZW=F",
    "NIY=F",
    "NKD=F",
    "FEZ",
    "EWG",
    "EWU",
    "EWQ",
    "EWJ",
    "EWH",
    "ASHR",
    "INDO",
]

INTRADAY_INTERVALS = ["1m", "5m"]
INTRADAY_PERIOD = "7d"
INTRADAY_HISTORY_DAYS = 7
DAILY_INTERVAL = "1d"
DAILY_UPDATE_DAYS = 7
DAILY_FALLBACK_PERIOD = "max"


def _safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.=-]", "_", text)


def _intraday_filename(ticker: str, interval: str) -> str:
    safe_ticker = _safe_filename(ticker)
    return f"intraday_{safe_ticker}_{interval}_history.csv"


def _daily_filename(ticker: str) -> str:
    safe_ticker = _safe_filename(ticker)
    return f"daily_{safe_ticker}.csv"


def _intraday_path(ticker: str, interval: str) -> Path:
    return DATA_DIR / _intraday_filename(ticker, interval)


def _daily_path(ticker: str) -> Path:
    return DATA_DIR / _daily_filename(ticker)


def _download_price_data(
    ticker: str,
    interval: str,
    period: str | None = None,
    start: dt.date | None = None,
    end: dt.date | None = None,
) -> pd.DataFrame:
    download_args = {"interval": interval, "progress": False}
    if start is not None or end is not None:
        if period is not None:
            raise ValueError("Use either period or start/end, not both")
        if start is not None:
            download_args["start"] = start.isoformat()
        if end is not None:
            download_args["end"] = end.isoformat()
    elif period is not None:
        download_args["period"] = period
    else:
        raise ValueError("Either period or start/end must be supplied")

    df = yf.download(ticker, **download_args)
    if df.empty:
        raise ValueError(
            f"No data returned for {ticker} with interval={interval} period={period} start={start} end={end}"
        )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df = df.rename_axis("datetime").reset_index()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime")
    return df


def _save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_csv(path)
    except OSError as exc:
        print(f"Warning: failed to write cache file {path}: {exc}")


def get_intraday_data(
    ticker: str,
    interval: str,
    period: str = INTRADAY_PERIOD,
    start: dt.date | None = None,
    end: dt.date | None = None,
) -> pd.DataFrame:
    df = _download_price_data(
        ticker, interval=interval, period=period, start=start, end=end
    )
    return df


def get_daily_data(
    ticker: str,
    start: dt.date | None = None,
    end: dt.date | None = None,
    period: str | None = None,
    interval: str = DAILY_INTERVAL,
) -> pd.DataFrame:
    df = _download_price_data(
        ticker, interval=interval, period=period, start=start, end=end
    )
    return df


def append_daily_data(ticker: str, df: pd.DataFrame) -> Path:
    cache_file = _daily_path(ticker)
    if cache_file.exists():
        existing = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        combined = pd.concat([existing, df])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    else:
        combined = df
    _save_dataframe(combined, cache_file)
    return cache_file


def append_intraday_data(ticker: str, interval: str, df: pd.DataFrame) -> Path:
    cache_file = _intraday_path(ticker, interval)
    if cache_file.exists():
        existing = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        combined = pd.concat([existing, df])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    else:
        combined = df
    _save_dataframe(combined, cache_file)
    return cache_file


def update_daily_file(ticker: str) -> None:
    daily_file = _daily_path(ticker)
    if daily_file.exists():
        existing = pd.read_csv(daily_file, index_col=0, parse_dates=True)
        last_date = existing.index.max().date()
        if last_date >= dt.date.today():
            print("  daily: up to date")
            return
        start = last_date - dt.timedelta(days=1)
        end = dt.date.today() + dt.timedelta(days=1)
        new_df = get_daily_data(ticker, start=start, end=end)
    else:
        new_df = get_daily_data(ticker, period=DAILY_FALLBACK_PERIOD)

    if new_df.empty:
        print(f"  daily: no new data for {ticker}")
        return

    cache_path = append_daily_data(ticker, new_df)
    print(f"  daily: rows={len(new_df)}, saved={cache_path.name}")


def _intraday_start_end(ticker: str, interval: str) -> tuple[dt.date, dt.date]:
    cache_file = _intraday_path(ticker, interval)
    earliest_allowed = dt.date.today() - dt.timedelta(days=INTRADAY_HISTORY_DAYS)
    if cache_file.exists():
        existing = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        last_ts = existing.index.max()
        start = max(last_ts.date() - dt.timedelta(days=1), earliest_allowed)
    else:
        start = earliest_allowed
    end = dt.date.today() + dt.timedelta(days=1)
    return start, end


def update_ticker_data(ticker: str) -> None:
    print(f"Updating {ticker}")
    for interval in INTRADAY_INTERVALS:
        try:
            start, end = _intraday_start_end(ticker, interval)
            df_intraday = get_intraday_data(
                ticker, interval=interval, period=None, start=start, end=end
            )
            cache_path = append_intraday_data(ticker, interval, df_intraday)
            print(f"  {interval}: rows={len(df_intraday)}, saved={cache_path.name}")
        except Exception as exc:
            print(f"  {interval}: ERROR {exc}")

    try:
        update_daily_file(ticker)
    except Exception as exc:
        print(f"  daily: ERROR {exc}")


def update_all_tickers() -> None:
    for ticker in ALL_TICKERS:
        update_ticker_data(ticker)


def main() -> None:
    update_all_tickers()


if __name__ == "__main__":
    main()
