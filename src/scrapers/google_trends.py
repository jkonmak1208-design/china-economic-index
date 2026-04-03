"""Fetch Google Trends data for China-related economic queries."""

import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def fetch_google_trends(queries, month):
    """Fetch Google Trends interest for given queries and extract monthly value.

    Args:
        queries: list of search query strings
        month: YYYY-MM string

    Returns:
        float: average Google Trends interest for the month (0-100 scale), or None
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        logger.warning("pytrends not installed, skipping Google Trends")
        return None

    try:
        pytrends = TrendReq(hl="en-US", tz=480)  # tz=480 for China (UTC+8)

        # Request monthly data over 5 years
        pytrends.build_payload(queries, cat=0, timeframe="today 5-y", geo="")

        df = pytrends.interest_over_time()

        if df.empty:
            logger.warning("Google Trends returned empty data")
            return None

        # Drop the 'isPartial' column if present
        if "isPartial" in df.columns:
            df = df.drop(columns=["isPartial"])

        # Average across all queries for each time point
        df["mean_interest"] = df.mean(axis=1)

        # Filter to the target month
        monthly = df[df.index.strftime("%Y-%m") == month]["mean_interest"]

        if monthly.empty:
            # Try the closest available month
            logger.warning(f"No Google Trends data for {month}, using latest available")
            return float(df["mean_interest"].iloc[-1])

        return float(monthly.mean())

    except Exception as e:
        logger.warning(f"Failed to fetch Google Trends: {e}")
        return None
