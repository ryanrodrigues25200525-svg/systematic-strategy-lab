"""Ken French Data Library loader with local snapshots and checksums.

The research in notebooks 56 and 57 needs portfolio-level data that measures the
same thing the papers measured: decile portfolios sorted on prior return,
size-by-book-to-market and size-by-profitability grids, and 49 industry
portfolios, from 1926/1927 to the present. ETF proxies cannot provide that, and
they cannot provide a century of it.

Two rules make the numbers reproducible:

1. Every download is cached to ``data/french/`` as a CSV and recorded in a
   manifest with its URL, retrieval timestamp, CRSP vintage and SHA-256 digest.
   The notebooks read the snapshot by default, so a vendor revision cannot
   silently change a published finding.
2. The parser records the CRSP vintage embedded in the file header, so every
   table in a notebook can say which database it came from.

File format notes. Each Ken French CSV is a prose header, then repeated blocks
of ``<weighting> Returns -- <frequency>`` with a comma-led column header and
``YYYYMM`` or ``YYYY`` rows, then non-return blocks such as ``Average Firm
Size``. Missing values are written as ``-99.99`` or ``-999``. Returns are in
percent.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final
from urllib.request import urlopen

import numpy as np
import pandas as pd

BASE_URL: Final[str] = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"
DEFAULT_CACHE: Final[Path] = Path(__file__).resolve().parents[1] / "data" / "french"
MISSING_VALUES: Final[tuple[float, ...]] = (-99.99, -999.0, -9999.0)

DATASETS: Final[dict[str, str]] = {
    "momentum_12_2": "10_Portfolios_Prior_12_2",
    "reversal_1_0": "10_Portfolios_Prior_1_0",
    "reversal_60_13": "10_Portfolios_Prior_60_13",
    "size_value_5x5": "25_Portfolios_5x5",
    "size_profitability_5x5": "25_Portfolios_ME_OP_5x5",
    "size_investment_5x5": "25_Portfolios_ME_Inv_5x5",
    "industries_49": "49_Industry_Portfolios",
}

# Deliberately tolerant: the vendor files contain "Aerage" (sic), "Value Weight
# Returns" without the -ed, and the factor files carry no section header at all.
SECTION_PATTERN = re.compile(r"Weight\w*\s+Returns?\s*--\s*(?P<frequency>Monthly|Annual)", re.IGNORECASE)
MONTHLY_ROW = re.compile(r"^\s*(\d{6})\s*,")
ANNUAL_ROW = re.compile(r"^\s*(\d{4})\s*,")
VINTAGE_PATTERN = re.compile(r"(\d{6})\s+CRSP", re.IGNORECASE)


@dataclass(frozen=True)
class FrenchPortfolios:
    """Parsed contents of one Ken French portfolio file."""

    dataset: str
    vintage: str
    checksum: str
    source: str
    value_weighted: pd.DataFrame
    equal_weighted: pd.DataFrame | None = None
    annual: pd.DataFrame | None = None


def _clean(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.replace(list(MISSING_VALUES), np.nan) / 100.0


def parse_french_csv(text: str, *, dataset: str = "inline", source: str = "inline") -> FrenchPortfolios:
    """Parse the text of a Ken French portfolio file.

    Blocks are located by their header line rather than by line number, and a
    comma-led column header that appears without any section header starts an
    implicit value-weighted monthly block. That last rule exists because the
    factor files are exactly that shape. Only the *first* block of each kind is
    used, so a trailing "Value-Weighted Average of Prior Returns" block cannot
    overwrite the returns.
    """

    lines = text.splitlines()
    vintage_match = VINTAGE_PATTERN.search(text[:2000])
    vintage = vintage_match.group(1) if vintage_match else "unknown"

    blocks: list[dict] = []
    current: dict | None = None

    for line in lines:
        header = SECTION_PATTERN.search(line)
        if header:
            frequency = header.group("frequency").lower()
            weighting = "equal" if "equal" in line.lower() else "value"
            current = {"weighting": weighting, "frequency": frequency, "columns": None, "rows": []}
            blocks.append(current)
            continue

        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith(","):
            # A column header with no section header before it is an implicit
            # value-weighted monthly block; a second one starts a new block.
            if current is None or current["rows"]:
                current = {"weighting": "value", "frequency": "monthly", "columns": None, "rows": []}
                blocks.append(current)
            current["columns"] = [part.strip() for part in stripped[1:].split(",")]
            continue

        if current is None or current["columns"] is None:
            continue

        pattern = MONTHLY_ROW if current["frequency"] == "monthly" else ANNUAL_ROW
        if not pattern.match(line):
            current = None
            continue
        current["rows"].append([part.strip() for part in stripped.split(",")])

    def build(weighting: str, frequency: str) -> pd.DataFrame | None:
        for block in blocks:
            if block["weighting"] != weighting or block["frequency"] != frequency:
                continue
            if not block["rows"] or not block["columns"]:
                continue
            names = block["columns"]
            width = len(names)
            rows = [row[: width + 1] for row in block["rows"] if len(row) >= width + 1]
            frame = pd.DataFrame(rows, columns=["period", *names])
            if frequency == "monthly":
                index = pd.to_datetime(frame["period"], format="%Y%m") + pd.offsets.MonthBegin(0)
                index.name = "month"
            else:
                index = pd.to_datetime(frame["period"], format="%Y") + pd.offsets.YearEnd(0)
                index.name = "year"
            data = frame.drop(columns="period").apply(_clean, axis=0)
            data.index = index
            data = data[~data.index.isna()].sort_index()
            return data.astype(float)
        return None

    value_monthly = build("value", "monthly")
    if value_monthly is None or value_monthly.empty:
        raise ValueError("File contains no monthly return section")

    return FrenchPortfolios(
        dataset=dataset,
        vintage=vintage,
        checksum=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        source=source,
        value_weighted=value_monthly,
        equal_weighted=build("equal", "monthly"),
        annual=build("value", "annual"),
    )


def _manifest_path(cache_dir: Path) -> Path:
    return cache_dir / "manifest.json"


def _read_manifest(cache_dir: Path) -> dict:
    path = _manifest_path(cache_dir)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _write_manifest(cache_dir: Path, manifest: dict) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    _manifest_path(cache_dir).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def _download(dataset: str) -> str:
    url = f"{BASE_URL}/{DATASETS[dataset]}_CSV.zip"
    with urlopen(url, timeout=60) as response:  # noqa: S310 - fixed host, https
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        name = archive.namelist()[0]
        return archive.read(name).decode("latin1")


def load_french_portfolios(
    dataset: str,
    *,
    weighting: str = "value",
    cache_dir: Path | None = None,
    refresh: bool = False,
) -> FrenchPortfolios:
    """Load one portfolio dataset, preferring the local snapshot.

    ``refresh=True`` re-downloads and rewrites the snapshot. Otherwise a cached
    CSV is authoritative: that is the whole point of the snapshot, and it is why
    a findings table can still be reproduced after the vendor revises history.
    """

    if dataset not in DATASETS:
        raise ValueError(f"Unknown dataset {dataset!r}; expected one of {sorted(DATASETS)}")
    if weighting not in {"value", "equal"}:
        raise ValueError("weighting must be 'value' or 'equal'")

    cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE
    cache_file = cache_dir / f"{dataset}_{weighting}.csv"
    manifest = _read_manifest(cache_dir)

    if cache_file.exists() and not refresh:
        frame = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        frame.index.name = "month"
        entry = manifest.get(f"{dataset}_{weighting}", {})
        return FrenchPortfolios(
            dataset=dataset,
            vintage="local-cache",
            checksum=hashlib.sha256(cache_file.read_bytes()).hexdigest(),
            source=entry.get("url", str(cache_file)),
            value_weighted=frame.astype(float),
        )

    text = _download(dataset)
    parsed = parse_french_csv(text, dataset=dataset, source=f"{BASE_URL}/{DATASETS[dataset]}_CSV.zip")
    frame = parsed.value_weighted if weighting == "value" else parsed.equal_weighted
    if frame is None or frame.empty:
        raise ValueError(f"Dataset {dataset!r} has no {weighting}-weighted monthly returns")

    cache_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_file)
    manifest[f"{dataset}_{weighting}"] = {
        "url": parsed.source,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "crsp_vintage": parsed.vintage,
        "sha256": hashlib.sha256(cache_file.read_bytes()).hexdigest(),
        "rows": int(len(frame)),
        "columns": int(frame.shape[1]),
        "first_month": str(frame.index.min().date()),
        "last_month": str(frame.index.max().date()),
    }
    _write_manifest(cache_dir, manifest)
    return parsed


def load_french_factors(*, cache_dir: Path | None = None, refresh: bool = False) -> pd.DataFrame:
    """Load the combined five-factor plus momentum monthly series, in decimals.

    Uses ``F-F_Research_Data_5_Factors_2x3`` for Mkt-RF, SMB, HML, RMW, CMA and
    RF, and ``F-F_Momentum_Factor`` for Mom, joined on month. Both files are part
    of the same library and share the CRSP vintage.
    """

    cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE
    cache_file = cache_dir / "factors_monthly.csv"
    if cache_file.exists() and not refresh:
        frame = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        frame.index.name = "month"
        return frame.astype(float)

    five = parse_french_csv(_download_text("F-F_Research_Data_5_Factors_2x3"))
    momentum = parse_french_csv(_download_text("F-F_Momentum_Factor"))

    five_frame = five.value_weighted
    momentum_frame = momentum.value_weighted
    momentum_frame.columns = ["Mom"] + [column for column in momentum_frame.columns[1:]]
    momentum_frame = momentum_frame[["Mom"]]

    combined = five_frame.join(momentum_frame, how="inner")
    cache_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(cache_file)

    manifest = _read_manifest(cache_dir)
    manifest["factors_monthly"] = {
        "url": f"{BASE_URL}/F-F_Research_Data_5_Factors_2x3_CSV.zip + F-F_Momentum_Factor_CSV.zip",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "crsp_vintage": five.vintage,
        "sha256": hashlib.sha256(cache_file.read_bytes()).hexdigest(),
        "rows": int(len(combined)),
        "columns": int(combined.shape[1]),
        "first_month": str(combined.index.min().date()),
        "last_month": str(combined.index.max().date()),
    }
    _write_manifest(cache_dir, manifest)
    return combined.astype(float)


def _download_text(stem: str) -> str:
    url = f"{BASE_URL}/{stem}_CSV.zip"
    with urlopen(url, timeout=60) as response:  # noqa: S310 - fixed host, https
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        return archive.read(archive.namelist()[0]).decode("latin1")


def spread_returns(returns: pd.DataFrame, *, long: str, short: str) -> pd.Series:
    """Long-minus-short return of two columns, in decimals.

    A missing leg produces a missing spread rather than a zero, so an early
    sample cannot be mistaken for a flat portfolio.
    """

    for column in (long, short):
        if column not in returns.columns:
            raise ValueError(f"column {column!r} not in the portfolio frame")
    spread = returns[long] - returns[short]
    return spread.rename(f"{long} minus {short}")
