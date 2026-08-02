# 🗺️ Research map and learning guide

This guide shows how the repository moves from a market anomaly to a reproducible experiment. The arrows are deliberately explicit: a paper is not a backtest, a backtest is not an investment product, and a result is not complete until its limitations are recorded.

## 🔭 Visual roadmap

~~~mermaid
flowchart LR
    A["Market anomaly or economic intuition"] --> B["Paper, public fund description, or public claim"]
    B --> C["Precise rule and information timing"]
    C --> D["Reusable implementation"]
    D --> E["Gross and after-cost result"]
    E --> F["Robustness, regimes, and audit"]
    F --> G["Conclusion: what went well, what went wrong, limitations"]

    A1["Momentum"] --> B1["Jegadeesh–Titman / 12–1 evidence"]
    B1 --> C1["Rank prior returns, skip the latest month"]
    C1 --> D1["Notebook 13 or 41"]
    D1 --> E1["Performance table"]
    E1 --> F1["Costs, crashes, test split"]
    F1 --> G1["Proxy and implementation caveats"]

    A2["Profitability"] --> B2["Fama–French operating profitability"]
    B2 --> C2["June accounting sort, July–June holding period"]
    C2 --> D2["Notebook 49"]
    D2 --> E2["RMW factor history"]
    E2 --> F2["Cost scenarios and rolling behavior"]
    F2 --> G2["Published factor, not a security-level screener"]

    A3["Diversification"] --> B3["Risk-parity and multi-style research"]
    B3 --> C3["Define sleeves, weights, and rebalance timing"]
    C3 --> D3["Notebook 47"]
    D3 --> E3["Ensemble versus SPY and 60/40"]
    E3 --> F3["Correlation, risk contribution, drawdown"]
    F3 --> G3["Hand-selected sleeves and proxy limitations"]

    A4["Research integrity"] --> B4["Backtest-quality methods"]
    B4 --> C4["Execution, validation, and uncertainty checks"]
    C4 --> D4["Notebook 48"]
    D4 --> E4["Audit output"]
    E4 --> F4["Bootstrap, factors, costs, PBO-style proxy"]
    F4 --> G4["Not a formal statistical guarantee"]
~~~

## 📚 Repository map

| Research layer | What to learn | Where to start | Main limitation to remember |
| --- | --- | --- | --- |
| Baselines | Buy and hold, simple indicators, consistent metrics | [01](notebooks/01_buy_and_hold.ipynb) → [04](notebooks/04_multi_asset_portfolios.ipynb) | A benchmark is necessary, but it is not a strategy explanation |
| Academic replications | Momentum, mean reversion, regime filters, portfolio construction | [05](notebooks/05_paper_strategy_replications.ipynb) → [07](notebooks/07_additional_paper_replications.ipynb) | ETF proxies are not the original stock-level samples |
| Fund-style research | AQR factors, Bridgewater-style risk balancing, Man AHL and Winton trend | [08](notebooks/08_aqr_fund_replication.ipynb) → [24](notebooks/24_winton_portable_alpha.ipynb) | Public descriptions cannot reveal proprietary signals or execution |
| Alternatives and event-driven ideas | Pairs, stat arb, beta, seasonality, merger and volatility proxies | [25](notebooks/25_pairs_trading_gatev.ipynb) → [35](notebooks/35_classic_alternatives_multi_strategy_basket.ipynb) | Liquid alternative ETFs can hide leverage, fees, and path dependence |
| Public claim audits | Reddit and X/Twitter claims with incomplete rules | [36](notebooks/36_reddit_ibs_mean_reversion.ipynb) → [40](notebooks/40_x_volatility_risk_premium_proxy.ipynb) | A headline Sharpe or win rate is not a reproducible specification |
| More paper strategies | Risk-managed momentum, 52-week high, industry momentum | [41](notebooks/41_paper_risk_managed_momentum.ipynb) → [43](notebooks/43_paper_industry_momentum.ipynb) | A proxy can answer a narrower question than the paper |
| Original hypotheses | Combinations built from earlier evidence | [44](notebooks/44_adaptive_regime_ensemble.ipynb) → [46](notebooks/46_signal_consensus_target_risk.ipynb) | Novelty alone is not evidence; simpler controls still matter |
| Portfolio capstone | Correlation, risk contribution, drawdown and benchmark context | [47](notebooks/47_capstone_multi_strategy_portfolio.ipynb) | Equal capital is a design choice, not an optimal allocation |
| Research-quality audit | Timing, bootstrap uncertainty, parameter stability, factor exposure | [48](notebooks/48_backtest_quality_audit.ipynb) | The PBO-style cell is a warning proxy, not a formal PBO estimate |
| Fundamentals | Historical stock-level profitability construction | [49](notebooks/49_stock_level_profitability_factor.ipynb) | Published factor data does not expose holdings, borrow, or exact turnover |

## 🧑‍🎓 Suggested beginner learning path

### 1. Learn the mechanics

Read [01](notebooks/01_buy_and_hold.ipynb), [02](notebooks/02_moving_average_crossover.ipynb), and [03](notebooks/03_strategy_comparison.ipynb). Focus on:

- what a return series is;
- why a signal must be shifted before returns are applied;
- why a benchmark and transaction-cost assumption belong in the same table as the strategy;
- how maximum drawdown differs from volatility.

### 2. Learn strategy families

Use [04](notebooks/04_multi_asset_portfolios.ipynb), [12](notebooks/12_aqr_value_factor.ipynb), [13](notebooks/13_aqr_momentum_factor.ipynb), [17](notebooks/17_bridgewater_all_weather_proxy.ipynb), and [20](notebooks/20_man_ahl_slow_trend.ipynb). Ask what each strategy is paid to endure:

- value can be cheap for a reason;
- momentum can crash during sharp reversals;
- trend can whipsaw in sideways markets;
- diversification depends on changing correlations.

### 3. Learn how research claims are tested

Read one paper-inspired notebook, one fund proxy, and one public-claim audit:

1. [41](notebooks/41_paper_risk_managed_momentum.ipynb)
2. [23](notebooks/23_winton_trend_ensemble.ipynb)
3. [36](notebooks/36_reddit_ibs_mean_reversion.ipynb)

Compare how much of the original claim survives after rules become explicit.

### 4. Study original ideas without skipping controls

Read [44](notebooks/44_adaptive_regime_ensemble.ipynb), [45](notebooks/45_crisis_aware_ibs_mean_reversion.ipynb), and [46](notebooks/46_signal_consensus_target_risk.ipynb). For each, read the simpler control before the original strategy and inspect the crisis windows only as descriptive diagnostics.

### 5. Finish with the capstone and audit

Read [47](notebooks/47_capstone_multi_strategy_portfolio.ipynb), then [48](notebooks/48_backtest_quality_audit.ipynb), then [49](notebooks/49_stock_level_profitability_factor.ipynb). This sequence moves from combining sleeves, to checking the research process, to using historical accounting information with explicit formation timing.

## 🧪 How to extend the map

For any new strategy, add one row only after answering these questions:

1. What anomaly or economic mechanism is being tested?
2. What is the primary paper, public description, or claim?
3. What exact information is available at the decision time?
4. What is the simplest implementable rule?
5. What is the benchmark and what are realistic costs?
6. Which parameter choices were made before the final test?
7. What went well, what went wrong, and what remains untested?

That checklist is the research habit this repository is designed to demonstrate.
