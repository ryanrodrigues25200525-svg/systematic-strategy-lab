"""Small plotting helpers shared by notebooks."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


def plot_equity_curve(frame: pd.DataFrame, *, title: str = "Equity curve") -> plt.Axes:
    ax = frame["equity"].plot(figsize=(12, 5), label="Strategy")
    if "benchmark_returns" in frame:
        benchmark_equity = (1.0 + frame["benchmark_returns"]).cumprod() * frame["equity"].iloc[0]
        benchmark_equity.plot(ax=ax, label="Buy and hold", alpha=0.8)
    ax.set_title(title)
    ax.set_ylabel("Portfolio value")
    ax.legend()
    ax.grid(alpha=0.25)
    return ax


def plot_drawdown(frame: pd.DataFrame, *, title: str = "Drawdown") -> plt.Axes:
    ax = (100.0 * frame["drawdown"]).plot.area(figsize=(12, 3), color="firebrick", alpha=0.75)
    ax.set_title(title)
    ax.set_ylabel("Drawdown (%)")
    ax.grid(alpha=0.25)
    return ax


def monthly_returns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a year-by-month net-return table for a result frame."""

    monthly = (1.0 + frame["net_returns"]).resample(pd.offsets.MonthEnd()).prod() - 1.0
    table = monthly.to_frame("return")
    table["year"] = table.index.year
    table["month"] = table.index.month
    return table.pivot(index="year", columns="month", values="return").reindex(columns=range(1, 13))
