# Public hedge-fund strategy proxy findings

This report records the current live ETF-proxy experiments in notebooks 08–11. The results are educational backtests, not fund performance, investment advice, or forecasts.

## What was tested

| Fund / idea | Transparent proxy | Current formal-test finding |
|---|---|---|
| AQR | Value, momentum, quality, defensive ETF sleeves, plus an equal-weight multi-style blend | The equal-weight multi-style blend had the highest test Sharpe among the tested AQR proxies: 1.32. The defensive proxy had the shallowest test drawdown: -9.36%. |
| Bridgewater | Four-asset All Weather-style inverse-volatility portfolio using SPY, TLT, GLD, and DBC | The equal-weight control had the highest test Sharpe: 0.81, and the shallowest test drawdown: -18.00%. The simple inverse-volatility proxy did not automatically improve the result. |
| Man AHL | Fast, medium, slow, and very-slow volatility-scaled time-series momentum across six ETF proxies | The 63-day medium-speed trend had the highest test Sharpe: 0.71. The 21-day fast model had the highest annualized turnover: 11.14, illustrating the speed/cost trade-off. |
| Winton | Multi-speed trend ensemble plus a 50/50 trend-and-SPY portable-alpha proxy | Portable alpha had the highest test Sharpe: 0.80. Its test return was 33.48% versus 13.74% for trend-only, with drawdown of -11.82% versus -15.29%. |

## How to interpret the findings

- Each notebook uses a chronological train/validation/test split, a one-bar execution delay, and a 10 bps cost assumption.
- Stress windows are descriptive diagnostics selected after the fact; they are not additional untouched test sets.
- The fund strategies are not exactly reproducible from public information. The proxies omit proprietary signals, broader universes, fundamental data, leverage, derivatives, financing, futures rolls, borrow costs, execution, and fees.
- A high Sharpe in one test period is not proof of a persistent edge. Read it together with return, volatility, drawdown, turnover, cost sensitivity, and crisis behavior.

## Sources

- [AQR — Understanding Factor Investing](https://funds.aqr.com/Insights/Strategies/Understanding-Factor-Investing)
- [AQR — Investing with Style](https://www.aqr.com/insights/research/journal-article/investing-with-style)
- [Bridgewater — The All Weather Story](https://www.bridgewater.com/research-and-insights/the-all-weather-story)
- [Man AHL — The Need for Speed in Trend-Following](https://www.man.com/insights/need-for-speed-trend-following)
- [Man AHL — Trend Following: Equity and Bond Crisis Alpha](https://www.man.com/insights/trend-following-equity-bond-crisis-alpha)
- [Winton — What is trend following?](https://www.winton.com/news/what-is-trend-following)
- [Winton — Portable Alpha UCITS launch](https://www.winton.com/news/winton-portable-alpha-ucits-launches-today)
