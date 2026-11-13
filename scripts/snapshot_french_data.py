"""Snapshot the Ken French datasets used by notebooks 56 and 57.

Run this to refresh ``data/french/``. The snapshots are committed so that a
vendor revision cannot silently change a published finding; the manifest records
the URL, retrieval time, CRSP vintage and SHA-256 of every file.

    python scripts/snapshot_french_data.py [--refresh]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.french_data import DATASETS, DEFAULT_CACHE, load_french_factors, load_french_portfolios


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-download and rewrite the snapshots")
    parser.add_argument("--weighting", default="value", choices=("value", "equal"))
    args = parser.parse_args()

    DEFAULT_CACHE.mkdir(parents=True, exist_ok=True)
    print(f"Snapshot directory: {DEFAULT_CACHE}")

    rows = []
    for dataset in DATASETS:
        parsed = load_french_portfolios(dataset, weighting=args.weighting, refresh=args.refresh)
        frame = parsed.value_weighted
        rows.append((dataset, parsed.vintage, len(frame), str(frame.index.min().date()), str(frame.index.max().date()), frame.shape[1]))

    factors = load_french_factors(refresh=args.refresh)
    rows.append(("factors_monthly", "n/a", len(factors), str(factors.index.min().date()), str(factors.index.max().date()), factors.shape[1]))

    width = max(len(name) for name, *_ in rows)
    print(f"{'dataset'.ljust(width)}  vintage  months   first       last        cols")
    for name, vintage, months, first, last, columns in rows:
        print(f"{name.ljust(width)}  {vintage:<7}  {months:>6}  {first}  {last}  {columns:>4}")

    manifest = json.loads((DEFAULT_CACHE / "manifest.json").read_text())
    total_bytes = sum(path.stat().st_size for path in DEFAULT_CACHE.glob("*.csv"))
    print(f"\n{len(manifest)} files, {total_bytes / 1024:.0f} KiB, manifest at {DEFAULT_CACHE / 'manifest.json'}")


if __name__ == "__main__":
    main()
