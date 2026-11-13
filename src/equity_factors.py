"""Residual momentum, long-horizon reversal, and quality-composite research rules.

The three rules in this module come from equity-factor literature and are
adapted to a transparent ETF universe or to published factor returns. They are
not stock-level replications: with ETFs we cannot sort on individual securities,
and with a single market factor we cannot reproduce a three-factor regression.

References
----------
- Blitz, Huij and Martens (2011), *Residual momentum*: estimate factor
  exposures over 36 months, then rank on the standardised trailing residual
  return, skipping the most recent month.
- DeBondt and Thaler (1985), *Does the stock market overreact?*: rank on
  three-to-five years of past return and buy prior losers.
- Asness, Frazzini and Pedersen (2019), *Quality minus junk*: combine
  profitability, growth, safety and payout into a quality score.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .portfolio import _validate_panel


def _month_end_panel(close: pd.DataFrame) -> pd.DataFrame:
    """Convert a daily close panel into month-end closes."""

    return close.resample("ME").last()


def _decide_at_month_start(monthly_weights: pd.DataFrame, daily_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Broadcast a month-end decision onto the following daily trading calendar.

    A weight decided at the close of month ``m`` becomes the target exposure on
    the first trading day of month ``m + 1``. The portfolio backtester adds its
    usual one-bar execution delay on top, so the decision still cannot earn the
    return that produced it.
    """

    daily = monthly_weights.reindex(daily_index, method="ffill").fillna(0.0)
    return daily.astype(float)


def _validate_shares(long_share: float, short_share: float, bottom_n: int) -> None:
    if long_share < 0.0 or short_share < 0.0:
        raise ValueError("long_share and short_share must be non-negative")
    if long_share + short_share > 1.0 + 1e-9:
        raise ValueError("Gross exposure cannot exceed 1.0 in this simple backtester")
    if bottom_n < 0:
        raise ValueError("bottom_n must be non-negative")
    if (short_share > 0.0) != (bottom_n > 0):
        raise ValueError("short_share and bottom_n must be used together")


def _select_extremes(
    score: pd.DataFrame,
    *,
    top_n: int,
    bottom_n: int,
    long_share: float,
    short_share: float,
) -> pd.DataFrame:
    """Turn a monthly score panel into monthly target weights."""

    weights = pd.DataFrame(0.0, index=score.index, columns=score.columns)
    for timestamp in score.index:
        valid = score.loc[timestamp].dropna()
        if len(valid) < top_n + bottom_n:
            continue
        if top_n:
            winners = valid.nlargest(top_n).index
            weights.loc[timestamp, winners] = long_share / top_n
        if bottom_n:
            losers = valid.nsmallest(bottom_n).index
            weights.loc[timestamp, losers] = -short_share / bottom_n
    return weights


def residual_momentum_weights(
    close: pd.DataFrame,
    *,
    market_asset: str = "SPY",
    regression_window: int = 36,
    signal_window: int = 11,
    skip_recent: int = 1,
    top_n: int = 3,
    bottom_n: int = 0,
    long_share: float = 1.0,
    short_share: float = 0.0,
) -> pd.DataFrame:
    """Hold winners by *market-residual* momentum, rebalanced monthly.

    For each asset the trailing ``regression_window`` months of returns are
    regressed on the market asset's returns (no intercept, matching the paper's
    exclusion of estimated alpha). The signal is the ``signal_window``-month
    cumulative residual return, skipping the most recent ``skip_recent`` months,
    divided by the standard deviation of the same residual window. Dividing by
    residual volatility is what makes the score comparable across assets: it
    turns momentum into a risk-adjusted residual rather than a raw return.

    The market asset is excluded from selection because its residual is zero by
    construction.
    """

    panel = _validate_panel(close)
    market_asset = market_asset.upper()
    if market_asset not in panel.columns:
        raise ValueError("market_asset must be a column of the price panel")
    if regression_window < 12:
        raise ValueError("regression_window must be at least 12 months")
    if signal_window < 2 or skip_recent < 0 or signal_window + skip_recent > regression_window:
        raise ValueError("signal_window and skip_recent must fit inside regression_window")
    if top_n <= 0 or top_n > len(panel.columns) - 1:
        raise ValueError("top_n must be positive and smaller than the investable universe")
    _validate_shares(long_share, short_share, bottom_n)

    monthly = _month_end_panel(panel)
    monthly_returns = monthly.pct_change()
    market = monthly_returns[market_asset]
    candidates = [column for column in panel.columns if column != market_asset]

    market_variance = market.rolling(regression_window).var(ddof=1)
    scores = pd.DataFrame(index=monthly_returns.index, columns=candidates, dtype=float)
    for asset in candidates:
        covariance = monthly_returns[asset].rolling(regression_window).cov(market)
        beta = covariance / market_variance
        residual = monthly_returns[asset] - beta * market
        window = residual.shift(skip_recent).rolling(signal_window)
        scores[asset] = window.sum() / window.std(ddof=1)

    monthly_weights = _select_extremes(
        scores, top_n=top_n, bottom_n=bottom_n, long_share=long_share, short_share=short_share
    )
    monthly_weights = monthly_weights.reindex(columns=panel.columns, fill_value=0.0)
    return _decide_at_month_start(monthly_weights, panel.index).rename_axis(columns="asset")


