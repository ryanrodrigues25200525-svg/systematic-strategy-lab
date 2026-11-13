# 🕵️ Surviving claims audit

Notebook 54 falsified the library's most promising result. This round audits the four claims that survived it, and answers the question a reader should ask: **is anything here true?**

> Educational research only. Not financial advice.

> ## 🧭 Superseded in part
>
> Notebooks 56 and 57 re-tested these mechanisms on a century of the original stock-level portfolios and changed the conclusion from "everything is beta" to **"the anomalies are real, the observation window is the problem"**. Read [FACTOR_REPLICATION_FINDINGS.md](FACTOR_REPLICATION_FINDINGS.md) after this document: the attribution findings here stand, but they are not the whole story.

## 📊 The four claims

| Claim | Source | Verdict |
| --- | --- | --- |
| SPY 200-day trend gate beats buy-and-hold on risk-adjusted return | notebook 52 | **Partly** — real risk reduction, alpha t = 2.13, but grid p = 0.12 and only 3 of 7 assets improve on Sharpe |
| ERC has alpha against the equity market | notebook 50 | **No** — 3.73%/yr (t = 2.88) collapses to 1.83% (t = 1.93) with duration as a second factor |
| Equal weight has alpha | notebook 50 | **No** — 1.72% (t = 1.38) becomes 0.32% (t = 0.30) |
| "Deflated Sharpe > 0.95" means a result survives | notebook 54's method | **No** — on total returns every long-only sleeve passes; the test only bites on beta-adjusted returns |

## 📈 The trend gate over 33 years (SPY, 1993-2025, cash defence, 10 bps)

| | Trend gate | SPY buy & hold |
| --- | ---: | ---: |
| Annualised return | 7.91% | **10.68%** |
| Annualised volatility | **11.99%** | 18.63% |
| Sharpe ratio | **0.70** | 0.64 |
| Sortino ratio | **0.97** | 0.91 |
| Max drawdown | **-24.99%** | -55.19% |
| Calmar ratio | **0.32** | 0.19 |
| Turnover | 6.5 | 0.0 |
| Alpha vs SPY | 3.40%/yr, **t = 2.13** | — |
| Beta | 0.41 | 1.00 |
| Beta-adjusted Sharpe | 0.12 | — |

Per decade (Sharpe, gate vs buy & hold): 1993-99 **1.07 / 1.33**; 2000-09 **0.32 / 0.07**; 2010-19 **0.63 / 0.93**; 2020-25 **0.88 / 0.78**. The gate wins 2 of 4 decades.

## 🔍 What each test found

**1. The Sharpe edge is a crash artefact.** On rolling three-year windows the gate beats buy-and-hold only **32.2%** of the time; median rolling Sharpe 0.67 against **0.82**. It beats buy-and-hold on return in **3 of 32 years**. It wins the full-sample comparison by sitting out 2001 and 2008, not by being better in an ordinary three-year stretch.

**2. The grid is not significant.** Full-sample Sharpe by window: 50d 0.339, 100d 0.505, 150d 0.649, **200d 0.695**, 250d 0.636, 300d 0.748. Best of six = 0.748 against a bootstrap null 95th percentile of 0.823 → **p = 0.124**.

**3. Generality is mixed.** The gate improves Sharpe on 3 of 7 assets (QQQ 0.76 vs 0.75, XLK 0.73 vs 0.72, EFA 0.48 vs 0.39) and loses on IWM (0.25 vs 0.45), EEM (0.29 vs 0.37), GLD (0.56 vs 0.68) and TLT (0.11 vs 0.29). It improves the drawdown on **6 of 7** (TLT unchanged at -48.5%).

**4. Attribution kills the allocation family.** Adding TLT as a second regressor:

| Allocation | Alpha vs SPY | t | Alpha vs SPY+TLT | t | Beta TLT |
| --- | ---: | ---: | ---: | ---: | ---: |
| Equal weight | 1.72% | +1.38 | **0.32%** | **+0.30** | +0.19 |
| ERC (252d) | 2.27% | +1.75 | **0.23%** | **+0.26** | +0.28 |
| ERC (504d) | 3.73% | +2.88 | **1.83%** | **+1.93** | +0.26 |

Their single-factor "alpha" was the term premium. A bond-heavy portfolio looks skilful against SPY and ordinary against SPY plus duration.

**5. The deflated Sharpe is easy to pass for the wrong reason.** On total returns: gate 1.000, equal weight 0.999, ERC 504 1.000 — all "significant", all because the equity premium is real. On beta-adjusted returns: gate **0.744**, equal weight **0.774**, ERC 504 **0.984** (and that last one hedges SPY only, leaving a +0.26 duration beta behind).

**6. The covariance-estimator debate was a distraction.** ERC Sharpe across eight lookback/estimator combinations ranges 0.70-0.88; sample and OAS covariances give identical results to two decimals. Lookback matters, shrinkage does not — exactly what notebook 50 found and this re-tests.

## 🧠 The verdict

Across 54 notebooks, four strategy families, nineteen new rules and two falsification rounds:

> **The library contains one durable effect: equity and duration beta are real, and de-risking on trend reduces drawdowns at a fair price. Everything that looked like alpha was a beta in disguise, a window, or a grid search — usually all three.**

Concretely:

- **Beta is real**: equities earn a premium, duration earns a premium, and a 60/40-style mix captures both. That is why equal weight and ERC look good and why their "alpha" vanishes on attribution.
- **The trend gate is the only timing rule with a defensible positive alpha** (t = 2.13 over 33 years, unchanged by duration controls because it holds cash). Its honest description is *drawdown insurance at the cost of 2.8 percentage points of annual return*, not a return engine.
- **No rule in this library clears a serious multiple-testing bar.** Harvey, Liu and Zhu's suggestion of t ≈ 3 has not been met by anything here.

## 🧩 Implementation

- `src/macro_regimes.py`: added `trend_gate_weights` (the rule under test, with a 20-day minimum window) — previously it lived inline in notebook 52.
- `src/factor_audit.py`: `alpha_beta` now accepts `extra_factors`, so attribution can add duration, size, credit or anything else. This one change is what turned "ERC has alpha" into "ERC has duration".

## 📓 Notebook

- [55 — Falsification round 2: surviving claims](notebooks/55_surviving_claims_audit.ipynb)

## ✅ Validation standards

- 2 new tests: `trend_gate_weights` (holds the asset above its average, defence below, nothing during warm-up, truncation-invariant, rejects a two-day "trend" window) and multi-factor `alpha_beta` (recovers both betas and shrinks a polluted single-factor alpha).
- The gate book is checked to be long-only, never above 100% gross, and empty before its average exists.
- Every claim is tested on the longest sample available to it: 33 years for SPY alone, 19 years for the ten-ETF panel.
- The bootstrap null uses the same six-window grid that produced the observed maximum.
- Negative findings are stated in the tl;dr, not buried.

## ⚠️ Limitations

- Single-market and two-factor attributions only: no size, value, credit or commodity factors. A richer model would explain more of the residual, not less.
- The trend gate is tested as a single-asset overlay with cash and bond defences, not levered and not as one sleeve of several gates.
- The block bootstrap destroys volatility regimes as well as trend structure, which biases it *against* a rule whose purpose is to respond to regimes. That is the price of a null that is genuinely a null.
- Three decades is one sample of history. Two crashes dominate the trend gate's result, and no amount of resampling creates more history.
