"""Price-data loading and validation helpers.

The live loader is intentionally thin. The research code works with an explicit
OHLCV DataFrame so a later point-in-time data source can replace Yahoo Finance
without changing the backtester.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

REQUIRED_COLUMNS: Final[tuple[str, ...]] = ("open", "high", "low", "close", "volume")


def validate_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize a daily OHLCV DataFrame.

    The index must be a strictly increasing, unique DatetimeIndex. Prices and
    volume must be finite and non-negative; high/low relationships are checked
    when all OHLC columns are present.
    """

    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError("OHLCV data must use a pandas DatetimeIndex")
    if data.empty:
        raise ValueError("OHLCV data cannot be empty")
    if not data.index.is_unique or not data.index.is_monotonic_increasing:
        raise ValueError("OHLCV index must be unique and strictly increasing")

    normalized = data.copy()
    normalized.columns = [str(column).lower() for column in normalized.columns]
    missing = sorted(set(REQUIRED_COLUMNS) - set(normalized.columns))
    if missing:
        raise ValueError(f"OHLCV data is missing required columns: {missing}")

    normalized = normalized.loc[:, list(REQUIRED_COLUMNS)].astype(float)
    if not np.isfinite(normalized.to_numpy()).all():
        raise ValueError("OHLCV data contains non-finite values")
    if (normalized[list(REQUIRED_COLUMNS)] < 0).any().any():
        raise ValueError("OHLCV values cannot be negative")
    ohlc_max = normalized[["open", "close", "low"]].max(axis=1)
    ohlc_min = normalized[["open", "close", "high"]].min(axis=1)
    # Adjusted vendor data can differ by a few floating-point units after
    # corporate-action transformations. Keep the structural check, but do not
    # reject a rounding-level discrepancy that cannot affect a daily return.
    tolerance = 1e-8 * normalized[["open", "high", "low", "close"]].abs().max(axis=1).clip(lower=1.0)
    if (normalized["high"] + tolerance < ohlc_max).any():
        raise ValueError("High must be at least as large as open, close, and low")
    if (normalized["low"] - tolerance > ohlc_min).any():
        raise ValueError("Low must be no larger than open, close, and high")
    if (normalized["close"] <= 0).any():
        raise ValueError("Close prices must be positive")

    return normalized


def load_price_data(
    ticker: str,
    start: str,
    end: str,
    *,
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """Download and validate daily OHLCV data through ``yfinance``.

    ``end`` follows Yahoo Finance's usual exclusive-end convention. The import
    is local so unit tests and demo usage do not require the optional network
    dependency to be available.
    """

    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError("Install requirements.txt to use load_price_data") from exc

    if not ticker or not start or not end:
        raise ValueError("ticker, start, and end are required")

    raw = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=auto_adjust,
        progress=False,
        actions=False,
    )
    if raw.empty:
        raise ValueError(f"No data returned for {ticker!r} between {start} and {end}")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.columns = [str(column).lower() for column in raw.columns]
    if "adj close" in raw.columns and "close" not in raw.columns:
        raw = raw.rename(columns={"adj close": "close"})

    return validate_ohlcv(raw)


def load_price_panel(
    tickers: list[str] | tuple[str, ...],
    start: str,
    end: str,
    *,
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """Download a close-price panel for several assets through ``yfinance``.

    The result has one column per ticker and a common DatetimeIndex. Rows with
    a missing asset price are removed so a portfolio never silently treats a
    missing observation as a zero return.
    """

    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError("Install requirements.txt to use load_price_panel") from exc

    tickers = list(dict.fromkeys(str(ticker).upper() for ticker in tickers if str(ticker).strip()))
    if not tickers or not start or not end:
        raise ValueError("tickers, start, and end are required")

    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=auto_adjust,
        progress=False,
        actions=False,
        group_by="column",
    )
    if raw.empty:
        raise ValueError(f"No data returned for {tickers!r} between {start} and {end}")

    if isinstance(raw.columns, pd.MultiIndex):
        price_level = raw.columns.get_level_values(0)
        if "Close" in price_level:
            panel = raw.xs("Close", axis=1, level=0)
        elif "close" in [str(value).lower() for value in price_level]:
            close_key = next(value for value in price_level if str(value).lower() == "close")
            panel = raw.xs(close_key, axis=1, level=0)
        else:
            raise ValueError("Downloaded panel does not contain a close-price level")
    else:
        close_column = "Close" if "Close" in raw.columns else "close"
        panel = raw[[close_column]].rename(columns={close_column: tickers[0]})

    panel.columns = [str(column).upper() for column in panel.columns]
    panel = panel.sort_index().dropna(how="all").dropna(axis=1, how="all")
    if panel.empty or not panel.index.is_unique or not panel.index.is_monotonic_increasing:
        raise ValueError("Downloaded price panel must be non-empty and chronologically indexed")
    panel = panel.dropna(how="any").astype(float)
    if not np.isfinite(panel.to_numpy()).all() or (panel <= 0).any().any():
        raise ValueError("Price panel must contain finite, positive prices")
    return panel


def make_demo_ohlcv(
    periods: int = 1_500,
    *,
    seed: int = 7,
    start: str = "2015-01-01",
) -> pd.DataFrame:
    """Create deterministic OHLCV data for tests and offline notebook runs.

    The series is synthetic and must not be interpreted as market evidence. It
    contains mild regime changes so the example can exercise both trend and
    non-trend behavior without requiring a network connection.
    """

    if periods < 50:
        raise ValueError("periods must be at least 50")

    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, periods=periods)
    regime = np.where(np.arange(periods) % 500 < 250, 0.00035, -0.00005)
    shocks = rng.normal(loc=0.0, scale=0.009, size=periods)
    close = 100.0 * np.exp(np.cumsum(regime + shocks))
    overnight = rng.normal(0.0, 0.0015, size=periods)
    open_price = close * np.exp(overnight)
    spread = np.abs(rng.normal(0.004, 0.001, size=periods))
    high = np.maximum(open_price, close) * (1.0 + spread)
    low = np.minimum(open_price, close) * (1.0 - spread)
    volume = rng.integers(1_000_000, 5_000_000, size=periods).astype(float)

    return validate_ohlcv(
        pd.DataFrame(
            {
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            },
            index=dates,
        )
    )
