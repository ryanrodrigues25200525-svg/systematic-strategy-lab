# 🧪 Residual momentum stress-test findings

This is a falsification attempt on the one apparently-promising result in the library: the residual momentum rule from [notebook 51](notebooks/51_equity_factor_momentum_reversal_quality.ipynb), which scored a 0.99 test-period Sharpe ratio against 0.61 for plain 12–1 momentum.

**It does not survive.** The specification was frozen before any audit test ran and was not adjusted afterwards.

> Educational research only. Not financial advice. This document exists to record a negative result, not to rank strategies.

## 📉 Result of each test

| Test | Observed | Verdict |
| --- | --- | --- |
| Rolling 3-year Sharpe (756d, 2013-2025) | mean **0.52** vs **0.61** for plain momentum; beats the control in **37.4%** of windows | test slice is the outlier |
| Year-by-year walk-forward, frozen spec | beats plain momentum on return in **7 of 15** years; mean 8.59% vs 9.53% | coin flip, slightly worse |
| Five blocks | 2007-10: 0.00 / 2011-14: 0.95 / 2015-18: **-0.14** / 2019-21: 0.83 / 2022-25: 0.92 | one bad regime, one good one |
| Universe: no non-equity sleeves | 0.75 vs 0.52 | holds |
| Universe: wider, 22 investable | 1.06 vs 0.66 | holds |
| **Universe: drop top-3 winners** (XLK, XLY, XLI) | **0.84 vs 0.86** | edge disappears |
| Alpha / beta (full sample) | alpha **2.58%/yr, t = 1.12**; beta **0.36**; beta-adjusted Sharpe **-0.08** | return is market beta |
| Rank information coefficient | **-0.0159** (t = -0.56), 177 monthly cross-sections | signal does not predict |
| Multiple-testing bootstrap (200 resamples) | best of 12 configs = **1.124**; null 95th percentile **1.606**; **p = 0.249** | indistinguishable from noise |
| Deflated Sharpe ratio | **0.971** at 1 trial, **0.598** at 12 trials | fails its own search |

## 🧠 What this means

1. **The 0.99 was a window, not an edge.** The 2022-2025 test slice is the best of five blocks. Over the full sample the rule's rolling Sharpe averages *below* plain momentum's, and its average annual return is lower (8.59% vs 9.53%).
2. **The return was beta.** Beta 0.36 against 0.56 for plain momentum explains both the lower volatility and most of the return. After hedging market exposure with a prior-only rolling beta, the Sharpe ratio is negative (-0.08). Plain momentum is the same (-0.13). Neither has statistically distinguishable alpha (t = 1.12 and 0.76).
3. **The signal has no predictive power.** Mean monthly rank IC of -0.016 across 177 cross-sections. Whatever produced the portfolio return, it was not the ranking.
4. **Three sectors explain it.** Dropping the sample's three best performers (XLK +1466%, XLY +687%, XLI +527%) removes the entire test-period advantage: 0.84 vs 0.86.
5. **The grid search had no power.** Twelve configurations on a 943-day window; the observed maximum of 1.124 sits below the 95th percentile of the same search on bootstrapped data (1.606). p = 0.25, deflated Sharpe 0.60.

## ✅ What survives

- **The holding-overlap finding.** Residual momentum and plain momentum hold genuinely different books (49% Jaccard overlap) with different market betas. That is a fact about the signals; it is not a claim about returns.
- **The implementation.** The 36-month regression, the skip month, the residual-volatility standardisation, and the one-bar execution delay are implemented as specified and covered by tests. The negative result is about the idea in this universe, not a bug.
- **The tooling.** `src/factor_audit.py` now provides the reusable pieces: stationary block bootstrap, prior-only beta adjustment, OLS alpha/beta with a t-statistic, a bootstrap p-value, and the Bailey–López de Prado deflated Sharpe ratio.

## 🧩 Implementation

New module [`src/factor_audit.py`](src/factor_audit.py):

- `stationary_block_bootstrap(returns, block_length=21, seed=...)` — Politis–Romano resampling that keeps volatility clustering and cross-sectional correlation but destroys time-series momentum. The null model used for the reality check.
- `beta_adjusted_returns(returns, market, lookback=252)` — removes a rolling market beta estimated only from prior data.
- `alpha_beta(returns, market)` — OLS alpha (annualised), beta, alpha t-statistic, residual volatility.
- `bootstrap_pvalue(observed, null_samples)` — one-sided p-value that never returns zero.
- `deflated_sharpe_ratio(sharpe, trials, n_observations, ...)` — annualised Sharpe in, per-observation test internally, probability out. The unit handling is the whole point: mixing annualised Sharpe with a daily sample length makes the deflation look either toothless or brutal.
- `annualized_sharpe(returns)`.

`residual_momentum_score` was extracted from `residual_momentum_weights` so the signal can be tested independently of portfolio construction — the information-coefficient cell needs the score, not the book.

## 📓 Notebook

- [54 — Residual momentum stress test](notebooks/54_residual_momentum_stress_test.ipynb)

## ✅ Validation standards

- 8 new tests in `tests/test_factor_audit.py`. The bootstrap test asserts that every resampled row is an observed row and that ~95% of adjacent rows are contiguous in the source (the stationary-bootstrap property), plus reproducibility and input validation. The beta test asserts that a pure 2x market series produces zero adjusted return. The DSR test checks the closed form against a **simulated** expected maximum of 200 standard normals and asserts the two practical boundaries: a 1.0 Sharpe over 3 years with 200 trials fails; the same Sharpe with 2 trials over 10 years passes.
- 1 new test for `residual_momentum_score`: the held assets must be the score's top two at 80%+ of decision dates.
- The frozen specification is stated in the notebook before any results, and a check cell asserts the grid used by the bootstrap is the reported grid.

## ⚠️ Limitations of the audit

- The bootstrap null destroys time-series momentum, which is the right null for a momentum claim but also removes regime structure a real signal might exploit.
- 200 resamples can place a p-value of 0.25; it cannot resolve 0.04.
- Alpha t-statistics are plain OLS on daily returns, ignoring heteroskedasticity and autocorrelation. A HAC correction would make them smaller, not larger.
- Seventeen ETFs give a wide rank-IC standard error. The result means "no evidence", not "proof of no effect".
- The test period had already been inspected in notebook 51. Nothing in this notebook can undo that, which is why the audit leans on rolling windows, per-year results and asset-dependence rather than on a single corrected statistic.
