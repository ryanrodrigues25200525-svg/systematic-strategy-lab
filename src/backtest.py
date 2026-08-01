"""Simple, explicit vectorized backtesting primitives.

This module is intentionally opinionated: target positions are shifted one bar
before returns are applied, and costs are charged on absolute exposure changes.
That makes the default workflow easy to inspect and difficult to accidentally
run with same-bar look-ahead.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .metrics import calculate_metrics


@dataclass(frozen=True)
class BacktestResult:
    """All time series and summary data produced by one backtest."""

    frame: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]

    @property
    def equity(self) -> pd.Series:
        return self.frame["equity"]

    @property
    def drawdown(self) -> pd.Series:
        return self.frame["drawdown"]


def moving_average_signal(
    close: pd.Series,
    *,
    fast_window: int = 50,
    slow_window: int = 200,
) -> pd.Series:
    """Return a long/flat signal: long when fast SMA exceeds slow SMA."""

    if fast_window <= 0 or slow_window <= 0 or fast_window >= slow_window:
        raise ValueError("Require 0 < fast_window < slow_window")
    close = pd.Series(close, dtype=float)
    fast = close.rolling(fast_window, min_periods=fast_window).mean()
    slow = close.rolling(slow_window, min_periods=slow_window).mean()
    return (fast > slow).astype(float).fillna(0.0).rename("target_position")


def volatility_target_position(
    close: pd.Series,
    signal: pd.Series,
    *,
    target_volatility: float = 0.15,
    volatility_window: int = 20,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Scale a signal to a target annualized volatility without look-ahead."""

    if target_volatility <= 0 or volatility_window <= 1 or max_leverage <= 0:
        raise ValueError("Volatility target, window, and leverage must be positive")
    close = pd.Series(close, dtype=float)
    signal = pd.Series(signal, index=close.index, dtype=float).fillna(0.0)
    realized_volatility = close.pct_change().rolling(volatility_window).std() * np.sqrt(252)
    scale = (target_volatility / realized_volatility).clip(lower=0.0, upper=max_leverage)
    # The signal and realized volatility are known at the close; run_backtest
    # shifts this target exposure before applying the next period's return.
    return (signal * scale.fillna(0.0)).clip(-max_leverage, max_leverage).rename("target_position")


def run_backtest(
    close: pd.Series,
    target_position: pd.Series,
    *,
    initial_capital: float = 100_000.0,
    transaction_cost_bps: float = 10.0,
    benchmark_returns: pd.Series | None = None,
    annualization: int = 252,
) -> BacktestResult:
    """Run a long/short or long/flat close-to-close backtest.

    A target position calculated at timestamp ``t`` is held for the return from
    ``t`` to ``t + 1``. In the aligned frame below this is represented by
    ``held_position = target_position.shift(1)``. Costs are a fraction of the
    absolute change in exposure, so a 0-to-1 entry costs one transaction and a
    1-to-0 exit costs another.
    """

    if initial_capital <= 0 or transaction_cost_bps < 0:
        raise ValueError("Initial capital must be positive and costs cannot be negative")
    close = pd.Series(close, dtype=float).rename("close")
    target = pd.Series(target_position, index=close.index, dtype=float).fillna(0.0)
    if not close.index.equals(target.index):
        raise ValueError("close and target_position must have identical indexes")
    if close.empty or not close.index.is_monotonic_increasing or not close.index.is_unique:
        raise ValueError("close must have a non-empty, unique, increasing index")
    if (close <= 0).any() or not np.isfinite(close.to_numpy()).all():
        raise ValueError("close prices must be finite and positive")

    asset_returns = close.pct_change().fillna(0.0)
    held_position = target.shift(1).fillna(0.0).rename("held_position")
    turnover = held_position.diff().abs().fillna(held_position.abs()).rename("turnover")
    cost_rate = transaction_cost_bps / 10_000.0
    costs = (turnover * cost_rate).rename("transaction_cost")
    gross_returns = (held_position * asset_returns).rename("gross_returns")
    net_returns = (gross_returns - costs).rename("net_returns")
    equity = (1.0 + net_returns).cumprod() * float(initial_capital)
    drawdown = (equity / equity.cummax() - 1.0).rename("drawdown")

    if benchmark_returns is None:
        benchmark = asset_returns.rename("benchmark_returns")
    else:
        benchmark = pd.Series(benchmark_returns, index=close.index, dtype=float).fillna(0.0)
        benchmark = benchmark.rename("benchmark_returns")

    frame = pd.concat(
        [close, target.rename("target_position"), held_position, asset_returns.rename("asset_returns"), gross_returns, turnover, costs, net_returns, benchmark, equity.rename("equity"), drawdown],
        axis=1,
    )

    change = held_position.diff().fillna(held_position).abs()
    trades = frame.loc[change > 1e-12, ["target_position", "held_position", "turnover", "transaction_cost"]].copy()
    trades.insert(0, "side", np.where(trades["held_position"] > trades["held_position"].shift(1).fillna(0.0), "increase", "decrease"))
    trades.index.name = "timestamp"
    metrics = dict(
        calculate_metrics(
            net_returns,
            benchmark_returns=benchmark,
            positions=held_position,
            turnover=turnover,
            trade_count=len(trades),
            annualization=annualization,
        )
    )
    return BacktestResult(frame=frame, trades=trades, metrics=metrics)


def split_time_series(
    data: pd.DataFrame,
    *,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> dict[str, pd.DataFrame]:
    """Split data chronologically into train, validation, and untouched test sets."""

    if not 0 < train_fraction < 1 or not 0 <= validation_fraction < 1:
        raise ValueError("Fractions must be in (0, 1) and [0, 1), respectively")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train plus validation fractions must leave a test period")
    if len(data) < 10:
        raise ValueError("Need at least 10 observations for a time-series split")

    train_end = int(len(data) * train_fraction)
    validation_end = int(len(data) * (train_fraction + validation_fraction))
    return {
        "train": data.iloc[:train_end].copy(),
        "validation": data.iloc[train_end:validation_end].copy(),
        "test": data.iloc[validation_end:].copy(),
    }
