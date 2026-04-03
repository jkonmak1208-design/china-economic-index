#!/usr/bin/env python3
"""Backfill historical months for the economic sentiment index.

Since news scrapers only capture current articles, backfill primarily
uses FRED macro data and Google Trends (which have historical data).
Sentiment and keyword sub-indicators will be None for months without articles.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import run_full_update


def generate_months(start, end):
    """Generate list of YYYY-MM strings from start to end (inclusive)."""
    months = []
    year, mon = int(start[:4]), int(start[5:7])
    end_year, end_mon = int(end[:4]), int(end[5:7])

    while (year, mon) <= (end_year, end_mon):
        months.append(f"{year}-{mon:02d}")
        if mon == 12:
            year += 1
            mon = 1
        else:
            mon += 1

    return months


def main():
    parser = argparse.ArgumentParser(description="Backfill historical index data")
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="Start month (YYYY-MM)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End month (YYYY-MM). Defaults to previous month.",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        default=True,
        help="Skip scraping for historical months (default: True)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.end is None:
        now = datetime.now()
        if now.month == 1:
            args.end = f"{now.year - 1}-12"
        else:
            args.end = f"{now.year}-{now.month - 1:02d}"

    months = generate_months(args.start, args.end)
    print(f"Backfilling {len(months)} months: {months[0]} to {months[-1]}")

    for i, month in enumerate(months):
        print(f"\n[{i + 1}/{len(months)}] Processing {month}...")
        try:
            result = run_full_update(month, skip_scrape=args.skip_scrape)
            composite = result.get("composite_index")
            if composite is not None:
                print(f"  Composite index: {composite:.2f}")
            else:
                print(f"  Composite index: N/A (insufficient data)")
        except Exception as e:
            print(f"  ERROR: {e}")
            logging.exception(f"Failed to process {month}")

    print(f"\nBackfill complete. Processed {len(months)} months.")


if __name__ == "__main__":
    main()
