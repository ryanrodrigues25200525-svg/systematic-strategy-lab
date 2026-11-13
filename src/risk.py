"""Covariance shrinkage and risk-based portfolio construction primitives.

Every method here is deliberately dependency-light: shrinkage, the equal-risk
contribution solver, and hierarchical clustering are implemented with NumPy and
pandas only, so the notebook results can be audited line by line.

References
----------
- Ledoit and Wolf (2004), *A well-conditioned estimator for large-dimensional
  covariance matrices*: linear shrinkage toward a scaled identity.
- Chen, Wiesel, Eldar and Hero (2010), *Shrinkage algorithms for MMSE
  covariance estimation*: the Oracle Approximating Shrinkage (OAS) intensity.
- Maillard, Roncalli and Teiletche (2010), *On the properties of equally
  weighted risk contributions*: the ERC portfolio.
- Griveau-Billion, Richard and Roncalli (2013): the convex-programming
  reformulation used by ``erc_weights``.
- Lopez de Prado (2016), *Building diversified portfolios that outperform
  out-of-sample*: Hierarchical Risk Parity.
- Choueifaty and Coignard (2008): the maximum-diversification ratio.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VALID_SHRINKAGE_METHODS = ("oas", "ledoit-wolf", "none")


def _validate_returns(returns: pd.DataFrame) -> pd.DataFrame:
    frame = returns.astype(float)
    if frame.empty or frame.columns.has_duplicates:
        raise ValueError("Returns frame must be non-empty with unique assets")
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError("Returns index must be unique and increasing")
    if not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Returns frame must contain finite values")
    if len(frame) < 2:
        raise ValueError("Need at least two observations to estimate a covariance matrix")
    return frame


def _validate_covariance(covariance: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(covariance, pd.DataFrame):
        covariance = pd.DataFrame(covariance)
    matrix = covariance.astype(float)
    if matrix.empty or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Covariance must be a non-empty square matrix")
    if not matrix.index.equals(matrix.columns):
        raise ValueError("Covariance index and columns must match")
    if not np.isfinite(matrix.to_numpy()).all():
        raise ValueError("Covariance must contain finite values")
    if (np.diag(matrix.to_numpy()) <= 0.0).any():
        raise ValueError("Covariance diagonal must be strictly positive")
    if not np.allclose(matrix.to_numpy(), matrix.to_numpy().T, atol=1e-12):
        raise ValueError("Covariance must be symmetric")
    return matrix


def _oas_intensity(sample: np.ndarray, observations: int) -> float:
    """Chen et al. (2010) closed-form shrinkage intensity toward ``mu * I``."""

    assets = sample.shape[0]
    if assets == 1:
        return 0.0
    trace = float(np.trace(sample))
    trace_squared = float(np.sum(sample**2))
    numerator = (1.0 - 2.0 / assets) * trace_squared + trace**2
    denominator = (observations + 1.0 - 2.0 / assets) * (trace_squared - trace**2 / assets)
    if denominator <= 0.0:
        return 1.0
    return float(np.clip(numerator / denominator, 0.0, 1.0))


def _ledoit_wolf_intensity(sample: np.ndarray, centered: np.ndarray, observations: int, target: np.ndarray) -> float:
    """Ledoit and Wolf (2004) intensity for the scaled-identity target."""

    if sample.shape[0] == 1:
        return 0.0
    squared = centered**2
    beta_squared = (np.sum(squared.T @ squared) - observations * np.sum(sample**2)) / (observations**2)
    delta_squared = np.sum((sample - target) ** 2)
    if delta_squared <= 0.0:
        return 1.0
    return float(np.clip(beta_squared / delta_squared, 0.0, 1.0))


def shrink_covariance(
    returns: pd.DataFrame,
    *,
    method: str = "oas",
    return_intensity: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, float]:
    """Estimate a covariance matrix with linear shrinkage toward a scaled identity.

    ``method="oas"`` uses the closed-form Oracle Approximating Shrinkage
    intensity, ``method="ledoit-wolf"`` uses the Ledoit-Wolf intensity for the
    same target, and ``method="none"`` returns the raw sample covariance. The
    target is ``mu * I`` with ``mu`` equal to the average sample variance, so
    total variance is preserved by construction.

    Shrinkage matters here because several allocation methods below invert or
    cluster the covariance matrix. A sample covariance built from fewer
    observations than assets is singular, and even a well-scaled sample matrix
    is badly conditioned when assets are highly correlated.

    Set ``return_intensity=True`` to receive ``(covariance, intensity)``; the
    intensity is the weight placed on the scaled-identity target and is useful
    as a diagnostic for how little information the sample matrix contains.
    """

    frame = _validate_returns(returns)
    if method not in VALID_SHRINKAGE_METHODS:
        raise ValueError(f"Unknown shrinkage method {method!r}; expected one of {VALID_SHRINKAGE_METHODS}")

    values = frame.to_numpy(dtype=float)
    observations, assets = values.shape
    centered = values - values.mean(axis=0)
    sample = centered.T @ centered / observations
    if method == "none":
        result = pd.DataFrame(sample, index=frame.columns, columns=frame.columns)
        return (result, 0.0) if return_intensity else result

    mu = float(np.trace(sample) / assets)
    target = np.eye(assets) * mu
    if assets == 1:
        result = pd.DataFrame(sample, index=frame.columns, columns=frame.columns)
        return (result, 0.0) if return_intensity else result

    if method == "ledoit-wolf":
        intensity = _ledoit_wolf_intensity(sample, centered, observations, target)
    else:
        intensity = _oas_intensity(sample, observations)

    shrunk = intensity * target + (1.0 - intensity) * sample
    # Remove the residual asymmetry introduced by floating-point accumulation.
    shrunk = (shrunk + shrunk.T) / 2.0
    result = pd.DataFrame(shrunk, index=frame.columns, columns=frame.columns)
    return (result, intensity) if return_intensity else result


def risk_contributions(weights: pd.Series, covariance: pd.DataFrame) -> pd.Series:
    """Return each asset's share of total portfolio variance.

    The contribution of asset ``i`` is ``w_i * (Sigma w)_i / (w' Sigma w)``, so
    the shares sum to one for any fully invested portfolio.
    """

    covariance = _validate_covariance(covariance)
    weight = pd.Series(weights, dtype=float).reindex(covariance.index)
    if weight.isna().any():
        raise ValueError("Weights must cover every asset in the covariance matrix")
    variance = float(weight.to_numpy() @ covariance.to_numpy() @ weight.to_numpy())
    if variance <= 0.0:
        raise ValueError("Portfolio variance must be positive")
    marginal = covariance.to_numpy() @ weight.to_numpy()
    return pd.Series(weight.to_numpy() * marginal / variance, index=covariance.index, name="risk_contribution")


def _convex_erc(covariance: np.ndarray, budget: np.ndarray, iterations: int = 400) -> np.ndarray:
    """Solve ERC through Spinu's convex program: min_y y'Cy - sum b_i log(y_i).

    The first-order condition is ``2 (Cy)_i = b_i / y_i``, which is exactly the
    equal-risk-contribution condition after normalising ``y``. A damped Newton
    iteration keeps every ``y_i`` strictly positive, so the solver handles
    singular and near-singular covariance matrices where a quadratic optimiser
    would fail.
    """

    assets = covariance.shape[0]
    diagonal = np.clip(np.diag(covariance), 1e-18, None)
    y = 1.0 / np.sqrt(diagonal)
    y = y / np.sqrt(y @ covariance @ y) * np.sqrt(np.sum(budget))

    for _ in range(iterations):
        gradient = 2.0 * covariance @ y - budget / y
        if np.max(np.abs(gradient)) < 1e-15:
            break
        hessian = 2.0 * covariance + np.diag(budget / y**2)
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:  # pragma: no cover - defensive
            step = np.linalg.pinv(hessian) @ gradient
        scale = 1.0
        while np.any(y - scale * step <= 0.0) and scale > 1e-12:
            scale *= 0.5
        candidate = y - scale * step
        if np.any(candidate <= 0.0):  # pragma: no cover - defensive
            break
        y = candidate
    return y / y.sum()


def erc_weights(covariance: pd.DataFrame, *, budget: pd.Series | None = None) -> pd.Series:
    """Compute equal (or budgeted) risk contribution weights.

    With ``budget=None`` every asset contributes the same share of portfolio
    variance. Passing a budget solves the general risk-budgeting problem. When
    the covariance matrix is diagonal the answer collapses to inverse
    volatility, which is why naive risk parity is a special case rather than a
    different idea.
    """

    covariance = _validate_covariance(covariance)
    assets = len(covariance.index)
    if budget is None:
        target = np.full(assets, 1.0 / assets)
    else:
        target = pd.Series(budget, dtype=float).reindex(covariance.index)
        if target.isna().any() or (target <= 0.0).any():
            raise ValueError("Risk budget must cover every asset with positive values")
        target = target.to_numpy() / target.sum()

    weights = _convex_erc(covariance.to_numpy(), target)
    return pd.Series(weights, index=covariance.index, name="weight")


def _cluster_variance(covariance: np.ndarray, indices: np.ndarray) -> float:
    cluster = covariance[np.ix_(indices, indices)]
    diagonal = np.clip(np.diag(cluster), 1e-18, None)
    inverse_variance = 1.0 / diagonal
    weight = inverse_variance / inverse_variance.sum()
    return float(weight @ cluster @ weight)


def _quasi_diagonal_order(linkage: np.ndarray) -> list[int]:
    """Unwind a scipy-style single-linkage matrix into a leaf order."""

    items = [int(node) for node in linkage[-1, :2]]
    while max(items) >= len(linkage) + 1:
        expanded: list[int] = []
        for item in items:
            if item < len(linkage) + 1:
                expanded.append(item)
            else:
                row = linkage[item - (len(linkage) + 1)]
                expanded.extend([int(row[0]), int(row[1])])
        items = expanded
    return items


def _single_linkage(distance: np.ndarray) -> np.ndarray:
    """Build a single-linkage dendrogram without SciPy.

    Returns a SciPy-compatible ``(n - 1) x 4`` matrix where the first two
    columns are cluster ids, the third is the merge distance, and the fourth is
    the number of original observations in the new cluster. Cluster ids ``0`` to
    ``n - 1`` are leaves and ``n + i`` identifies the ``i``-th merge.
    """

    observations = distance.shape[0]
    active = {index: [index] for index in range(observations)}
    cluster_distance = {
        (min(i, j), max(i, j)): float(distance[i, j])
        for i in range(observations)
        for j in range(i + 1, observations)
    }
    rows = []
    next_id = observations
    while len(active) > 1:
        pairs = [
            (value, first, second)
            for (first, second), value in cluster_distance.items()
            if first in active and second in active
        ]
        value, first, second = min(pairs)
        rows.append([first, second, value, len(active[first]) + len(active[second])])
        merged = active.pop(first) + active.pop(second)
        active[next_id] = merged
        for other in list(active):
            if other == next_id:
                continue
            key = (min(other, next_id), max(other, next_id))
            cluster_distance[key] = min(
                cluster_distance.get((min(other, first), max(other, first)), np.inf),
                cluster_distance.get((min(other, second), max(other, second)), np.inf),
            )
        next_id += 1
    return np.asarray(rows, dtype=float)


def hierarchical_risk_parity_weights_from_cov(covariance: pd.DataFrame) -> pd.Series:
    """Run the three HRP stages on a covariance matrix.

    1. Turn correlations into distances ``d_ij = sqrt(0.5 * (1 - rho_ij))``.
    2. Cluster the distance matrix with single linkage and order the assets so
       similar assets sit next to each other (quasi-diagonalisation).
    3. Recursively bisect the ordered list, splitting each cluster's budget in
       inverse proportion to the two halves' inverse-variance variances.

    HRP never inverts the covariance matrix, so it stays usable when the matrix
    is singular and it does not concentrate in a handful of correlated assets
    the way an unconstrained minimum-variance optimiser can.
    """

    covariance = _validate_covariance(covariance)
    values = covariance.to_numpy(dtype=float)
    volatility = np.sqrt(np.diag(values))
    correlation = values / np.outer(volatility, volatility)
    correlation = np.clip(correlation, -1.0, 1.0)
    np.fill_diagonal(correlation, 1.0)

    distance = np.sqrt(np.clip(0.5 * (1.0 - correlation), 0.0, None))
    order = _quasi_diagonal_order(_single_linkage(distance))

    weights = pd.Series(1.0, index=order, dtype=float)
    clusters = [np.array(order, dtype=int)]
    while clusters:
        current = clusters.pop()
        if len(current) <= 1:
            continue
        split = len(current) // 2
        left, right = current[:split], current[split:]
        left_variance = _cluster_variance(values, left)
        right_variance = _cluster_variance(values, right)
        total = left_variance + right_variance
        # Allocate the smaller-variance half more capital, capped so a degenerate
        # split cannot hand the entire cluster to one side.
        left_share = 1.0 - left_variance / total if total > 0.0 else 0.5
        left_share = float(np.clip(left_share, 0.0, 1.0))
        weights.loc[left] *= left_share
        weights.loc[right] *= 1.0 - left_share
        clusters.extend([left, right])

    result = weights.reindex(range(len(covariance.index))).fillna(0.0)
    result.index = covariance.index
    result = result / result.sum()
    return result.rename("weight")


def max_diversification_weights_from_cov(covariance: pd.DataFrame) -> pd.Series:
    """Solve the long-only maximum-diversification portfolio.

    The diversification ratio is ``(w'sigma) / sqrt(w' Sigma w)``. Its
    unconstrained solution is proportional to ``Sigma^-1 sigma``, so the
    long-only version clips the negative entries and renormalises. Clipping is a
    heuristic rather than an exact quadratic program, but it preserves the
    economic content: assets that add correlation without adding return-per-unit
    of risk receive less capital than they would under minimum variance.
    """

    covariance = _validate_covariance(covariance)
    values = covariance.to_numpy(dtype=float)
    volatility = np.sqrt(np.diag(values))
    try:
        raw = np.linalg.solve(values, volatility)
    except np.linalg.LinAlgError:  # pragma: no cover - defensive
        raw = np.linalg.pinv(values) @ volatility
    positive = np.clip(raw, 0.0, None)
    if positive.sum() <= 0.0:  # pragma: no cover - defensive
        positive = np.ones_like(raw)
    return pd.Series(positive / positive.sum(), index=covariance.index, name="weight")


def diversification_ratio(weights: pd.Series, covariance: pd.DataFrame) -> float:
    """Return ``(w'sigma) / sqrt(w' Sigma w)`` for an allocation."""

    covariance = _validate_covariance(covariance)
    weight = pd.Series(weights, dtype=float).reindex(covariance.index).to_numpy()
    volatility = np.sqrt(np.diag(covariance.to_numpy()))
    denominator = np.sqrt(weight @ covariance.to_numpy() @ weight)
    if denominator <= 0.0:
        raise ValueError("Portfolio variance must be positive")
    return float(weight @ volatility / denominator)
