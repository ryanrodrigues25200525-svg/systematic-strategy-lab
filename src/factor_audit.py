"""Research-integrity tools: bootstrap inference, beta decomposition, deflation.

These helpers exist so a promising in-sample result can be attacked rather than
celebrated. They are deliberately small and dependency-free.

References
----------
- Politis and Romano (1994), *The stationary bootstrap*: resample blocks of
  geometrically distributed length so a time series keeps its local dependence
  but loses its global structure.
- White (2000), *A reality check for data snooping*: the relevant null for a
  parameter search is the distribution of the **best** statistic across the
  search, not the distribution of a single one.
- Bailey and Lopez de Prado (2014), *The deflated Sharpe ratio*: corrects an
  observed Sharpe ratio for the number of independent trials, the sample length,
  and the skewness and kurtosis of the return distribution.
"""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd

EULER_MASCHERONI = 0.5772156649015329


def _validate_returns(returns: pd.DataFrame) -> pd.DataFrame:
    frame = returns.astype(float)
    if frame.empty or frame.columns.has_duplicates:
        raise ValueError("Returns must be a non-empty frame with unique columns")
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError("Returns index must be unique and increasing")
    if not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Returns must be finite")
    return frame


def stationary_block_bootstrap(
    returns: pd.DataFrame,
    *,
    block_length: int = 21,
    seed: int = 0,
) -> pd.DataFrame:
    """Resample a return panel with a stationary bootstrap.

    Consecutive rows are copied from the original panel in runs whose length is
    geometric with mean ``block_length``, so volatility clustering and
    cross-sectional correlation survive while any long-horizon pattern — momentum,
    reversal, regime structure — is destroyed. The output keeps the original index
    so downstream code does not need a special calendar.

    This is the null model used by the audit notebook: if a momentum rule makes
    money on resampled data, the rule is not a momentum rule.
    """

    frame = _validate_returns(returns)
    if block_length < 1:
        raise ValueError("block_length must be at least 1")
    if len(frame) < 2 * block_length:
        raise ValueError("Need at least two blocks of observations to resample")

    rng = np.random.default_rng(seed)
    observations = len(frame)
    values = frame.to_numpy()
    restart_probability = 1.0 / block_length

    positions = np.empty(observations, dtype=int)
    positions[0] = rng.integers(observations)
    for step in range(1, observations):
        if rng.random() < restart_probability:
            positions[step] = rng.integers(observations)
        else:
            positions[step] = (positions[step - 1] + 1) % observations

    return pd.DataFrame(values[positions], index=frame.index, columns=frame.columns)


def bootstrap_pvalue(observed: float, null_samples: np.ndarray) -> float:
    """One-sided bootstrap p-value that includes the observed value in the tail.

    ``(1 + #{null >= observed}) / (1 + n)`` never returns zero, which matters when
    a result looks impressive against a finite number of resamples.
    """

    samples = np.asarray(null_samples, dtype=float)
    if samples.size == 0:
        raise ValueError("null_samples cannot be empty")
    if not np.isfinite(observed):
        raise ValueError("observed must be finite")
    exceedances = int(np.sum(samples >= observed))
    return float((1 + exceedances) / (1 + samples.size))


def beta_adjusted_returns(
    returns: pd.Series,
    market: pd.Series,
    *,
    lookback: int = 252,
) -> pd.Series:
    """Remove a time-varying market beta estimated only from prior data.

    Beta is a rolling covariance over ``lookback`` observations divided by the
    market variance, shifted one bar so the hedge uses information available
    before the return it is applied to. The result answers "what is left after
    paying for the market exposure", which is the only honest way to compare a
    long book against a long/short one.
    """

    strategy = pd.Series(returns, dtype=float)
    benchmark = pd.Series(market, dtype=float).reindex(strategy.index)
    if lookback < 2:
        raise ValueError("lookback must exceed 1")
    if strategy.empty or benchmark.isna().any():
        raise ValueError("returns and market must be non-empty and share an index")

    variance = benchmark.rolling(lookback).var(ddof=1)
    covariance = strategy.rolling(lookback).cov(benchmark)
    beta = (covariance / variance).shift(1)
    adjusted = strategy - beta * benchmark
    return adjusted.rename("beta_adjusted_returns")


