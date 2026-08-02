# 🧪 Systematic Strategy Lab

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)
![Research](https://img.shields.io/badge/Focus-reproducible%20research-2E8B57)
![Status](https://img.shields.io/badge/status-educational%20research-6C757D)

> A transparent, beginner-friendly research library for testing systematic trading ideas under one consistent backtesting framework.

This repository studies trading strategies as research questions—not as promises of future returns. Each notebook explains the idea, defines the rules, runs the test, shows what happened, and records both the strengths and failure modes.

**Educational research only. Not financial advice. Historical backtests are not guarantees of future performance.**

---

## 💡 Why this project exists

Trading strategies are easy to describe and easy to overstate. This project is designed to make the important details visible:

- What information was available when the signal was created?
- When could the strategy actually trade?
- How much did turnover and transaction costs matter?
- Did the idea work only in one market regime?
- What went well—and what went wrong?

The goal is not to find one magical strategy. The goal is to build sound research habits and a reusable library of experiments.

## 📊 At a glance

| Component | Current implementation |
| --- | --- |
| Research notebooks | 46 runnable notebooks |
| Automated tests | 14 passing tests |
| Data | Adjusted Yahoo Finance prices, with deterministic offline demo fallback |
| Execution model | Signal at `t` earns returns from `t + 1` |
| Default cost | 10 basis points per unit of absolute exposure change |
| Validation | Chronological train / validation / untouched test split |
| Metrics | Return, volatility, Sharpe, Sortino, drawdown, Calmar, win rate, turnover, trades |
| Scope | Long-only, long/short, cross-sectional, multi-asset, factor, trend, and crisis-aware strategies |

## 🚀 Start here

If you are new to the project, read in this order:

1. [Buy-and-hold baseline](notebooks/01_buy_and_hold.ipynb)
2. [Moving-average crossover](notebooks/02_moving_average_crossover.ipynb)
3. [Strategy comparison](notebooks/03_strategy_comparison.ipynb)
4. [Multi-asset portfolios](notebooks/04_multi_asset_portfolios.ipynb)
5. [Paper strategy replications](notebooks/05_paper_strategy_replications.ipynb)
6. [Regime and crisis strategies](notebooks/06_regime_and_crisis_strategies.ipynb)
7. [Additional paper replications](notebooks/07_additional_paper_replications.ipynb)

Then explore the fund research:

- [Fund comparison overview](notebooks/08_aqr_fund_replication.ipynb)
- [Bridgewater All Weather overview](notebooks/09_bridgewater_all_weather.ipynb)
- [Man AHL trend overview](notebooks/10_man_ahl_trend_following.ipynb)
- [Winton trend and portable alpha overview](notebooks/11_winton_trend_and_portable_alpha.ipynb)
- [Fund strategy findings report](FUND_STRATEGY_FINDINGS.md)
- [Extended strategy findings report](EXTENDED_STRATEGY_FINDINGS.md)
- [Reddit strategy audit findings](REDDIT_STRATEGY_FINDINGS.md)
- [X/Twitter strategy audit findings](TWITTER_STRATEGY_FINDINGS.md)
- [New research-paper strategy findings](PAPER_STRATEGY_FINDINGS.md)
- [Original strategy findings](ORIGINAL_STRATEGY_FINDINGS.md)

---

## 🗂️ Strategy index

Every distinct fund strategy also has its own standalone notebook. The overview notebooks compare related ideas; the standalone notebooks go deep on one idea at a time.

### 📐 AQR-style factor research

Public AQR material discusses systematic value, momentum, quality, and defensive styles. These notebooks use liquid ETF proxies and clearly label the implementation gap.

| Strategy | Notebook | Proxy |
| --- | --- | --- |
| Value factor | [12 — AQR value factor](notebooks/12_aqr_value_factor.ipynb) | VTV |
| Momentum factor | [13 — AQR momentum factor](notebooks/13_aqr_momentum_factor.ipynb) | MTUM |
| Quality factor | [14 — AQR quality factor](notebooks/14_aqr_quality_factor.ipynb) | QUAL |
| Defensive factor | [15 — AQR defensive factor](notebooks/15_aqr_defensive_factor.ipynb) | USMV |
| Multi-style blend | [16 — AQR multi-style blend](notebooks/16_aqr_multi_style_blend.ipynb) | VTV + MTUM + QUAL + USMV |

### 🌦️ Bridgewater-style risk balancing

| Strategy | Notebook | Proxy |
| --- | --- | --- |
| All Weather risk balancing | [17 — Bridgewater All Weather proxy](notebooks/17_bridgewater_all_weather_proxy.ipynb) | SPY + TLT + GLD + DBC, inverse-volatility weights |

### 📈 Man AHL-style trend following

| Strategy | Notebook | Rule |
| --- | --- | --- |
| Fast trend | [18 — Man AHL fast trend](notebooks/18_man_ahl_fast_trend.ipynb) | 21-day time-series momentum |
| Medium trend | [19 — Man AHL medium trend](notebooks/19_man_ahl_medium_trend.ipynb) | 63-day time-series momentum |
| Slow trend | [20 — Man AHL slow trend](notebooks/20_man_ahl_slow_trend.ipynb) | 126-day time-series momentum |
| Very slow trend | [21 — Man AHL very-slow trend](notebooks/21_man_ahl_very_slow_trend.ipynb) | 252-day time-series momentum |
| Multi-speed blend | [22 — Man AHL multi-speed blend](notebooks/22_man_ahl_multi_speed_blend.ipynb) | Average of 21 / 63 / 126 / 252-day sleeves |

### 🌊 Winton-style trend research

| Strategy | Notebook | Rule |
| --- | --- | --- |
| Diversified trend ensemble | [23 — Winton trend ensemble](notebooks/23_winton_trend_ensemble.ipynb) | Multi-speed trend across six ETF markets |
| Portable alpha | [24 — Winton portable alpha](notebooks/24_winton_portable_alpha.ipynb) | 50% SPY + 50% diversified trend |

### 🧰 Extended hedge-fund and paper research

These notebooks cover additional relative-value, market-neutral, factor, macro, event-driven, volatility, and portfolio-construction ideas. They are public-concept proxies—not proprietary fund replications.

| Strategy | Notebook | Research family / proxy |
| --- | --- | --- |
| Pairs trading | [25 — Pairs trading](notebooks/25_pairs_trading_gatev.ipynb) | Gatev–Goetzmann–Rouwenhorst; KO / PEP spread |
| Sector residual statistical arbitrage | [26 — Sector residual stat arb](notebooks/26_statistical_arbitrage_sector_residuals.ipynb) | Avellaneda–Lee; long–short sector residual proxy |
| Betting against beta | [27 — Betting against beta](notebooks/27_betting_against_beta.ipynb) | Frazzini–Pedersen; low-beta / high-beta spread |
| Value and momentum everywhere | [28 — Value and momentum](notebooks/28_value_momentum_everywhere.ipynb) | Asness–Moskowitz–Pedersen; cross-asset blend |
| Dual momentum global macro | [29 — Dual momentum](notebooks/29_dual_momentum_global_macro.ipynb) | Antonacci; relative plus absolute momentum |
| Halloween seasonality | [30 — Halloween effect](notebooks/30_halloween_seasonality.ipynb) | Jacobsen–Zhang; November–April exposure |
| Minimum variance | [31 — Minimum variance](notebooks/31_minimum_variance_portfolio.ipynb) | Clarke–de Silva–Thorley; covariance-based weights |
| Merger arbitrage | [32 — Merger arbitrage proxy](notebooks/32_merger_arbitrage_proxy.ipynb) | Event-driven ETF proxy: MNA |
| Volatility risk premium | [33 — Volatility risk premium](notebooks/33_volatility_risk_premium_proxy.ipynb) | Carr–Wu; buy-write ETF proxy: PBP |
| Convertible arbitrage | [34 — Convertible arbitrage proxy](notebooks/34_convertible_arbitrage_proxy.ipynb) | Liquid alternatives proxy: CWB |
| Classic alternatives basket | [35 — Multi-strategy basket](notebooks/35_classic_alternatives_multi_strategy_basket.ipynb) | AQR DELTA-style diversified proxy basket |

See [Extended Strategy Findings](EXTENDED_STRATEGY_FINDINGS.md) for the observed test-period results and the implementation caveats behind each proxy.

### 💬 Reddit strategy audits

These notebooks audit reproducible Reddit claims, including a high-Sharpe mean-reversion headline and a dual-momentum allocation idea. The claims are shown beside cost-aware, untouched-test results.

| Strategy | Notebook | Audit focus |
| --- | --- | --- |
| IBS lower-band mean reversion | [36 — Reddit IBS mean reversion](notebooks/36_reddit_ibs_mean_reversion.ipynb) | Original four-rule setup versus a reported 2.11-Sharpe improved version |
| Global dual momentum rotation | [37 — Reddit dual momentum](notebooks/37_reddit_dual_momentum.ipynb) | SPY / EFA relative momentum with a 200-day trend filter and TLT defense |

See [Reddit Strategy Audit Findings](REDDIT_STRATEGY_FINDINGS.md) for the claim-versus-reproduction summary.

### 🐦 X/Twitter strategy audits

These notebooks audit public X/Twitter strategy descriptions while labeling incomplete rules and proxy implementations clearly.

| Strategy | Notebook | Audit focus |
| --- | --- | --- |
| MACD + RSI mean reversion | [38 — X MACD + RSI on SMH](notebooks/38_x_macd_rsi_smh.ipynb) | Public 73% win-rate claim versus a transparent approximation |
| Minervini SEPA trend template | [39 — X Minervini SEPA proxy](notebooks/39_x_minervini_sepa_proxy.ipynb) | Technical moving-average and 52-week-range subset across ETFs |
| Filtered volatility risk premium | [40 — X volatility-risk-premium proxy](notebooks/40_x_volatility_risk_premium_proxy.ipynb) | VIX/VIX3M filters, dynamic sizing, and short-volatility stress tests |

See [X/Twitter Strategy Audit Findings](TWITTER_STRATEGY_FINDINGS.md) for the claim-versus-reproduction summary.

### 📚 New academic paper replications

These notebooks add distinct paper-inspired tests for momentum crashes, 52-week-high momentum, and industry momentum. Each one includes the paper citation, a transparent ETF proxy, out-of-sample results, cost sensitivity, and a failure analysis.

| Paper strategy | Notebook | Research question |
| --- | --- | --- |
| Risk-managed momentum | [41 — Volatility-managed momentum](notebooks/41_paper_risk_managed_momentum.ipynb) | Does scaling momentum exposure reduce crash risk? |
| 52-week-high momentum | [42 — 52-week-high momentum](notebooks/42_paper_52_week_high_momentum.ipynb) | Does closeness to a 52-week high add information beyond 12–1 momentum? |
| Industry momentum | [43 — Industry momentum](notebooks/43_paper_industry_momentum.ipynb) | Does momentum persist at the sector level? |

See [New Research-Paper Strategy Findings](PAPER_STRATEGY_FINDINGS.md) for the claim-versus-reproduction summary.

### 🧠 Original strategy experiments

These notebooks combine ideas from the earlier paper, fund, Reddit, and X/Twitter research into new, explicitly labeled hypotheses. They are compared against simpler baselines and include crisis diagnostics so the library does not reward complexity by default.

| Original strategy | Notebook | Ingredients |
| --- | --- | --- |
| Adaptive regime ensemble | [44 — Adaptive regime ensemble](notebooks/44_adaptive_regime_ensemble.ipynb) | Momentum + 52-week-high proximity + trend gate + inverse volatility + defensive fallback |
| Crisis-aware IBS mean reversion | [45 — Crisis-aware IBS](notebooks/45_crisis_aware_ibs_mean_reversion.ipynb) | IBS mean reversion + 200-day trend filter + VIX circuit breakers |
| Signal-consensus target-risk allocation | [46 — Signal-consensus allocation](notebooks/46_signal_consensus_target_risk.ipynb) | Fast/slow trend agreement + momentum + high-volatility selectivity |

See [Original Strategy Findings](ORIGINAL_STRATEGY_FINDINGS.md) for the out-of-sample results and tradeoffs.

---

## 🔬 Research workflow

Every notebook follows the same reader-friendly structure:

1. **Idea** — What market behavior or economic intuition motivates the strategy?
2. **Rules** — What are the exact signals, positions, sizing rules, and rebalance schedule?
3. **Data** — What assets, dates, benchmark, costs, and limitations are used?
4. **Implementation** — How is look-ahead bias avoided?
5. **Results** — What happened to return, risk, drawdown, turnover, and benchmark-relative performance?
6. **Robustness** — Do costs, parameters, other periods, or crisis windows change the conclusion?
7. **Review** — What went well, what went wrong, and what should a beginner learn from it?

## 📌 Current findings snapshot

These are the latest formal-test observations from the standalone fund notebooks. They are sample-specific proxy results, not fund returns.

| Research family | Observed result | Main lesson |
| --- | --- | --- |
| AQR multi-style blend | Highest test Sharpe among the AQR proxies: **1.32** | Combining styles can smooth the path, but the ETF implementation is not the original stock-level process. |
| AQR defensive proxy | Shallowest AQR-proxy drawdown: **-9.36%** | Lower risk can mean a more tolerable path, but it may lag strong equity markets. |
| Bridgewater All Weather proxy | Test Sharpe: **0.72** | Inverse volatility does not automatically improve on every control; correlations matter. |
| Man AHL medium trend | Test Sharpe: **0.71** | Medium speed was more balanced in this sample than the fast or slow alternatives. |
| Man AHL fast trend | Test Sharpe: **-0.15**; annualized turnover: **11.14** | Faster response can come with whipsaws and materially higher trading activity. |
| Winton portable alpha | Test Sharpe: **0.80**; test drawdown: **-11.82%** | Adding an equity sleeve changed both return and crisis behavior versus trend alone. |

For the full tables, cost checks, and stress-window diagnostics, read [FUND_STRATEGY_FINDINGS.md](FUND_STRATEGY_FINDINGS.md), [EXTENDED_STRATEGY_FINDINGS.md](EXTENDED_STRATEGY_FINDINGS.md), and the individual notebooks.

## 🛡️ Methodological standards

### 🚫 No-lookahead execution

Signals use information through the close of day `t`. The backtester shifts positions by one bar before applying the return from `t` to `t + 1`.

### 💸 Realistic costs

Costs are charged on absolute exposure changes. Each notebook exposes the default 10 bps assumption and tests a range of higher and lower costs where turnover is important.

### 🗓️ Chronological validation

The notebooks use chronological train, validation, and test periods. The final test period is not used to select parameters. Crisis windows are labeled as descriptive diagnostics because they are chosen after the fact.

### 🧾 Honest failure analysis

An unsuccessful or cost-sensitive strategy is still a useful result. The notebooks do not hide whipsaws, missed rebounds, drawdowns, proxy limitations, or strategies that lose their appeal after costs.

## 💻 Run the project locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
jupyter notebook
```

To execute a notebook from the command line:

```bash
python -m jupyter nbconvert \
  --execute \
  --to notebook \
  --inplace \
  --ExecutePreprocessor.timeout=600 \
  notebooks/12_aqr_value_factor.ipynb
```

If Yahoo Finance is unavailable, set `USE_DEMO_DATA = True` in the notebook's data cell. The demo data is deterministic and exists only to validate the workflow—not to provide market evidence.

## 🗃️ Project structure

```text
systematic-strategy-lab/
├── notebooks/
│   ├── 01–07  foundation and paper-replication notebooks
│   ├── 08–11  fund comparison overview notebooks
│   └── 12–24  fund strategy proxies; 25–46 extended paper, hedge-fund, Reddit, X/Twitter, research-paper, and original strategy audits
├── src/
│   ├── backtest.py       single-asset backtesting and execution timing
│   ├── data.py           Yahoo Finance loader and deterministic demo data
│   ├── fund_strategies.py fund-specific transparent trend proxy
│   ├── metrics.py        consistent performance metrics
│   ├── plots.py          reusable chart helpers
│   ├── portfolio.py      portfolio weights and portfolio backtests
│   ├── research.py       chronological comparison helpers
│   └── strategies.py     single-asset signal builders
├── scripts/
│   ├── generate_fund_strategy_notebooks.py
│   └── create_reddit_notebooks.py
├── tests/
│   └── test_backtest.py
├── FUND_STRATEGY_FINDINGS.md
├── requirements.txt
└── README.md
```

## ⚠️ Important limitations

The fund notebooks are public-concept proxies, not exact replications. They generally do not model:

- point-in-time fundamentals or survivorship-free stock universes;
- proprietary signals, portfolio optimizers, and execution systems;
- futures rolls, FX forwards, margin, leverage, collateral income, financing, or borrow costs;
- taxes, bid-ask spread variation, market impact, and capacity constraints;
- changes in asset correlations during a crisis.

The results should therefore be read as research on simplified rules under explicit assumptions.

## 📚 Selected research sources

- [AQR — Understanding Factor Investing](https://funds.aqr.com/Insights/Strategies/Understanding-Factor-Investing)
- [AQR — Investing with Style](https://www.aqr.com/insights/research/journal-article/investing-with-style)
- [AQR — Understanding Defensive Equity](https://www.aqr.com/Insights/Research/White-Papers/Understanding-Defensive-Equity)
- [Bridgewater — The All Weather Story](https://www.bridgewater.com/research-and-insights/the-all-weather-story)
- [Man AHL — The Need for Speed in Trend-Following](https://www.man.com/insights/need-for-speed-trend-following)
- [Man AHL — Trend Following: Equity and Bond Crisis Alpha](https://www.man.com/insights/trend-following-equity-bond-crisis-alpha)
- [Winton — What is trend following?](https://www.winton.com/news/what-is-trend-following)
- [Winton — Portable Alpha UCITS launch](https://www.winton.com/news/winton-portable-alpha-ucits-launches-today)
- [Moskowitz, Ooi, and Pedersen — Time Series Momentum](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf)
- [Moreira and Muir — Volatility-Managed Portfolios](https://doi.org/10.1111/jofi.12513)
- [Frazzini and Pedersen — Betting Against Beta](https://www.nber.org/papers/w16601)
- [Bailey et al. — The Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659)
- [Gatev, Goetzmann, and Rouwenhorst — Pairs Trading](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1095996)
- [Avellaneda and Lee — Statistical Arbitrage](https://doi.org/10.1080/14697680903124632)
- [Frazzini and Pedersen — Betting Against Beta](https://pages.stern.nyu.edu/~afrazzin/pdf/Betting%20Against%20Beta%20-%20Frazzini%20and%20Pedersen.pdf)
- [Asness, Moskowitz, and Pedersen — Value and Momentum Everywhere](https://doi.org/10.1111/jofi.12021)
- [Antonacci — Risk Premia Harvesting Through Dual Momentum](https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2042750)
- [Jacobsen and Zhang — The Halloween Indicator](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2154873)
- [Clarke, de Silva, and Thorley — Minimum-Variance Portfolios](https://doi.org/10.3905/jpm.2006.661366)
- [Carr and Wu — Variance Risk Premiums](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1359527)
- [AQR — Arbitrage Strategies](https://funds.aqr.com/Insights/Strategies/Arbitrage)
- [AQR — DELTA Strategy](https://www.aqr.com/Insights/Research/Book/AQRs-DELTA-Strategy-A)
- [Reddit — IBS mean-reversion strategy](https://www.reddit.com/r/algotrading/comments/1cwsco8/a_mean_reversion_strategy_with_211_sharpe/)
- [Reddit — leveraged dual momentum backtest](https://www.reddit.com/r/LETFs/comments/1jj4tad/leveraged_dual_momentum_backtest/)
- [Reddit — discussion of realistic Sharpe ratios](https://www.reddit.com/r/quant/comments/1u16w3p/are_longterm_sharpe_ratios_above_3_and_30_annual/)
- [QuantifiedStrategies — MACD + RSI X post](https://x.com/QuantifiedStrat/status/2013527816940462540)
- [Market Rebellion — Minervini SEPA X post](https://x.com/RebellioMarket/status/2018972895304894065)
- [Concretum Research — volatility trading X post](https://x.com/ConcretumR/status/1952298941745172695)
- [Barroso and Santa-Clara — Momentum Has Its Moments](https://doi.org/10.1016/j.jfineco.2014.11.010)
- [Daniel and Moskowitz — Momentum Crashes](https://www.nber.org/papers/w20439)
- [Liu, Liu, and Ma — 52-week-high momentum](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1364566)
- [Moskowitz and Grinblatt — Do Industries Explain Momentum?](https://doi.org/10.1111/0022-1082.00146)
- [Clare, Seaton, Smith, and Thomas — The Trend Is Our Friend](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2265693)
- [Goulding, Harvey, and Mazzoleni — Momentum Turning Points](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3489539)

## ⚖️ License and disclaimer

This repository is intended for educational research and portfolio demonstration. It is not financial advice, an offer to buy or sell securities, or a guarantee of future performance. Before treating any result as investable research, replace the simplified data and cost assumptions with point-in-time, instrument-appropriate data and independent validation.
