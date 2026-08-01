"""Small, transparent strategy signal builders used by the notebooks.

Each function returns a target exposure known at the end of the current bar.
``run_backtest`` shifts that exposure before applying the next bar's return.
This separation makes the signal logic easy to read and the execution timing
easy to test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _series(value: pd.Series, name: str = "close") -> pd.Series:
    result = pd.Series(value, dtype=float).rename(name)
    if result.empty or not result.index.is_unique or not result.index.is_monotonic_increasing:
        raise ValueError("Price series must have a non-empty, unique, increasing index")
    if (result <= 0).any() or not np.isfinite(result.to_numpy()).all():
        raise ValueError("Price series must contain finite, positive values")
    return result


def time_series_momentum_signal(
    close: pd.Series,
    *,
    lookback: int = 126,
    long_only: bool = True,
) -> pd.Series:
    """Use the sign of the trailing return as a momentum signal.

    With ``long_only=True`` the strategy is long when the lookback return is
    positive and flat otherwise. With ``long_only=False`` it is long or short.
    The signal uses only prices through the current bar; execution is delayed
    by ``run_backtest``.
    """

    if lookback <= 0:
        raise ValueError("lookback must be positive")
    close = _series(close)
    trailing_return = close / close.shift(lookback) - 1.0
    if long_only:
        signal = (trailing_return > 0.0).astype(float)
    else:
        signal = np.sign(trailing_return).astype(float)
    return signal.fillna(0.0).rename("target_position")


def bollinger_mean_reversion_signal(
    close: pd.Series,
    *,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.Series:
    """Return a long/flat Bollinger-band mean-reversion signal.

    Enter long when price is below the lower band. Hold until price rises above
    the moving-average center line. The bands are calculated from a rolling mean
    and standard deviation; the backtester supplies the one-bar execution delay.
    """

    if window <= 1 or num_std <= 0:
        raise ValueError("window must exceed 1 and num_std must be positive")
    close = _series(close)
    middle = close.rolling(window, min_periods=window).mean()
    width = close.rolling(window, min_periods=window).std(ddof=1)
    lower = middle - num_std * width

    signal = pd.Series(0.0, index=close.index, name="target_position")
    state = 0.0
    for timestamp in close.index:
        if pd.notna(lower.loc[timestamp]):
            if state == 0.0 and close.loc[timestamp] < lower.loc[timestamp]:
                state = 1.0
            elif state == 1.0 and close.loc[timestamp] > middle.loc[timestamp]:
                state = 0.0
        signal.loc[timestamp] = state
    return signal


def donchian_breakout_signal(
    close: pd.Series,
    *,
    high: pd.Series | None = None,
    low: pd.Series | None = None,
    entry_window: int = 100,
    exit_window: int = 50,
) -> pd.Series:
    """Return a long/flat prior-channel breakout signal.

    Enter when the close exceeds the highest high of the prior ``entry_window``
    bars. Exit when it falls below the lowest low of the prior ``exit_window``
    bars. The explicit one-bar shift in the channel prevents today's high/low
    from becoming part of today's own breakout threshold.
    """

    if entry_window <= 1 or exit_window <= 1:
        raise ValueError("entry_window and exit_window must exceed 1")
    close = _series(close)
    high = _series(high if high is not None else close, name="high")
    low = _series(low if low is not None else close, name="low")
    if not close.index.equals(high.index) or not close.index.equals(low.index):
        raise ValueError("close, high, and low must have identical indexes")

    prior_high = high.shift(1).rolling(entry_window, min_periods=entry_window).max()
    prior_low = low.shift(1).rolling(exit_window, min_periods=exit_window).min()
    signal = pd.Series(0.0, index=close.index, name="target_position")
    state = 0.0
    for timestamp in close.index:
        if state == 0.0 and pd.notna(prior_high.loc[timestamp]) and close.loc[timestamp] > prior_high.loc[timestamp]:
            state = 1.0
        elif state == 1.0 and pd.notna(prior_low.loc[timestamp]) and close.loc[timestamp] < prior_low.loc[timestamp]:
            state = 0.0
        signal.loc[timestamp] = state
    return signal
