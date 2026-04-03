#!/usr/bin/env python3
"""CLI wrapper to run the monthly index update pipeline."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import run_full_update


def main():
    parser = argparse.ArgumentParser(description="Run monthly economic sentiment index update")
    parser.add_argument(
        "--month",
        type=str,
        default=None,
        help="Month to process (YYYY-MM format). Defaults to previous month.",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip scraping, use existing articles in database",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                Path(__file__).parent.parent / "data" / "pipeline.log",
                encoding="utf-8",
            ),
        ],
    )

    # Default to previous month
    if args.month is None:
        now = datetime.now()
        if now.month == 1:
            month = f"{now.year - 1}-12"
        else:
            month = f"{now.year}-{now.month - 1:02d}"
    else:
        month = args.month

    # Validate month format
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        print(f"Error: Invalid month format '{month}'. Use YYYY-MM.")
        sys.exit(1)

    print(f"Running pipeline for month: {month}")
    result = run_full_update(month, skip_scrape=args.skip_scrape)

    print("\n--- Results ---")
    for key, value in result.items():
        if value is not None:
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")
        else:
            print(f"  {key}: N/A")


if __name__ == "__main__":
    main()
