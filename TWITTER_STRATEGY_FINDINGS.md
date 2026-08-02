# 🐦 X/Twitter strategy audit findings

This report audits three publicly described strategy ideas found on X/Twitter. Each strategy has a separate executed notebook. The notebooks distinguish the source claim from the implementation that could actually be reproduced with the project’s data and backtester.

> Educational research only. Not financial advice. Historical proxy results are not guarantees of future performance.

## 📊 Results at a glance

| Strategy | Public claim or idea | Untouched-test result | Main lesson |
| --- | --- | --- | --- |
| MACD + RSI on SMH | QuantifiedStrategies post referenced 73% win rate, 8% CAGR, −46% drawdown, and 235 trades | **−2.73% annualized return; −0.32 Sharpe; −24.01% drawdown** after 10 bps costs | The public description omits a key filter, and a transparent approximation did not survive the later test period. |
| Minervini SEPA technical proxy | Trend template: price above rising moving averages, close to 52-week highs, well above 52-week lows | **7.14% annualized return; 0.58 Sharpe; −15.00% drawdown** after 10 bps costs | The technical subset was positive but lagged SPY’s 0.74 test Sharpe; missing fundamentals are a major limitation. |
| Filtered short-volatility proxy | Concretum described implied-versus-realized volatility, VIX term structure, and dynamic sizing | **−12.82% annualized return; −0.27 Sharpe; −43.05% drawdown** after 10 bps costs | Filters reduced 2018 and 2020 crash losses versus unfiltered short VXX, but the proxy still had severe risk and negative later-period returns. |

## 📓 Notebooks

- [38 — X MACD + RSI on SMH](notebooks/38_x_macd_rsi_smh.ipynb)
- [39 — X Minervini SEPA technical proxy](notebooks/39_x_minervini_sepa_proxy.ipynb)
- [40 — X volatility risk-premium proxy](notebooks/40_x_volatility_risk_premium_proxy.ipynb)

## 🔎 What the checks found

### MACD + RSI approximation

The source article reports a 73% win rate and 8% CAGR, but the public X post does not fully specify the third mean-reversion filter. The notebook uses standard MACD 12/26/9, Wilder-style RSI(14), RSI below 50, and close below a 5-day mean as an explicit approximation.

- The untouched test was negative: −2.73% annualized return and −0.32 Sharpe after 10 bps costs.
- The approximation had 43.10% test win rate, so the public 73% win-rate claim was not reproduced.
- At zero transaction costs, test Sharpe was still −0.16; at 50 bps, it fell to −0.91.
- The best validation combination in the small sensitivity grid reached 1.01 validation Sharpe but only −0.33 test Sharpe, a clear example of why validation selection is not proof.

### Minervini SEPA technical proxy

The X post lists the technical trend template but also emphasizes earnings, sales growth, relative strength, institutional sponsorship, catalysts, and volatility-contraction patterns. The notebook tests only the price/ moving-average / 52-week-range conditions across SPY, QQQ, SMH, IWM, XLK, and XLF.

- The untouched test returned 7.14% annually with 0.58 Sharpe and −15.00% drawdown.
- SPY buy and hold returned 12.13% annually with 0.74 Sharpe and −24.50% drawdown in the same test period.
- The proxy’s shallower drawdown is useful, but its lower return and Sharpe show the cost of comparing a filtered allocation with a simple equity benchmark.
- Nearby threshold combinations behaved similarly because the moving-average trend conditions dominated the 52-week-range thresholds.

### Filtered short-volatility proxy

The notebook uses VXX as a long-volatility product proxy, VIX and VIX3M as implied-volatility inputs, and SPY realized volatility. It shorts VXX only when the implied premium is positive, the term structure is in contango, and VIX is not in an extreme spike; exposure is capped at one. The common live-data sample begins in 2018 because the downloaded series overlap only from 2018-01-25.

- The filtered proxy’s test result was negative: −12.82% annualized return, −0.27 Sharpe, and −43.05% drawdown after 10 bps costs.
- It was materially safer than unfiltered short VXX in stress windows: −3.98% versus −46.94% in the 2018 Volmageddon window, and −8.55% versus −79.04% in the 2020 COVID window.
- The filter did not make the strategy safe; a −43% later-period drawdown is still unacceptable for many portfolios.
- VXX is not an options portfolio, and this test does not model borrow, margin, collateral yield, option greeks, or forced deleveraging.

## 🧭 Research judgment

The most valuable result here is not a new high-Sharpe winner. It is the separation between: public claims, exact rules, proxy assumptions, and untouched-test behavior. The X sources supplied useful hypotheses, but the executed evidence shows that incomplete rules, missing fundamentals, product mechanics, and regime dependence can dominate a headline statistic.

## 🔗 Sources

- [QuantifiedStrategies X post](https://x.com/QuantifiedStrat/status/2013527816940462540)
- [QuantifiedStrategies MACD + RSI article](https://www.quantifiedstrategies.com/?p=133255)
- [Market Rebellion X post summarizing Minervini SEPA](https://x.com/RebellioMarket/status/2018972895304894065)
- [Concretum Research X post on volatility trading](https://x.com/ConcretumR/status/1952298941745172695)
- [Bloomberg Twitter sentiment research report](https://developer.twitter.com/content/dam/developer-twitter/pdfs-and-files/Bloomberg-Twitter-Data-Research-Report.pdf)

## ✅ Validation standards

- All three notebooks executed top-to-bottom with no stored execution errors.
- Data came from the project’s Yahoo Finance loader with deterministic fallback code available.
- Signals and target weights are delayed before returns are applied.
- Costs, chronological train/validation/test splits, and stress windows are visible in the notebooks.
- Proxy and source-implementation gaps are explicitly documented.