def alpha_beta(
    returns: pd.Series,
    market: pd.Series,
    *,
    annualization: int = 252,
) -> dict[str, float]:
    """Ordinary-least-squares alpha and beta with a t-statistic for alpha.

    The t-statistic is the plain OLS one, so it assumes homoskedastic,
    uncorrelated residuals. Treat it as a screening number, not inference: daily
    strategy returns are usually heteroskedastic.
    """

    strategy = pd.Series(returns, dtype=float)
    benchmark = pd.Series(market, dtype=float).reindex(strategy.index)
    aligned = pd.concat([strategy.rename("strategy"), benchmark.rename("market")], axis=1).dropna()
    if len(aligned) < 30:
        raise ValueError("Need at least 30 aligned observations for an alpha/beta estimate")

    y = aligned["strategy"].to_numpy()
    x = aligned["market"].to_numpy()
    design = np.column_stack([np.ones_like(x), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    residuals = y - design @ coefficients
    degrees_of_freedom = len(y) - 2
    residual_variance = float(residuals @ residuals / degrees_of_freedom)
    covariance = residual_variance * np.linalg.inv(design.T @ design)
    alpha_daily, beta = float(coefficients[0]), float(coefficients[1])
    alpha_standard_error = float(np.sqrt(covariance[0, 0]))
    return {
        "alpha": alpha_daily * annualization,
        "beta": beta,
        "alpha_t_stat": alpha_daily / alpha_standard_error if alpha_standard_error > 0 else 0.0,
        "residual_volatility": float(np.sqrt(residual_variance) * np.sqrt(annualization)),
        "observations": float(len(y)),
    }


def deflated_sharpe_ratio(
    sharpe_ratio: float,
    *,
    trials: int,
    n_observations: int,
    annualization: int = 252,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
    sharpe_variance: float | None = None,
) -> float:
    """Bailey–Lopez de Prado deflated Sharpe ratio, as a probability.

    ``sharpe_ratio`` is **annualised**; the test is computed in per-observation
    units, because the sampling theory applies to the non-annualised statistic.
    Mixing the two units makes the deflation look either toothless or brutal, so
    the conversion happens here rather than at the call site.

    The observed Sharpe ratio is compared against the Sharpe ratio you would
    *expect* the best of ``trials`` independent strategies to achieve by chance.
    ``sharpe_variance`` (annualised variance of the trial Sharpe ratios) defaults
    to the iid value implied by the sample length.

    Returns the probability that the true Sharpe ratio exceeds that benchmark. A
    value below roughly 0.95 means the result does not survive its own search.
    """

    if trials < 1:
        raise ValueError("trials must be at least 1")
    if n_observations < 3:
        raise ValueError("n_observations must be at least 3")
    if kurtosis < 1.0:
        raise ValueError("kurtosis must be at least 1")
    if annualization < 1:
        raise ValueError("annualization must be positive")

    # Work in per-observation units throughout.
    per_observation = sharpe_ratio / np.sqrt(annualization)
    variance = 1.0 / n_observations if sharpe_variance is None else float(sharpe_variance) / annualization
    if variance <= 0.0:
        raise ValueError("sharpe_variance must be positive")

    normal = NormalDist()
    if trials == 1:
        benchmark = 0.0
    else:
        # Expected maximum of `trials` standard normals (Bailey-Lopez de Prado 2014).
        upper = normal.inv_cdf(1.0 - 1.0 / trials)
        lower = normal.inv_cdf(1.0 - 1.0 / (trials * np.e))
        benchmark = np.sqrt(variance) * ((1.0 - EULER_MASCHERONI) * upper + EULER_MASCHERONI * lower)

    denominator = np.sqrt(1.0 - skewness * per_observation + (kurtosis - 1.0) / 4.0 * per_observation**2)
    if not np.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("Return distribution makes the deflation undefined")
    statistic = (per_observation - benchmark) * np.sqrt(n_observations - 1) / denominator
    return float(normal.cdf(statistic))


def annualized_sharpe(returns: pd.Series, *, annualization: int = 252) -> float:
    """Annualised Sharpe ratio with a zero risk-free rate."""

    clean = pd.Series(returns, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) < 2:
        raise ValueError("Need at least two observations")
    deviation = float(clean.std(ddof=1))
    return 0.0 if deviation == 0.0 else float(clean.mean() / deviation * np.sqrt(annualization))