def long_term_reversal_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 756,
    skip_recent: int = 21,
    top_n: int = 3,
    bottom_n: int = 0,
    long_share: float = 1.0,
    short_share: float = 0.0,
) -> pd.DataFrame:
    """Buy prior long-horizon losers and optionally short prior winners.

    DeBondt and Thaler form portfolios on three to five years of past returns and
    hold for three years. This implementation keeps the formation rule (negative
    of the trailing multi-year return, skipping the most recent month to avoid
    contaminating it with short-term reversal) but rebalances monthly, which is a
    materially shorter holding period than the paper.
    """

    panel = _validate_panel(close)
    if lookback < 252:
        raise ValueError("lookback must be at least one year (252 trading days)")
    if skip_recent < 0 or skip_recent >= lookback:
        raise ValueError("skip_recent must be non-negative and shorter than lookback")
    if top_n <= 0 or top_n > len(panel.columns):
        raise ValueError("top_n must be positive and no larger than the universe")
    _validate_shares(long_share, short_share, bottom_n)

    monthly = _month_end_panel(panel)
    months = max(3, int(round(lookback / 21)))
    skip_months = int(round(skip_recent / 21))
    formation = monthly.shift(skip_months).pct_change(months)
    score = -formation  # losers score high

    monthly_weights = _select_extremes(
        score, top_n=top_n, bottom_n=bottom_n, long_share=long_share, short_share=short_share
    )
    return _decide_at_month_start(monthly_weights, panel.index).rename_axis(columns="asset")


def quality_composite_returns(
    factors: pd.DataFrame,
    *,
    legs: dict[str, float] | None = None,
    volatility_window: int = 36,
) -> pd.Series:
    """Combine factor legs into an inverse-volatility-weighted composite.

    ``legs`` maps a column of ``factors`` to a signed weight, for example
    ``{"RMW": 1.0, "CMA": -1.0}`` for "profitable and conservatively
    investing". Each leg is divided by its own trailing volatility estimate
    (shifted one period) and the legs are weighted in inverse proportion to
    those volatilities. Standardising matters because the raw legs have very
    different volatilities, so equal capital would let the noisiest leg dominate.

    The result is a monthly return series, not an investable portfolio, so any
    backtest must supply its own turnover and cost assumption.
    """

    if not isinstance(factors, pd.DataFrame) or factors.empty:
        raise ValueError("factors must be a non-empty DataFrame")
    legs = {"RMW": 1.0, "CMA": -1.0} if legs is None else legs
    if not legs:
        raise ValueError("legs cannot be empty")
    missing = [column for column in legs if column not in factors.columns]
    if missing:
        raise ValueError(f"factors is missing required columns: {missing}")
    if volatility_window < 2:
        raise ValueError("volatility_window must exceed 1")
    if not np.isfinite(factors[list(legs)].to_numpy()).all():
        raise ValueError("factor returns must be finite")

    volatility = factors[list(legs)].rolling(volatility_window).std(ddof=1).shift(1)
    inverse = 1.0 / volatility
    total = inverse.sum(axis=1)
    composite = pd.Series(0.0, index=factors.index, dtype=float)
    for column, sign in legs.items():
        composite += sign * factors[column] * (inverse[column] / total)
    composite[total.isna()] = np.nan
    return composite.rename("quality_composite")


def cross_sectional_momentum_score(close: pd.DataFrame, *, lookback: int = 252, skip_recent: int = 21) -> pd.DataFrame:
    """Monthly 12-1 momentum score, provided as the control for the two rules above."""

    panel = _validate_panel(close)
    if lookback <= 0 or skip_recent < 0:
        raise ValueError("lookback must be positive and skip_recent non-negative")
    monthly = _month_end_panel(panel)
    months = max(1, int(round(lookback / 21)))
    skip_months = int(round(skip_recent / 21))
    return monthly.shift(skip_months).pct_change(months)


def cross_sectional_momentum_weights_monthly(
    close: pd.DataFrame,
    *,
    lookback: int = 252,
    skip_recent: int = 21,
    top_n: int = 3,
    bottom_n: int = 0,
    long_share: float = 1.0,
    short_share: float = 0.0,
) -> pd.DataFrame:
    """Monthly 12-1 momentum allocation, so the controls share one calendar."""

    _validate_shares(long_share, short_share, bottom_n)
    score = cross_sectional_momentum_score(close, lookback=lookback, skip_recent=skip_recent)
    monthly_weights = _select_extremes(
        score, top_n=top_n, bottom_n=bottom_n, long_share=long_share, short_share=short_share
    )
    panel = _validate_panel(close)
    monthly_weights = monthly_weights.reindex(columns=panel.columns, fill_value=0.0)
    return _decide_at_month_start(monthly_weights, panel.index).rename_axis(columns="asset")
