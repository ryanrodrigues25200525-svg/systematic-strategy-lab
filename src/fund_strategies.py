"""Transparent proxies for public hedge-fund strategy descriptions.

These functions deliberately implement simple, inspectable approximations of
publicly described ideas. They are not replicas of any fund's proprietary
research, instruments, execution, financing, or risk systems.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .portfolio import _month_start_mask, _rebalance_weights, _validate_panel, time_series_momentum_portfolio_weights


def volatility_scaled_time_series_momentum_weights(
    close: pd.DataFrame,
    *,
    lookback: int = 126,
    volatility_lookback: int = 63,
    target_volatility: float = 0.10,
    max_exposure: float = 1.0,
) -> pd.DataFrame:
    """Build a monthly, long/short trend portfolio with a volatility throttle.

    The sign of each market's trailing return determines long versus short
    exposure. Equal gross weights are scaled down when the realized portfolio
    volatility is above the target. The scaling estimate is shifted so it is
    known before the next holding period.
    """

    panel = _validate_panel(close)
    if lookback <= 0 or volatility_lookback <= 1 or target_volatility <= 0 or max_exposure <= 0:
        raise ValueError("lookback, volatility_lookback, target_volatility, and max_exposure must be positive")

    base = time_series_momentum_portfolio_weights(panel, lookback=lookback)
    returns = panel.pct_change().fillna(0.0)
    base_returns = (base.shift(1).fillna(0.0) * returns).sum(axis=1)
    realized_volatility = base_returns.rolling(volatility_lookback, min_periods=volatility_lookback).std(ddof=1)
    realized_volatility = realized_volatility.shift(1) * np.sqrt(252)

    candidates = pd.DataFrame(0.0, index=panel.index, columns=panel.columns)
    for timestamp in panel.index[_month_start_mask(panel.index).to_numpy()]:
        volatility = realized_volatility.loc[timestamp]
        if pd.notna(volatility) and volatility > 0:
            scale = min(max_exposure, target_volatility / float(volatility))
            candidates.loc[timestamp] = base.loc[timestamp] * scale
    return _rebalance_weights(panel.index, panel.columns, candidates).rename_axis(columns="asset")
