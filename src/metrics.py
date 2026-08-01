"""Consistent performance metrics for every research notebook."""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0 or not np.isfinite(denominator):
        return 0.0
    return float(numerator / denominator)


def calculate_metrics(
    returns: pd.Series,
    *,
    benchmark_returns: pd.Series | None = None,
    positions: pd.Series | None = None,
    turnover: pd.Series | None = None,
    trade_count: int | None = None,
    annualization: int = 252,
    risk_free_rate: float = 0.0,
) -> Mapping[str, float]:
    """Calculate annualized, risk-adjusted, and trading-activity metrics.

    ``returns`` should be net strategy returns. ``win_rate`` is the fraction of
    non-flat strategy periods with positive net return. ``turnover`` is the
    annualized sum of absolute exposure changes. Pass the actual turnover series
    for portfolios whose total gross exposure stays constant while asset weights
    change.
    """

    clean = pd.Series(returns, dtype=float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if clean.empty:
        raise ValueError("returns cannot be empty")
    periods = len(clean)
    years = periods / annualization
    equity = (1.0 + clean).cumprod()
    total_return = float(equity.iloc[-1] - 1.0)
    annualized_return = float((1.0 + total_return) ** (1.0 / years) - 1.0) if years else 0.0
    standard_deviation = float(clean.std(ddof=1))
    if not np.isfinite(standard_deviation):
        standard_deviation = 0.0
    annualized_volatility = float(standard_deviation * np.sqrt(annualization))
    daily_rf = risk_free_rate / annualization
    excess = clean - daily_rf
    # Preserve the sign of the conventional Sharpe formula when the mean is negative.
    sharpe_ratio = _safe_ratio(float(excess.mean()) * np.sqrt(annualization), standard_deviation)

    downside = excess.where(excess < 0.0, 0.0)
    downside_deviation = float(np.sqrt((downside**2).mean()) * np.sqrt(annualization))
    sortino_ratio = _safe_ratio(float(excess.mean()) * annualization, downside_deviation)

    rolling_max = equity.cummax()
    drawdown = equity / rolling_max - 1.0
    max_drawdown = float(drawdown.min())
    calmar_ratio = _safe_ratio(annualized_return, abs(max_drawdown))

    active = clean if positions is None else clean[pd.Series(positions, index=clean.index).abs() > 1e-12]
    active = active[active != 0.0]
    win_rate = float((active > 0.0).mean()) if not active.empty else 0.0

    if turnover is not None:
        turnover_series = pd.Series(turnover, index=clean.index, dtype=float).fillna(0.0)
        annualized_turnover = float(turnover_series.sum() / years)
    elif positions is None:
        annualized_turnover = 0.0
    else:
        position_series = pd.Series(positions, index=clean.index, dtype=float).fillna(0.0)
        annualized_turnover = float(position_series.diff().abs().fillna(position_series.abs()).sum() / years)

    benchmark_total_return = np.nan
    benchmark_relative_return = np.nan
    if benchmark_returns is not None:
        benchmark = pd.Series(benchmark_returns, index=clean.index, dtype=float).fillna(0.0)
        benchmark_total_return = float((1.0 + benchmark).prod() - 1.0)
        benchmark_relative_return = total_return - benchmark_total_return

    return {
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "annualized_turnover": annualized_turnover,
        "number_of_trades": float(trade_count if trade_count is not None else 0),
        "total_return_after_costs": total_return,
        "benchmark_total_return": benchmark_total_return,
        "benchmark_relative_return": benchmark_relative_return,
    }
