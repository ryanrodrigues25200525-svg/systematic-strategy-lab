# 📅 Calendar effect findings

This batch tests four calendar anomalies on SPY: the turn-of-month window, the pre-holiday session, the pre-FOMC announcement drift, and day-of-week patterns. Every effect is reported twice — as a per-day return difference with a t-statistic, and as a tradeable strategy after costs.

> Educational research only. Not financial advice. Historical results are not guarantees of future performance.

## 📊 Per-day statistics (SPY, 1993-01-29 to 2025-12-31)

| Effect | Window days | Share of days | Mean inside | Mean outside | Difference | Welch t |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Turn of month | 1,580 | 19.1% | 7.41 bps | 4.08 bps | +3.32 bps | +1.03 |
| Pre-holiday | 295 | 3.6% | 10.85 bps | 4.49 bps | +6.35 bps | +1.13 |
| Pre-FOMC (2011+) | 120 | 1.4% | 15.76 bps | 4.55 bps | +11.20 bps | +1.06 |
| Monday | 1,558 | 18.8% | 5.35 bps | 4.57 bps | +0.78 bps | +0.22 |
| Tuesday | 1,702 | 20.5% | 7.21 bps | 4.07 bps | +3.14 bps | +0.99 |
| Wednesday | 1,700 | 20.5% | 5.89 bps | 4.41 bps | +1.47 bps | +0.47 |
| Thursday | 1,667 | 20.1% | 1.62 bps | 5.50 bps | -3.88 bps | -1.21 |
| Friday | 1,660 | 20.0% | 3.48 bps | 5.03 bps | -1.55 bps | -0.50 |

## 📉 The same effects as strategies

| Effect | Sharpe @ 0 bps | @ 2 bps | @ 10 bps |
| --- | ---: | ---: | ---: |
| Turn of month | 0.45 | 0.39 | 0.15 |
| Pre-holiday | 0.34 | 0.22 | -0.29 |
| Pre-FOMC (2011+) | 0.26 | 0.19 | -0.07 |
| Wednesday | 0.37 | 0.12 | -0.89 |
| Monday | 0.29 | 0.07 | -0.78 |
| Friday | 0.22 | -0.03 | -1.06 |
| Union of all three windows | 0.58 | 0.48 | 0.11 |
| **SPY buy and hold** | **0.64** | 0.64 | 0.64 |

## 🕰️ Decay check

| Block | Turn-of-month inside | Outside | t | Pre-holiday inside | t |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1993–2005 | 11.46 bps | 2.85 bps | +1.72 | 5.00 bps | +0.05 |
| 2006–2015 | 4.31 bps | 3.46 bps | +0.14 | 10.53 bps | +0.63 |
| 2016–2025 | 5.27 bps | 6.31 bps | -0.19 | 18.26 bps | +1.60 |

## 🧠 What the results suggest

- **Every event effect points the documented way, and none of them is significant.** Turn-of-month +3.3 bps per day, pre-holiday +6.4, pre-FOMC +11.2. The largest t-statistic in the whole table is 1.21 — and it belongs to Thursday, in the *opposite* direction to the folk Monday effect.
- **The turn-of-month premium decayed.** +1.72 t in 1993–2005, +0.14 in 2006–2015, and -0.19 in 2016–2025, where in-window days were *worse* than other days. That is the signature of a published and arbitraged anomaly.
- **The pre-holiday effect looks like it moved rather than died.** It is strongest in the most recent block (+1.60), which is the opposite pattern to turn-of-month. With 295 observations that could easily be noise.
- **Pre-FOMC drift is much weaker than the published result.** 15.8 bps per announcement day against roughly 49 bps in Lucca and Moench's sample, on 120 observations with a 10.5 bps standard error. Consistent with post-publication decay; not distinguishable from zero here.
- **Nothing survives costs.** At 10 bps every calendar strategy loses to buy-and-hold, and the union of all windows earns 0.11 Sharpe versus 0.64. The problem is arithmetic: a four-day window every month pays two round trips a month while holding only 19% of the time, so turnover is 24 units a year against a 3.3% gross return.
- **A conditional mean is not an edge.** The in-window Sharpe ratios look impressive (1.03, 1.83, 2.18) precisely because they are conditional on being in the window; the equity curve you can actually own includes the cash drag.

## 🧩 Implementation

New module [`src/calendar_effects.py`](src/calendar_effects.py):

- `turn_of_month_mask(index, days_before=1, days_after=3)` — last trading day plus the first three of the next month.
- `nyse_holidays(start_year, end_year)` and `pre_holiday_mask(index)` — the closure calendar is **computed**, including Easter (anonymous Gregorian algorithm), the weekend observance rules, Juneteenth from 2022, and the exclusion of Columbus Day and Veterans Day.
- `pre_fomc_mask(index, dates=None, include_unscheduled=False)` and `scheduled_fomc_dates()` — 120 scheduled FOMC statements from 2011 to 2025, extracted from the Federal Reserve's own calendar and historical pages and then frozen in the module, so the notebook never scrapes a live page.
- `day_of_week_mask(index, weekday)`.
- `positions_from_return_mask(mask)` — shifts a return mask one bar earlier, with the reasoning documented: `run_backtest` already delays execution by one bar, and a calendar date is known in advance.

## 📓 Notebook

- [53 — Calendar effects](notebooks/53_calendar_effects.ipynb)

## ✅ Validation standards

- 7 new tests in `tests/test_calendar_effects.py`. The 2024 NYSE holiday list is asserted against the exchange's published dates; the turn-of-month window size is asserted; the pre-holiday mask must exclude Columbus and Veterans Day; every scheduled FOMC date must be a trading day; weekday masks must partition the calendar.
- The most important test is synthetic: with returns of exactly 1% on masked days and zero elsewhere, the strategy must earn `1.01^(masked days) - 1`. The classic off-by-one in event studies fails this test.
- t-statistics and sample sizes are reported alongside Sharpe ratios, and the FOMC test prints its standard error.
- Cost sensitivity at 0 / 2 / 10 bps, three subperiod blocks, and a per-year decay chart.
- Negative results kept: no effect is significant and no calendar strategy beats buy-and-hold after 10 bps.

## ⚠️ Limitations

- One asset (SPY). The effects are documented across indices and countries; that replication is not done here.
- The FOMC date list covers 2011–2025, not the paper's original 1994 sample.
- Daily close-to-close returns only; the 24-hour window around the 2pm announcement is measured from the previous close.
- Emergency statements are excluded by default (including them moves the mean from 15.8 to 11.7 bps).
- Nine effects tested on one sample: some apparent significance would be expected by chance. None was found.
