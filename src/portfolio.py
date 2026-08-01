"""Multi-asset portfolio backtesting and transparent weight builders."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .metrics import calculate_metrics


@dataclass(frozen=True)
class PortfolioBacktestResult:
    """Time series, weights, trade log, and metrics for a portfolio backtest."""

    frame: pd.DataFrame
    target_weights: pd.DataFrame
    held_weights: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]


def _validate_panel(close: pd.DataFrame) -> pd.DataFrame:
    panel = close.astype(float).copy()
    panel.columns = [str(column).upper() for column in panel.columns]
    if panel.empty or panel.columns.has_duplicates:
        raise ValueError("Price panel must be non-empty with unique assets")
    if not panel.index.is_unique or not panel.index.is_monotonic_increasing:
        raise ValueError("Price panel index must be unique and increasing")
    if not np.isfinite(panel.to_numpy()).all() or (panel <= 0).any().any():
        raise ValueError("Price panel must contain finite, positive prices")
    return panel


def _month_start_mask(index: pd.DatetimeIndex) -> pd.Series:
    month = pd.Series(index.to_period("M"), index=index)
    return month.ne(month.shift(1))


def _rebalance_weights(
    index: pd.DatetimeIndex,
    columns: pd.Index,
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    """Hold each monthly decision until the next monthly decision."""

    mask = _month_start_mask(index)
    weights = pd.DataFrame(np.nan, index=index, columns=columns)
    weights.loc[mask] = candidates.loc[mask]
    return weights.ffill().fillna(0.0)


def equal_weight_weights(close: pd.DataFrame) -> pd.DataFrame:
    """Return fixed equal weights across all assets."""

    panel = _validate_panel(close)
    return pd.DataFrame(1.0 / len(panel.columns), index=panel.index, columns=panel.columns)


def cross_sectional_momentum_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 126,
    top_n: int = 3,
    skip_recent: int = 0,
) -> pd.DataFrame:
    """Select the top ``top_n`` assets by trailing return at monthly rebalance.

    ``skip_recent`` omits the most recent observations from the score. A value
    of 21 is a practical ETF approximation of the academic 12-1 momentum rule.
    """

    panel = _validate_panel(close)
    if lookback <= 0 or top_n <= 0 or top_n > len(panel.columns) or skip_recent < 0:
        raise ValueError("Require positive lookback/top_n, non-negative skip_recent, and top_n <= assets")
    score = panel.shift(skip_recent).pct_change(lookback).shift(1)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        valid = score.loc[timestamp].dropna()
        selected = valid.nlargest(top_n).index
        if len(selected):
            candidates.loc[timestamp, selected] = 1.0 / len(selected)
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def short_term_reversal_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 21,
    top_n: int = 3,
) -> pd.DataFrame:
    """Select recent losers, a long-only adaptation of short-term reversal."""

    panel = _validate_panel(close)
    if lookback <= 0 or top_n <= 0 or top_n > len(panel.columns):
        raise ValueError("Require positive lookback/top_n and top_n <= number of assets")
    score = panel.pct_change(lookback).shift(1)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        valid = score.loc[timestamp].dropna()
        selected = valid.nsmallest(top_n).index
        if len(selected):
            candidates.loc[timestamp, selected] = 1.0 / len(selected)
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def fifty_two_week_high_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 252,
    top_n: int = 3,
) -> pd.DataFrame:
    """Select assets closest to their prior 52-week high at monthly rebalance."""

    panel = _validate_panel(close)
    if lookback <= 1 or top_n <= 0 or top_n > len(panel.columns):
        raise ValueError("Require lookback > 1, positive top_n, and top_n <= assets")
    prior_close = panel.shift(1)
    prior_high = prior_close.rolling(lookback).max()
    score = prior_close / prior_high
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        valid = score.loc[timestamp].dropna()
        selected = valid.nlargest(top_n).index
        if len(selected):
            candidates.loc[timestamp, selected] = 1.0 / len(selected)
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def downside_volatility_momentum_weights(
    close: pd.DataFrame,
    *,
    momentum_lookback: int = 252,
    skip_recent: int = 21,
    volatility_lookback: int = 60,
    top_n: int = 3,
) -> pd.DataFrame:
    """Select 12-1 momentum winners and scale them by inverse downside volatility.

    This is a transparent long-only ETF adaptation of newer volatility-managed
    momentum research. It is not an exact replication of stock-level papers.
    """

    panel = _validate_panel(close)
    if (
        momentum_lookback <= 0
        or skip_recent < 0
        or volatility_lookback <= 1
        or top_n <= 0
        or top_n > len(panel.columns)
    ):
        raise ValueError("Invalid momentum, skip, volatility, or top_n parameter")
    momentum = panel.shift(skip_recent).pct_change(momentum_lookback).shift(1)
    daily_returns = panel.pct_change()
    downside = daily_returns.where(daily_returns < 0.0, 0.0)
    downside_volatility = downside.rolling(volatility_lookback).std(ddof=1).shift(1)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        valid_momentum = momentum.loc[timestamp].dropna()
        selected = valid_momentum.nlargest(top_n).index
        risk = downside_volatility.loc[timestamp, selected].dropna()
        risk = risk[risk > 0.0]
        if not risk.empty:
            inverse = 1.0 / risk
            candidates.loc[timestamp, inverse.index] = inverse / inverse.sum()
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def volatility_managed_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 21,
    target_volatility: float = 0.15,
    max_exposure: float = 1.0,
) -> pd.DataFrame:
    """Scale equal-weight exposure down when trailing portfolio volatility rises.

    This is a long-only monthly ETF adaptation of volatility-managed portfolio
    research. Unused exposure is treated as cash by the simple backtester.
    """

    panel = _validate_panel(close)
    if lookback <= 1 or target_volatility <= 0 or not 0 < max_exposure <= 1:
        raise ValueError("Require lookback > 1, positive target volatility, and max_exposure in (0, 1]")
    base_weight = 1.0 / len(panel.columns)
    market_returns = panel.pct_change().mean(axis=1)
    annualized_volatility = market_returns.rolling(lookback).std(ddof=1).shift(1) * np.sqrt(252)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        volatility = annualized_volatility.loc[timestamp]
        if pd.notna(volatility) and volatility > 0:
            scale = min(max_exposure, target_volatility / float(volatility))
            candidates.loc[timestamp] = base_weight * scale
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def volatility_managed_momentum_weights(
    close: pd.DataFrame,
    *,
    momentum_lookback: int = 126,
    top_n: int = 3,
    volatility_lookback: int = 21,
    target_volatility: float = 0.15,
) -> pd.DataFrame:
    """Combine cross-sectional momentum with a monthly volatility throttle."""

    panel = _validate_panel(close)
    if (
        momentum_lookback <= 0
        or top_n <= 0
        or top_n > len(panel.columns)
        or volatility_lookback <= 1
        or target_volatility <= 0
    ):
        raise ValueError("Invalid momentum, top_n, volatility, or target-volatility parameter")
    score = panel.pct_change(momentum_lookback).shift(1)
    market_returns = panel.pct_change().mean(axis=1)
    annualized_volatility = market_returns.rolling(volatility_lookback).std(ddof=1).shift(1) * np.sqrt(252)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        valid = score.loc[timestamp].dropna()
        volatility = annualized_volatility.loc[timestamp]
        if valid.empty or pd.isna(volatility) or volatility <= 0:
            continue
        selected = valid.nlargest(top_n).index
        scale = min(1.0, target_volatility / float(volatility))
        candidates.loc[timestamp, selected] = scale / len(selected)
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def dual_momentum_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 252,
    top_n: int = 1,
    risk_assets: tuple[str, ...] = ("SPY", "QQQ", "IWM", "EFA", "EEM"),
    defensive_assets: tuple[str, ...] = ("TLT", "GLD"),
) -> pd.DataFrame:
    """Use relative momentum among risk assets plus an absolute momentum filter."""

    panel = _validate_panel(close)
    if lookback <= 0 or top_n <= 0:
        raise ValueError("lookback and top_n must be positive")
    risk = [asset for asset in risk_assets if asset in panel.columns]
    defensive = [asset for asset in defensive_assets if asset in panel.columns]
    if not risk or not defensive or top_n > len(risk):
        raise ValueError("risk_assets and defensive_assets must overlap the price panel")
    score = panel.pct_change(lookback).shift(1)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        risk_scores = score.loc[timestamp, risk].dropna().nlargest(top_n)
        if not risk_scores.empty and (risk_scores > 0).all():
            candidates.loc[timestamp, risk_scores.index] = 1.0 / len(risk_scores)
            continue
        defensive_scores = score.loc[timestamp, defensive].dropna()
        defensive_scores = defensive_scores[defensive_scores > 0].nlargest(top_n)
        if not defensive_scores.empty:
            candidates.loc[timestamp, defensive_scores.index] = 1.0 / len(defensive_scores)
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def trend_following_rotation_weights(
    close: pd.DataFrame,
    *,
    trend_window: int = 200,
    momentum_lookback: int = 126,
    top_n: int = 1,
    risk_assets: tuple[str, ...] = ("SPY", "QQQ", "IWM", "EFA", "EEM"),
    defensive_assets: tuple[str, ...] = ("TLT", "GLD"),
) -> pd.DataFrame:
    """Hold assets in positive long-term trends; rotate to defensive assets otherwise."""

    panel = _validate_panel(close)
    if trend_window <= 1 or momentum_lookback <= 0 or top_n <= 0:
        raise ValueError("Require trend_window > 1 and positive momentum_lookback/top_n")
    risk = [asset for asset in risk_assets if asset in panel.columns]
    defensive = [asset for asset in defensive_assets if asset in panel.columns]
    if not risk or not defensive or top_n > len(risk):
        raise ValueError("risk_assets and defensive_assets must overlap the price panel")
    prior_close = panel.shift(1)
    trend = prior_close > prior_close.rolling(trend_window).mean()
    score = panel.pct_change(momentum_lookback).shift(1)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        eligible = trend.loc[timestamp, risk]
        eligible = eligible[eligible].index
        risk_scores = score.loc[timestamp, eligible].dropna().nlargest(top_n)
        if not risk_scores.empty and (risk_scores > 0).all():
            candidates.loc[timestamp, risk_scores.index] = 1.0 / len(risk_scores)
            continue
        defensive_scores = score.loc[timestamp, defensive].dropna()
        defensive_scores = defensive_scores[defensive_scores > 0].nlargest(top_n)
        if not defensive_scores.empty:
            candidates.loc[timestamp, defensive_scores.index] = 1.0 / len(defensive_scores)
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def volatility_regime_rotation_weights(
    close: pd.DataFrame,
    *,
    volatility_lookback: int = 21,
    high_volatility_threshold: float = 0.20,
    momentum_lookback: int = 126,
    top_n: int = 1,
    market_asset: str = "SPY",
    risk_assets: tuple[str, ...] = ("SPY", "QQQ", "IWM", "EFA", "EEM"),
    defensive_assets: tuple[str, ...] = ("TLT", "GLD"),
) -> pd.DataFrame:
    """Use momentum in calm markets and defensive momentum in high-volatility markets."""

    panel = _validate_panel(close)
    if volatility_lookback <= 1 or momentum_lookback <= 0 or high_volatility_threshold <= 0 or top_n <= 0:
        raise ValueError("Invalid volatility, momentum, threshold, or top_n parameter")
    market_asset = market_asset.upper()
    risk = [asset for asset in risk_assets if asset in panel.columns]
    defensive = [asset for asset in defensive_assets if asset in panel.columns]
    if market_asset not in panel.columns or not risk or not defensive or top_n > len(risk):
        raise ValueError("market_asset, risk_assets, and defensive_assets must overlap the price panel")
    volatility = panel[market_asset].pct_change().rolling(volatility_lookback).std(ddof=1).shift(1) * np.sqrt(252)
    score = panel.pct_change(momentum_lookback).shift(1)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        market_volatility = volatility.loc[timestamp]
        if pd.isna(market_volatility):
            continue
        universe = defensive if market_volatility > high_volatility_threshold else risk
        selected_scores = score.loc[timestamp, universe].dropna()
        selected_scores = selected_scores[selected_scores > 0].nlargest(top_n)
        if not selected_scores.empty:
            candidates.loc[timestamp, selected_scores.index] = 1.0 / len(selected_scores)
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def time_series_momentum_portfolio_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 126,
) -> pd.DataFrame:
    """Take equal gross long/short exposure based on each asset's own trend.

    Positive trailing momentum receives a long sign and negative momentum a
    short sign. This is closer to a managed-futures-style time-series momentum
    abstraction than the long-only strategies in the other notebooks, but it
    omits futures roll, financing, margin, and borrow costs.
    """

    panel = _validate_panel(close)
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    score = panel.pct_change(lookback).shift(1)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        valid = score.loc[timestamp].dropna()
        if not valid.empty:
            signs = np.sign(valid)
            candidates.loc[timestamp, valid.index] = signs / signs.abs().sum()
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def low_beta_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 252,
    top_n: int = 3,
    market_asset: str = "SPY",
) -> pd.DataFrame:
    """Select the assets with the lowest trailing beta to a market asset."""

    panel = _validate_panel(close)
    market_asset = market_asset.upper()
    if lookback <= 1 or top_n <= 0 or top_n > len(panel.columns) or market_asset not in panel.columns:
        raise ValueError("Require lookback > 1, valid top_n, and market_asset in the panel")
    returns = panel.pct_change()
    market_returns = returns[market_asset]
    market_variance = market_returns.rolling(lookback).var(ddof=1).shift(1)
    beta = pd.DataFrame(index=panel.index, columns=panel.columns, dtype=float)
    for asset in panel.columns:
        beta[asset] = returns[asset].rolling(lookback).cov(market_returns).shift(1) / market_variance
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        valid = beta.loc[timestamp].dropna()
        selected = valid.nsmallest(top_n).index
        if len(selected):
            candidates.loc[timestamp, selected] = 1.0 / len(selected)
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def minimum_variance_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 60,
    ridge: float = 1e-8,
) -> pd.DataFrame:
    """Build a long-only sample minimum-variance portfolio monthly.

    Negative unconstrained weights are clipped to zero before normalization. A
    small diagonal ridge keeps the inverse covariance calculation stable.
    """

    panel = _validate_panel(close)
    if lookback <= 1 or ridge < 0:
        raise ValueError("lookback must exceed 1 and ridge cannot be negative")
    returns = panel.pct_change()
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        history = returns.loc[:timestamp].iloc[:-1].tail(lookback).dropna(how="any")
        if len(history) < lookback:
            continue
        covariance = history.cov().to_numpy(dtype=float)
        scale = float(np.trace(covariance) / len(panel.columns)) if np.isfinite(covariance).all() else 0.0
        covariance = covariance + np.eye(len(panel.columns)) * ridge * max(scale, 1.0)
        inverse = np.linalg.pinv(covariance)
        raw = np.clip(inverse @ np.ones(len(panel.columns)), 0.0, None)
        if raw.sum() > 0:
            candidates.loc[timestamp] = raw / raw.sum()
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def momentum_volatility_scaled_weights(
    close: pd.DataFrame,
    *,
    momentum_lookback: int = 252,
    skip_recent: int = 21,
    top_n: int = 3,
    volatility_lookback: int = 126,
    target_volatility: float = 0.12,
) -> pd.DataFrame:
    """Scale a 12-1 momentum portfolio by its own trailing realized volatility."""

    panel = _validate_panel(close)
    if (
        momentum_lookback <= 0
        or skip_recent < 0
        or top_n <= 0
        or top_n > len(panel.columns)
        or volatility_lookback <= 1
        or target_volatility <= 0
    ):
        raise ValueError("Invalid momentum, skip, top_n, volatility, or target-volatility parameter")
    base = cross_sectional_momentum_weights(
        panel, lookback=momentum_lookback, skip_recent=skip_recent, top_n=top_n
    )
    asset_returns = panel.pct_change().fillna(0.0)
    base_returns = (base.shift(1).fillna(0.0) * asset_returns).sum(axis=1)
    strategy_volatility = base_returns.rolling(volatility_lookback).std(ddof=1).shift(1) * np.sqrt(252)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        volatility = strategy_volatility.loc[timestamp]
        base_weights = base.loc[timestamp]
        if pd.notna(volatility) and volatility > 0 and base_weights.abs().sum() > 0:
            scale = min(1.0, target_volatility / float(volatility))
            candidates.loc[timestamp] = base_weights * scale
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def low_volatility_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 60,
    top_n: int = 3,
) -> pd.DataFrame:
    """Select the ``top_n`` assets with the lowest trailing volatility monthly."""

    panel = _validate_panel(close)
    if lookback <= 1 or top_n <= 0 or top_n > len(panel.columns):
        raise ValueError("Require lookback > 1, positive top_n, and top_n <= assets")
    volatility = panel.pct_change().rolling(lookback).std(ddof=1).shift(1)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        valid = volatility.loc[timestamp].dropna()
        selected = valid.nsmallest(top_n).index
        if len(selected):
            candidates.loc[timestamp, selected] = 1.0 / len(selected)
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def inverse_volatility_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 60,
) -> pd.DataFrame:
    """Weight assets in inverse proportion to trailing volatility monthly."""

    panel = _validate_panel(close)
    if lookback <= 1:
        raise ValueError("lookback must exceed 1")
    volatility = panel.pct_change().rolling(lookback).std(ddof=1).shift(1)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        valid = volatility.loc[timestamp].dropna()
        if not valid.empty and (valid > 0).all():
            inverse = 1.0 / valid
            candidates.loc[timestamp, inverse.index] = inverse / inverse.sum()
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def run_portfolio_backtest(
    close: pd.DataFrame,
    target_weights: pd.DataFrame,
    *,
    initial_capital: float = 100_000.0,
    transaction_cost_bps: float = 10.0,
    benchmark_returns: pd.Series | None = None,
    annualization: int = 252,
) -> PortfolioBacktestResult:
    """Backtest long-only or long/short weights with one-bar execution delay."""

    if initial_capital <= 0 or transaction_cost_bps < 0:
        raise ValueError("Initial capital must be positive and costs cannot be negative")
    panel = _validate_panel(close)
    weights = target_weights.reindex(index=panel.index, columns=panel.columns).fillna(0.0).astype(float)
    if (weights.abs().sum(axis=1) > 1.0000001).any():
        raise ValueError("Absolute portfolio exposure cannot exceed 1.0 in this simple backtester")

    asset_returns = panel.pct_change().fillna(0.0)
    held = weights.shift(1).fillna(0.0)
    changes = held.diff().fillna(held)
    turnover = changes.abs().sum(axis=1).rename("turnover")
    gross_returns = (held * asset_returns).sum(axis=1).rename("gross_returns")
    transaction_cost = (turnover * transaction_cost_bps / 10_000.0).rename("transaction_cost")
    net_returns = (gross_returns - transaction_cost).rename("net_returns")
    equity = ((1.0 + net_returns).cumprod() * float(initial_capital)).rename("equity")
    drawdown = (equity / equity.cummax() - 1.0).rename("drawdown")
    benchmark = asset_returns.iloc[:, 0].rename("benchmark_returns") if benchmark_returns is None else pd.Series(benchmark_returns, index=panel.index, dtype=float).fillna(0.0).rename("benchmark_returns")
    frame = pd.concat(
        [gross_returns, turnover, transaction_cost, net_returns, benchmark, held.abs().sum(axis=1).rename("held_gross_exposure"), equity, drawdown],
        axis=1,
    )

    trade_rows = changes.stack().rename("delta_weight").to_frame()
    trade_rows = trade_rows.loc[trade_rows["delta_weight"].abs() > 1e-12]
    trade_rows.index.names = ["timestamp", "asset"]
    trade_rows["turnover"] = trade_rows["delta_weight"].abs()
    trade_rows["side"] = np.where(trade_rows["delta_weight"] > 0, "increase", "decrease")
    trade_rows["transaction_cost"] = trade_rows["turnover"] * transaction_cost_bps / 10_000.0
    metrics = dict(
        calculate_metrics(
            net_returns,
            benchmark_returns=benchmark,
            positions=frame["held_gross_exposure"],
            turnover=turnover,
            trade_count=len(trade_rows),
            annualization=annualization,
        )
    )
    return PortfolioBacktestResult(
        frame=frame,
        target_weights=weights,
        held_weights=held,
        trades=trade_rows,
        metrics=metrics,
    )
