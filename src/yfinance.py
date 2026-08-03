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

INTRADAY_INTERVALS = ["1m", "4m"]
DAILY_INTERVAL = "1d"
UPDATE_PERIOD = "7d"


def _safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.=-]", "_", text)


def _cache_filename(
    ticker: str,
    interval: str,
    period: str,
    prefix: str = "",
    date_prefix: str | None = None,
) -> str:
    if date_prefix is None:
        date_prefix = dt.date.today().strftime("%m%d")
    safe_ticker = _safe_filename(ticker)
    name = f"{safe_ticker}_{interval}_{period}"
    if prefix:
        name = f"{prefix}_{name}"
    return f"{date_prefix}_{name}.csv"


def _cache_path(ticker: str, interval: str, period: str, prefix: str = "") -> Path:
    return DATA_DIR / _cache_filename(ticker, interval, period, prefix=prefix)


def _download_price_data(ticker: str, interval: str, period: str) -> pd.DataFrame:
    df = yf.download(ticker, interval=interval, period=period, progress=False)
    if df.empty:
        raise ValueError(
            f"No data returned for {ticker} with interval={interval} period={period}"
        )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df = df.rename_axis("datetime").reset_index()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime")
    return df


def _save_dataframe(df: pd.DataFrame, path: Path) -> None:
    try:
        df.to_csv(path)
    except OSError as exc:
        print(f"Warning: failed to write cache file {path}: {exc}")


def get_intraday_data(
    ticker: str, interval: str, period: str = UPDATE_PERIOD
) -> pd.DataFrame:
    cache_file = _cache_path(ticker, interval, period, prefix="intraday")
    df = _download_price_data(ticker, interval=interval, period=period)
    _save_dataframe(df, cache_file)
    return df


def get_daily_data(
    ticker: str, period: str = UPDATE_PERIOD, interval: str = DAILY_INTERVAL
) -> pd.DataFrame:
    df = _download_price_data(ticker, interval=interval, period=period)
    return df


def append_daily_data(ticker: str, df: pd.DataFrame) -> Path:
    cache_file = _cache_path(ticker, DAILY_INTERVAL, UPDATE_PERIOD, prefix="daily")
    if cache_file.exists():
        existing = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        combined = pd.concat([existing, df])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    else:
        combined = df
    _save_dataframe(combined, cache_file)
    return cache_file


def update_ticker_data(ticker: str) -> None:
    print(f"Updating {ticker}")
    for interval in INTRADAY_INTERVALS:
        try:
            df_intraday = get_intraday_data(
                ticker, interval=interval, period=UPDATE_PERIOD
            )
            print(f"  {interval} {UPDATE_PERIOD}: rows={len(df_intraday)}")
        except Exception as exc:
            print(f"  {interval} {UPDATE_PERIOD}: ERROR {exc}")

    try:
        daily_df = get_daily_data(ticker, period=UPDATE_PERIOD, interval=DAILY_INTERVAL)
        cache_path = append_daily_data(ticker, daily_df)
        print(f"  daily {UPDATE_PERIOD}: rows={len(daily_df)}, saved={cache_path.name}")
    except Exception as exc:
        print(f"  daily {UPDATE_PERIOD}: ERROR {exc}")


def update_all_tickers() -> None:
    for ticker in ALL_TICKERS:
        update_ticker_data(ticker)


def main() -> None:
    update_all_tickers()


if __name__ == "__main__":
    main()
