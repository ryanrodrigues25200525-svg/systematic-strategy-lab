"""Tests for the Ken French Data Library loader.

The parser is tested against a local fixture so the suite never needs the
network, and so the exact file format being defended against is visible in the
test file.
"""

import numpy as np
import pandas as pd
import pytest

from src.french_data import (
    DATASETS,
    parse_french_csv,
    load_french_portfolios,
    load_french_factors,
    spread_returns,
)

FIXTURE = """This file was created using the 202512 CRSP database.
It contains value- and equal-weighted returns for  3 prior-return portfolios.
The portfolios are constructed monthly. PRIOR_RET is from -12 to - 2.

Missing data are indicated by -99.99 or -999.


  Value Weight Returns -- Monthly
,Lo PRIOR,PRIOR 2,Hi PRIOR
192701,  -3.32,  -4.54,   2.67
192702,   7.39,   6.01,   7.03
192703, -99.99,  -3.05,  -3.84
192704,   1.28,  -3.01, -999.00

  Average Equal Weighted Returns -- Monthly
,Lo PRIOR,PRIOR 2,Hi PRIOR
192701,  -4.00,  -5.00,   3.00
192702,   8.00,   7.00,   8.00
192703,   1.00,   2.00,   3.00
192704,   2.00,   3.00,   4.00

  Average Value Weighted Returns -- Annual
,Lo PRIOR,PRIOR 2,Hi PRIOR
1927,  -3.32,  -4.54,   2.67
1928,   1.00,   2.00,   3.00

  Average Firm Size
,Lo PRIOR,PRIOR 2,Hi PRIOR
192701,   1.00,   2.00,   3.00
"""


def test_parse_extracts_vintage_and_each_section():
    parsed = parse_french_csv(FIXTURE)
    assert parsed.vintage == "202512"
    assert set(parsed.value_weighted.columns) == {"Lo PRIOR", "PRIOR 2", "Hi PRIOR"}
    assert len(parsed.value_weighted) == 4
    assert len(parsed.equal_weighted) == 4
    assert len(parsed.annual) == 2


def test_parse_converts_percent_to_decimal_and_missing_codes_to_nan():
    parsed = parse_french_csv(FIXTURE)
    monthly = parsed.value_weighted
    assert np.isclose(monthly.loc["1927-01-01", "Lo PRIOR"], -0.0332)
    assert np.isnan(monthly.loc["1927-03-01", "Lo PRIOR"])
    assert np.isnan(monthly.loc["1927-04-01", "Hi PRIOR"])
    assert monthly.index[0] == pd.Timestamp("1927-01-01")
    assert monthly.index[-1] == pd.Timestamp("1927-04-01")
    assert parsed.annual.index[0] == pd.Timestamp("1927-12-31")


def test_parse_handles_unavailable_optional_sections():
    minimal = """Created with the 202401 CRSP database.

  Value Weight Returns -- Monthly
,A,B
196301,   1.00,   2.00
196302,   3.00,   4.00
"""
    parsed = parse_french_csv(minimal)
    assert parsed.vintage == "202401"
    assert len(parsed.value_weighted) == 2
    assert parsed.equal_weighted is None
    assert parsed.annual is None


def test_parse_rejects_a_file_without_a_recognised_section():
    with pytest.raises(ValueError, match="no monthly return section"):
        parse_french_csv("nothing useful here\n123\n")


def test_spread_returns_builds_a_long_short_series():
    parsed = parse_french_csv(FIXTURE)
    spread = spread_returns(parsed.value_weighted, long="Hi PRIOR", short="Lo PRIOR")
    # 1927-02: 7.03 - 7.39 in percent, expressed as a decimal.
    assert np.isclose(spread.loc["1927-02-01"], (7.03 - 7.39) / 100.0)
    # 1927-03 has a missing leg, so the spread must be missing rather than zero.
    assert np.isnan(spread.loc["1927-03-01"])
    with pytest.raises(ValueError):
        spread_returns(parsed.value_weighted, long="Hi PRIOR", short="NOPE")


def test_loader_validates_dataset_names_and_weightings():
    assert "momentum_12_2" in DATASETS
    with pytest.raises(ValueError, match="Unknown dataset"):
        load_french_portfolios("not_a_dataset")
    with pytest.raises(ValueError, match="weighting"):
        load_french_portfolios("momentum_12_2", weighting="magic")


def test_loader_reads_from_a_local_cache_and_records_a_checksum(tmp_path):
    cache = tmp_path / "momentum_12_2_value.csv"
    pd.DataFrame(
        {"Lo PRIOR": [-0.0332, 0.0739], "Hi PRIOR": [0.0267, 0.0703]},
        index=pd.DatetimeIndex(["1927-01-01", "1927-02-01"], name="month"),
    ).to_csv(cache)

    parsed = load_french_portfolios("momentum_12_2", cache_dir=tmp_path)
    assert list(parsed.value_weighted.columns) == ["Lo PRIOR", "Hi PRIOR"]
    assert parsed.vintage == "local-cache"
    assert len(parsed.checksum) == 64  # sha256 hex digest


def test_factor_loader_parses_a_cached_factor_file(tmp_path):
    payload = pd.DataFrame(
        # Cached factor files are stored in decimals, unlike the vendor percent format.
        {"Mkt-RF": [0.010, -0.020], "SMB": [0.005, 0.001], "HML": [-0.002, 0.003], "RMW": [0.001, 0.002], "CMA": [0.000, 0.004], "RF": [0.0025, 0.0025], "Mom": [0.015, -0.005]},
        index=pd.DatetimeIndex(["1963-01-01", "1963-02-01"], name="month"),
    )
    payload.to_csv(tmp_path / "factors_monthly.csv")

    factors = load_french_factors(cache_dir=tmp_path)
    assert list(factors.columns) == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF", "Mom"]
    assert np.isclose(factors.loc["1963-02-01", "Mkt-RF"], -0.02)


def test_parse_tolerates_the_vendor_aerage_typo():
    text = """Created with the 202401 CRSP database.

  Aerage Value Weighted Returns -- Monthly
,A,B
196301,   1.00,   2.00
196302,   3.00,   4.00
"""
    parsed = parse_french_csv(text)
    assert list(parsed.value_weighted.columns) == ["A", "B"]
    assert np.isclose(parsed.value_weighted.loc["1963-02-01", "B"], 0.04)


def test_parse_handles_a_headerless_factor_file():
    text = """This file was created using the 202512 CRSP database.

,Mkt-RF,SMB,HML,RMW,CMA,RF
196307,   -0.39,   -0.48,   -0.84,    0.64,   -1.15,    0.27
196308,    5.08,   -0.80,    1.72,    0.40,   -0.38,    0.25

The annual returns are compounded from the monthly rates.
"""
    parsed = parse_french_csv(text)
    assert parsed.vintage == "202512"
    assert list(parsed.value_weighted.columns) == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    assert len(parsed.value_weighted) == 2
    assert np.isclose(parsed.value_weighted.loc["1963-08-01", "Mkt-RF"], 0.0508)


def test_parse_keeps_only_the_first_block_of_each_kind():
    text = """Created with the 202401 CRSP database.

,Lo,Hi
196301,   1.00,   2.00
196302,   3.00,   4.00

  Value-Weighted Average of Prior Returns
,Lo,Hi
196301,   99.00,  99.00
"""
    parsed = parse_french_csv(text)
    # The diagnostic block must not be mistaken for a second return block.
    assert np.isclose(parsed.value_weighted.loc["1963-01-01", "Lo"], 0.01)
    assert len(parsed.value_weighted) == 2
