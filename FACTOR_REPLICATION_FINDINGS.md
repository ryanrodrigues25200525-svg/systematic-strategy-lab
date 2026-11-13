# 🎩 Factor replication findings: the anomalies are real, the window is the problem

Notebooks 56 and 57 re-test every mechanism this library rejected at ETF level, using the portfolios the original papers used: Ken French decile and quintile sorts, snapshotted to `data/french/` with the CRSP vintage and a SHA-256 digest.

> Educational research only. Not financial advice. These are gross, frictionless long-short spreads.

## 📊 Momentum: 1,197 months, 1927-2026

| | Value |
| --- | --- |
| Long-short (decile 10 − decile 1) | **13.77%/yr**, 27.65% vol |
| Sharpe / t-statistic | **0.50** / **4.98** |
| Skewness / excess kurtosis | **−2.10** / 15.1 |
| Worst month / worst year | −77.7% (Aug 1932) / **−88.0%** (1932) |
| Maximum drawdown | **−95.56%** |
| Market beta since 1963 | **−0.67** |
| Volatility-managed (12% target, 6-month window) | Sharpe **0.73**, skew −0.69, max drawdown **−35.6%** |

Sharpe by era: 0.40 (1927-59), **1.03** (1960-89), 0.42 (1990-2009), **0.28** (2010-26). Vol-managed: 0.71 / 1.07 / 0.72 / **0.23** — better in three eras, worse in the most recent one.

The negative market beta is the mechanism of the crashes: the short leg is distressed, high-beta junk that rallies hardest in a recovery. 1932 and 2009 are not bad luck; they are the position.

## 📊 Reversal, value and quality

| Mechanism | Spread | Period | Mean | Sharpe | t |
| --- | --- | --- | ---: | ---: | ---: |
| Short-term reversal | decile 1 − 10, prior month | 1926-2026 | 9.44%/yr | 0.44 | **4.37** |
| Long-term reversal | decile 1 − 10, prior 60-13m | 1931-2026 | 5.41%/yr | 0.24 | **2.39** |
| Value | B/M quintile 5 − 1 | 1926-2026 | 5.02%/yr | 0.33 | **3.28** |
| Profitability | OP quintile 5 − 1 | 1963-2026 | 2.96%/yr | 0.28 | 2.22 |
| Investment | INV quintile 1 − 5 | 1963-2026 | 3.52%/yr | 0.39 | **3.14** |
| **Quality composite** | RMW + CMA, inverse-vol | 1963-2026 | 3.18%/yr | **0.43** | **3.33** |
| Quality, profitability only | RMW | 1963-2026 | 3.04%/yr | 0.28 | 2.18 |
| Quality, wrong sign | RMW − CMA | 1963-2026 | −0.38%/yr | −0.06 | −0.47 |

Quality composite by era: **0.93** (1963-89), 0.50 (1990-2009), **0.12** (2010-26).

## 🔍 The three answers this batch provides

**1. The ETF proxy was the problem for reversal, not for momentum.** Three-year reversal earned 0.19 Sharpe in 17 sector ETFs and earns t = 2.39 in the original stock-level deciles. A sector cross-section cannot express an overreaction effect: "the worst sector over five years" is a structurally declining industry, not an oversold stock. Momentum, by contrast, was measured about right at ETF level — the paper-scale factor is only a 0.50 Sharpe ratio because its volatility is enormous.

**2. Notebook 51's quality-composite finding replicates at 63 years.** Adding the investment leg takes Sharpe from 0.28 to 0.43 and t from 2.18 to 3.33, and the wrongly-signed version goes negative again (−0.06 Sharpe). The composite was not an artefact of ETF-era factor data.

**3. Everything is dormant in the only window a retail researcher can observe.** Post-2010 Sharpes: short-term reversal −0.02, long-term reversal −0.19, value −0.07, profitability −0.05, quality composite +0.12, investment +0.21. **Zero of six mechanisms clear t = 3 after 2010**, while four of six clear it on the full sample.

## 🧮 The power arithmetic that explains the whole repository

The large-sample standard error of an annualised Sharpe ratio is about `1 / sqrt(years)`, so the smallest Sharpe a sample can distinguish from zero at 80% power (two-sided 5%) is about `2.80 / sqrt(years)`.

