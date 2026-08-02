import datetime as dt
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score


def get_intraday_data(
    ticker: str, interval: str = "5m", period: str = "30d"
) -> pd.DataFrame:
    """Fetch intraday OHLCV data from yfinance for a symbol."""
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


def get_daily_data(
    ticker: str = "SPY", period: str = "5y", interval: str = "1d"
) -> pd.DataFrame:
    """Fetch daily OHLCV data from yfinance for a symbol over the past 5 years."""
    df = yf.download(ticker, interval=interval, period=period, progress=False)
    if df.empty:
        raise ValueError(
            f"No daily data returned for {ticker} with interval={interval} period={period}"
        )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df = df.rename_axis("datetime").reset_index()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime")
    return df


def feature_engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Add a stronger set of intraday technical and momentum features."""
    df = df.copy()
    df["return_1"] = df["Close"].pct_change(1)
    df["return_3"] = df["Close"].pct_change(3)
    df["return_6"] = df["Close"].pct_change(6)
    df["return_10"] = df["Close"].pct_change(10)
    df["return_15"] = df["Close"].pct_change(15)
    df["return_30"] = df["Close"].pct_change(30)

    df["ema_5"] = df["Close"].ewm(span=5, adjust=False).mean()
    df["ema_15"] = df["Close"].ewm(span=15, adjust=False).mean()
    df["ema_30"] = df["Close"].ewm(span=30, adjust=False).mean()
    df["ema_5_15_diff"] = df["ema_5"] - df["ema_15"]
    df["ema_15_30_diff"] = df["ema_15"] - df["ema_30"]
    df["ema_5_slope"] = df["ema_5"].diff(1)
    df["ema_15_slope"] = df["ema_15"].diff(1)

    df["rolling_mean_20"] = df["Close"].rolling(20).mean()
    df["rolling_std_20"] = df["Close"].rolling(20).std()
    df["bollinger_pct"] = (df["Close"] - df["rolling_mean_20"]) / df["rolling_std_20"]

    true_range = np.maximum(
        df["High"] - df["Low"],
        np.maximum(
            (df["High"] - df["Close"].shift(1)).abs(),
            (df["Low"] - df["Close"].shift(1)).abs(),
        ),
    )
    df["atr"] = true_range.rolling(14).mean()
    df["atr_pct"] = df["atr"] / df["Close"]

    df["volatility_15"] = df["return_1"].rolling(15).std()
    df["volatility_30"] = df["return_1"].rolling(30).std()

    df["range_pct"] = (df["High"] - df["Low"]) / df["Close"]
    df["close_loc"] = (df["Close"] - df["Low"]) / (df["High"] - df["Low"] + 1e-9)
    df["volume_change"] = df["Volume"].pct_change(1)
    df["volume_rolling_mean"] = df["Volume"].rolling(20).mean()

    close_diff = df["Close"].diff(1)
    gain = close_diff.clip(lower=0)
    loss = (-close_diff).clip(lower=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    df["rsi_14"] = 100 - 100 / (1 + rs)

    macd_fast = df["Close"].ewm(span=12, adjust=False).mean()
    macd_slow = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = macd_fast - macd_slow
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_diff"] = df["macd"] - df["macd_signal"]

    df["time_of_day"] = df.index.hour + df.index.minute / 60.0
    df["time_bucket"] = pd.cut(
        df["time_of_day"], bins=[0, 8, 10, 12, 14, 16, 24], labels=False
    )
    df["hour"] = df.index.hour
    df["minute"] = df.index.minute

    df = df.dropna()
    return df


def make_labels(
    df: pd.DataFrame, horizon: int = 3, threshold: float = 0.005
) -> pd.DataFrame:
    """Create a binary directional label for the next horizon using a stronger threshold."""
    df = df.copy()
    df["future_return"] = df["Close"].shift(-horizon) / df["Close"] - 1.0
    df["label"] = (df["future_return"] > threshold).astype(int)
    df = df.dropna(subset=["future_return"])
    return df


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    features = [
        "return_1",
        "return_3",
        "return_6",
        "ema_5_15_diff",
        "ema_15_30_diff",
        "atr",
        "volatility_15",
        "range_pct",
        "time_bucket",
    ]
    X = df[features].copy()
    y = df["label"].copy()
    return X, y


def train_and_evaluate(X: pd.DataFrame, y: pd.Series) -> None:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, shuffle=False
    )

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("=== Model evaluation ===")
    print(classification_report(y_test, y_pred, digits=4))
    print("ROC AUC:", round(roc_auc_score(y_test, y_proba), 4))
    print("Positive label frequency:", round(y_test.mean(), 4))


def run_example(
    ticker: str = "SPY",
    interval: str = "5m",
    period: str = "30d",
    horizon: int = 3,
    threshold: float = 0.005,
) -> None:
    print(f"Fetching intraday data for {ticker} interval={interval} period={period}")
    df = get_intraday_data(ticker, interval=interval, period=period)
    daily_df = get_daily_data(ticker=ticker, period="5y", interval="1d")

    print("Daily data shape:", daily_df.shape)
    print(daily_df[["Open", "High", "Low", "Close", "Volume"]].head())

    df = feature_engineer(df)
    df = make_labels(df, horizon=horizon, threshold=threshold)

    print("Sample data shape:", df.shape)
    print(
        df[
            ["Close", "return_1", "ema_5_15_diff", "atr", "future_return", "label"]
        ].tail()
    )

    X, y = build_feature_matrix(df)
    train_and_evaluate(X, y)


def run_experiments(
    ticker: str = "SPY",
    interval: str = "5m",
    period: str = "30d",
    threshold: float = 0.005,
) -> None:
    print("=== Experiment 1: 3-bar horizon ===")
    run_example(
        ticker=ticker, interval=interval, period=period, horizon=3, threshold=threshold
    )

    print("\n=== Experiment 2: 6-bar horizon ===")
    run_example(
        ticker=ticker, interval=interval, period=period, horizon=6, threshold=threshold
    )


if __name__ == "__main__":
    run_experiments()
