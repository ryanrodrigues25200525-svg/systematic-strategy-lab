"""Macro-regime allocation rules built from ETF price signals.

The three rules here are transparent proxies for macro regime ideas that are
usually described with data this project does not carry (credit option-adjusted
spreads, Treasury yield curves, realised inflation). Each rule replaces the
missing macro series with a *relative price* series that is observable every day
and is stated explicitly in the docstring, so the gap between the idea and the
implementation stays visible.

References
----------
- Gilchrist and Zakrajsek (2012), *Credit spreads and business cycle
  fluctuations*: the excess bond premium is a leading indicator of activity and
  a state variable for risk appetite.
- Estrella and Mishkin (1998), *Predicting U.S. recessions: financial variables
  as leading indicators*: term-structure slope predicts recessions.
- AQR Portfolio Solutions Group (2019), *Inversion anxiety*: the slope forecasts
  growth far better than it forecasts equity returns, which is why the notebook
  tests it as a tilt rather than as a market-timing switch.
- Baltussen, Swinkels and van Vliet (2023), *Investing in deflation, inflation
  and stagflation regimes*: asset-class returns differ sharply by inflation
  regime, with real equity and bond returns negative in high inflation.
- Bridgewater's public All Weather material: balance exposure across growth and
  inflation states rather than forecasting them.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from .portfolio import _month_start_mask, _rebalance_weights, _validate_panel


def _month_starts(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    return list(index[_month_start_mask(index).to_numpy()])


def _momentum(panel: pd.DataFrame, lookback: int) -> pd.DataFrame:
    return panel.pct_change(lookback).shift(1)


def _trend(panel: pd.DataFrame, window: int) -> pd.DataFrame:
    """True when the price is above its own trailing moving average."""

    prior = panel.shift(1)
    return prior > prior.rolling(window, min_periods=window).mean()


def _select_by_momentum(
    score: pd.Series,
    eligible: pd.Index,
    *,
    top_n: int,
    total_weight: float,
) -> dict[str, float]:
    """Equal-weight at most ``top_n`` eligible assets with positive momentum."""

    candidates = score.reindex(eligible).dropna()
    candidates = candidates[candidates > 0.0].nlargest(top_n)
    if candidates.empty:
        return {}
    return {asset: total_weight / len(candidates) for asset in candidates.index}


def _allocate(
    close: pd.DataFrame,
    decision: Callable[[pd.Timestamp], dict[str, float]],
) -> pd.DataFrame:
    """Apply a per-decision-date allocator at each month start and hold the result."""

    panel = _validate_panel(close)
    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in _month_starts(panel.index):
        weights = decision(timestamp)
        if not weights:
            continue
        for asset, weight in weights.items():
            candidates.loc[timestamp, asset] = weight
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")


def credit_regime_weights(
    close: pd.DataFrame,
    *,
    credit_asset: str = "HYG",
    safe_asset: str = "IEF",
    risk_assets: tuple[str, ...] = ("SPY", "QQQ", "EFA", "EEM"),
    defensive_assets: tuple[str, ...] = ("TLT", "IEF"),
    trend_window: int = 200,
    momentum_lookback: int = 126,
    top_n: int = 2,
) -> pd.DataFrame:
    """Switch between risk assets and defensive assets on credit leadership.

    The regime variable is the ``credit_asset / safe_asset`` price ratio — a
    high-yield ETF against an intermediate Treasury ETF. When the ratio is above
    its own ``trend_window`` moving average, credit is leading and the rule holds
    the ``top_n`` risk assets with positive ``momentum_lookback`` momentum.
    Otherwise it holds the defensive assets equally.

    This is a **price-ratio proxy** for a credit spread, not a spread. A widening
    spread and a falling Treasury yield both move the ratio, and ETF construction
    adds duration, accrued-coupon and fund-flow effects that a spread series would
    not have.
    """

    panel = _validate_panel(close)
    credit_asset, safe_asset = credit_asset.upper(), safe_asset.upper()
    missing = [asset for asset in (credit_asset, safe_asset) if asset not in panel.columns]
    if missing:
        raise ValueError(f"credit_asset and safe_asset must be columns of the panel: {missing}")
    risk = [asset for asset in risk_assets if asset in panel.columns]
    defensive = [asset for asset in defensive_assets if asset in panel.columns]
    if not risk or not defensive:
        raise ValueError("risk_assets and defensive_assets must overlap the price panel")
    if trend_window <= 1 or momentum_lookback <= 0 or top_n <= 0:
        raise ValueError("trend_window must exceed 1 and momentum_lookback/top_n must be positive")

    ratio = panel[credit_asset] / panel[safe_asset]
    prior_ratio = ratio.shift(1)
    risk_on = prior_ratio > prior_ratio.rolling(trend_window, min_periods=trend_window).mean()
    score = _momentum(panel, momentum_lookback)

    def decision(timestamp: pd.Timestamp) -> dict[str, float]:
        if bool(risk_on.loc[timestamp]):
            weights = _select_by_momentum(score.loc[timestamp], pd.Index(risk), top_n=top_n, total_weight=1.0)
            if weights:
                return weights
        return {asset: 1.0 / len(defensive) for asset in defensive}

    return _allocate(close, decision)


def inflation_rotation_weights(
    close: pd.DataFrame,
    *,
    inflation_assets: tuple[str, ...] = ("TIP", "GLD", "DBC"),
    deflation_assets: tuple[str, ...] = ("TLT",),
    trend_window: int = 200,
    momentum_lookback: int = 126,
    top_n: int = 2,
) -> pd.DataFrame:
    """Hold whatever protects against inflation, or duration when nothing does.

    Assets whose price is above their own ``trend_window`` moving average are
    eligible; the rule holds the ``top_n`` eligible assets with the strongest
    ``momentum_lookback`` return. When nothing qualifies it holds the
    ``deflation_assets`` equally.

    The motivating claim is that inflation and deflation regimes reward different
    assets, so a rule that *responds* to which regime is in force should be more
    robust than a fixed allocation. The claim being tested is response, not
    prediction: this rule never forecasts inflation, it only follows prices.
    """

    panel = _validate_panel(close)
    inflation = [asset for asset in inflation_assets if asset in panel.columns]
    deflation = [asset for asset in deflation_assets if asset in panel.columns]
    if not inflation or not deflation:
        raise ValueError("inflation_assets and deflation_assets must overlap the price panel")
    if trend_window <= 1 or momentum_lookback <= 0 or top_n <= 0:
        raise ValueError("trend_window must exceed 1 and momentum_lookback/top_n must be positive")

    trend = _trend(panel[inflation], trend_window)
    score = _momentum(panel, momentum_lookback)

    def decision(timestamp: pd.Timestamp) -> dict[str, float]:
        eligible = trend.loc[timestamp][trend.loc[timestamp]].index
        weights = _select_by_momentum(score.loc[timestamp], eligible, top_n=top_n, total_weight=1.0)
        if weights:
            return weights
        return {asset: 1.0 / len(deflation) for asset in deflation}

    return _allocate(close, decision)


def term_structure_tilt_weights(
    close: pd.DataFrame,
    *,
    short_asset: str = "SHY",
    long_asset: str = "TLT",
    duration_assets: tuple[str, ...] = ("TLT", "IEF"),
    procyclical_assets: tuple[str, ...] = ("SPY", "XLF"),
    lookback: int = 126,
    trend_window: int = 200,
    top_n: int = 2,
) -> pd.DataFrame:
    """Tilt with the duration trend, interpreted as a curve-slope proxy.

    The proxy is the ``long_asset / short_asset`` price ratio. When it is rising
    and above its ``trend_window`` average, long-duration bonds are outperforming
    cash-like paper: the curve is flattening and the rule holds
    ``duration_assets``. When it is falling, duration is losing and the rule
    holds the ``procyclical_assets`` with positive ``lookback`` momentum.

    The AQR evidence is that the slope predicts growth far more reliably than it
    predicts equity returns, so the honest prior here is that this rule captures
    a duration trend and very little macro information. The notebook reports the
    result as found.
    """

    panel = _validate_panel(close)
    short_asset, long_asset = short_asset.upper(), long_asset.upper()
    missing = [asset for asset in (short_asset, long_asset) if asset not in panel.columns]
    if missing:
        raise ValueError(f"short_asset and long_asset must be columns of the panel: {missing}")
    duration = [asset for asset in duration_assets if asset in panel.columns]
    procyclical = [asset for asset in procyclical_assets if asset in panel.columns]
    if not duration or not procyclical:
        raise ValueError("duration_assets and procyclical_assets must overlap the price panel")
    if lookback <= 1 or trend_window <= 1 or top_n <= 0:
        raise ValueError("lookback and trend_window must exceed 1 and top_n must be positive")

    ratio = panel[long_asset] / panel[short_asset]
    prior_ratio = ratio.shift(1)
    average = prior_ratio.rolling(trend_window, min_periods=trend_window).mean()
    slope = prior_ratio.pct_change(lookback)
    flattening = (prior_ratio > average) & (slope > 0.0)
    score = _momentum(panel, lookback)

    def decision(timestamp: pd.Timestamp) -> dict[str, float]:
        if bool(flattening.loc[timestamp]):
            return {asset: 1.0 / len(duration) for asset in duration}
        weights = _select_by_momentum(score.loc[timestamp], pd.Index(procyclical), top_n=top_n, total_weight=1.0)
        if weights:
            return weights
        return {asset: 1.0 / len(duration) for asset in duration}

    return _allocate(close, decision)
