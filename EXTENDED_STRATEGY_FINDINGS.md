# 🧭 Extended Strategy Findings

This report summarizes the additional hedge-fund-style and research-paper notebooks added in the second research batch. The numbers below are the executed formal-test outputs from the current Yahoo Finance sample and should be treated as proxy results, not investable performance claims.

## 📊 Formal test snapshot

| Notebook | Strategy family | Test Sharpe | Annualized return | Max drawdown |
| --- | --- | ---: | ---: | ---: |
| [25 — Pairs trading](notebooks/25_pairs_trading_gatev.ipynb) | Relative value / pairs | 1.32 | 7.43% | -6.70% |
| [26 — Sector residual stat arb](notebooks/26_statistical_arbitrage_sector_residuals.ipynb) | Equity market neutral | -1.16 | -1.60% | -5.21% |
| [27 — Betting against beta](notebooks/27_betting_against_beta.ipynb) | Low-beta long/short | -1.36 | -2.55% | -8.34% |
| [28 — Value and momentum everywhere](notebooks/28_value_momentum_everywhere.ipynb) | Cross-asset factor blend | -1.07 | -3.92% | -16.79% |
| [29 — Dual momentum](notebooks/29_dual_momentum_global_macro.ipynb) | Global macro rotation | 0.21 | 2.31% | -32.30% |
| [30 — Halloween seasonality](notebooks/30_halloween_seasonality.ipynb) | Calendar anomaly | 0.37 | 4.85% | -33.72% |
| [31 — Minimum variance](notebooks/31_minimum_variance_portfolio.ipynb) | Risk-first portfolio construction | 0.83 | 9.42% | -13.40% |
| [32 — Merger arbitrage proxy](notebooks/32_merger_arbitrage_proxy.ipynb) | Event-driven arbitrage | 1.29 | 6.00% | -3.02% |
| [33 — Volatility risk premium proxy](notebooks/33_volatility_risk_premium_proxy.ipynb) | Buy-write / short-volatility proxy | 0.90 | 10.29% | -15.42% |
| [34 — Convertible arbitrage proxy](notebooks/34_convertible_arbitrage_proxy.ipynb) | Convertible arbitrage proxy | 0.95 | 10.24% | -11.92% |
| [35 — Classic alternatives basket](notebooks/35_classic_alternatives_multi_strategy_basket.ipynb) | Multi-strategy diversification | 1.34 | 3.93% | -2.65% |

## 🧠 What the results suggest

- The strongest headline Sharpe ratios came from pairs trading, merger-arbitrage, and the diversified alternatives basket in this sample. That is not surprising: relative-value and alternative-ETF proxies can have lower directional exposure, while a diversified basket can smooth individual sleeve volatility.
- The sector residual and beta-spread tests were negative. That is useful evidence: a market-neutral label does not guarantee a positive result, especially when a small ETF universe, noisy estimates, shorting costs, and one fixed signal are used.
- Dual momentum and Halloween seasonality reduced neither drawdown nor opportunity cost enough in this particular test period. Calendar and trend filters can be late, whipsaw, or miss rebounds.
- The buy-write and convertible proxies delivered positive headline risk-adjusted results, but neither notebook reconstructs the actual hedged derivatives trade. Their returns remain exposed to ETF construction, equity beta, credit, option rolls, fees, and tail events.

## ⚠️ Implementation limits

The new notebooks intentionally distinguish a public strategy idea from a proprietary fund process. They generally do not include point-in-time stock universes, deal-level announcements, option chains, borrow fees, futures rolls, leverage, financing, margin, market impact, or internal ETF turnover. The right conclusion is therefore about the tested rule under stated assumptions—not about the live performance of any hedge fund or ETF.

## 📚 Research map

- [Gatev, Goetzmann, and Rouwenhorst — Pairs Trading](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1095996)
- [Avellaneda and Lee — Statistical Arbitrage in the US Equities Market](https://doi.org/10.1080/14697680903124632)
- [Frazzini and Pedersen — Betting Against Beta](https://pages.stern.nyu.edu/~afrazzin/pdf/Betting%20Against%20Beta%20-%20Frazzini%20and%20Pedersen.pdf)
- [Asness, Moskowitz, and Pedersen — Value and Momentum Everywhere](https://doi.org/10.1111/jofi.12021)
- [Antonacci — Risk Premia Harvesting Through Dual Momentum](https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2042750)
- [Jacobsen and Zhang — The Halloween Indicator](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2154873)
- [Clarke, de Silva, and Thorley — Minimum-Variance Portfolios](https://doi.org/10.3905/jpm.2006.661366)
- [Carr and Wu — Variance Risk Premiums](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1359527)
- [AQR — Arbitrage Strategies](https://funds.aqr.com/Insights/Strategies/Arbitrage)
- [AQR — DELTA Strategy](https://www.aqr.com/Insights/Research/Book/AQRs-DELTA-Strategy-A)