| Window | Months | Min detectable Sharpe (80% power) |
| --- | ---: | ---: |
| 1926-2026 (100 years) | 1,203 | **0.28** |
| 1963-2026 (63 years) | 765 | 0.35 |
| 1990-2026 (36 years) | 441 | 0.46 |
| 2010-2026 (17 years) | 201 | **0.68** |
| *The repo's ETF test window (943 days)* | 45 | *1.45* |

The ETF-era mechanisms sit at or below 0.30 Sharpe. A 17-year test window cannot resolve them; the 943-day windows used in notebooks 50-53 could not resolve anything below 1.45.

## 🧠 The revised closing verdict

Notebooks 50-55 concluded "everything is beta". That was correct about *returns* but incomplete about *mechanisms*:

> **The anomalies are real and statistically overwhelming over a century. This library tested them in the seventeen years when they stopped working, on universes too coarse to express some of them, at sample sizes that could not have detected them anyway.**

Three separate failure modes, all of which look identical in an ETF backtest:

| Failure mode | Example | Evidence |
| --- | --- | --- |
| Dormant period | value, reversal, profitability post-2010 | t < 1 in every case over 17 years |
| Universe too coarse | three-year reversal in 17 sector ETFs | t = 2.39 at stock level, 0.19 Sharpe in ETFs |
| Insufficient power | everything in notebooks 50-53 | 943 days cannot detect a Sharpe below 1.45 |

## 🧩 Implementation

- [`src/french_data.py`](src/french_data.py) — tolerant parser for the Ken French CSV format (handles the vendor's `Aerage` typo, headerless factor files, value/equal-weight and monthly/annual blocks, `-99.99` missing codes), a disk cache with a manifest recording URL, retrieval time, CRSP vintage and SHA-256 per file, and `spread_returns` for long-short construction.
- [`scripts/snapshot_french_data.py`](scripts/snapshot_french_data.py) — builds the committed snapshot (8 files, 2.1 MB, vintage 202609).
- `src/factor_audit.py` — `minimum_detectable_sharpe(n_observations, annualization, alpha, power)`.
- **Bug fixed**: `deflated_sharpe_ratio` had `annualization=252` as a *default*, so a caller with monthly data silently divided the Sharpe ratio by `sqrt(252)` instead of `sqrt(12)` and turned a significant result into an unremarkable one. The parameter is now mandatory, and `kurtosis` became `excess_kurtosis` to match the pandas/scipy convention. Notebooks 54 and 55 were re-executed with the corrected call.

## 📓 Notebooks

- [56 — Momentum at paper scale](notebooks/56_momentum_at_paper_scale.ipynb)
- [57 — Reversal, value and quality at scale](notebooks/57_reversal_value_quality_at_scale.ipynb)

## ✅ Validation standards

- 11 new tests in `tests/test_french_data.py`, run against a local fixture so the suite never needs the network: section detection, the `Aerage` typo, a headerless factor file, the diagnostic block that must not overwrite returns, percent-to-decimal conversion, missing codes, vintage extraction, cache round-trip, and dataset/weighting validation. Plus 2 tests for `minimum_detectable_sharpe` and the annualization/excess-kurtosis contract.
- Both notebooks read the committed snapshot, so results cannot drift with a vendor revision; the manifest records the vintage beside every table.
- Multi-period era tables, deflated Sharpe with explicit frequency, block-bootstrap reality checks, and a power table that includes the repository's own test window.

## ⚠️ Limitations

- Gross returns, no transaction costs. Short-term reversal has enormous turnover; its 9.44%/yr is not a net figure.
- Value-weighted decile portfolios are not tradable at retail scale — decile 1 in 1932 is a bucket of tiny distressed firms.
- One country. These are US premia, and the post-2010 dormancy may be global or US-specific; this notebook cannot distinguish.
- Overlapping samples: eight hypotheses are tested on the same history, and the post-2010 conclusion rests on 17 years.
- The French portfolios are the papers' construction, not the papers' data: different CRSP vintages produce slightly different numbers, which is exactly why the snapshot records the vintage.
