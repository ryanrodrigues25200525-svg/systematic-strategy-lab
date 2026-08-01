"""Helpers for evaluating results on a specified chronological period."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .backtest import BacktestResult
from .metrics import calculate_metrics


def metrics_for_period(result: BacktestResult, period_index: pd.Index) -> dict[str, float]:
    """Recalculate metrics for one period without resetting the full backtest."""

    frame = result.frame.loc[period_index]
    position_column = "held_position" if "held_position" in frame.columns else "held_gross_exposure"
    return dict(
        calculate_metrics(
            frame["net_returns"],
            benchmark_returns=frame["benchmark_returns"],
            positions=frame[position_column],
            turnover=frame["turnover"],
            trade_count=int((frame["turnover"] > 1e-12).sum()),
        )
    )


def comparison_table(
    results: Mapping[str, BacktestResult],
    period_index: pd.Index,
) -> pd.DataFrame:
    """Create a strategy-by-metric table for a common period."""

    return pd.DataFrame({name: metrics_for_period(result, period_index) for name, result in results.items()}).T
