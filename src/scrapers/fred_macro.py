"""Fetch macroeconomic indicators from FRED API."""

import logging
from datetime import datetime, timedelta

import pandas as pd
import requests

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_fred_series(series_id, api_key, start_date="2020-01-01", end_date=None):
    """Fetch a single FRED series.

    Args:
        series_id: FRED series identifier (e.g., "DEXCHUS")
        api_key: FRED API key
        start_date: start date string (YYYY-MM-DD)
        end_date: end date string, defaults to today

    Returns:
        pd.Series with datetime index and float values
    """
    if not api_key:
        logger.warning(f"No FRED API key provided, skipping {series_id}")
        return pd.Series(dtype=float)

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
        "observation_end": end_date,
    }

    try:
        resp = requests.get(FRED_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        observations = data.get("observations", [])
        dates = []
        values = []
        for obs in observations:
            if obs["value"] == ".":
                continue
            dates.append(pd.Timestamp(obs["date"]))
            values.append(float(obs["value"]))

        series = pd.Series(values, index=dates, name=series_id)
        logger.info(f"FRED {series_id}: fetched {len(series)} observations")
        return series

    except Exception as e:
        logger.warning(f"Failed to fetch FRED series {series_id}: {e}")
        return pd.Series(dtype=float)


def get_monthly_average(series, month):
    """Compute the monthly average of a daily series for a given month.

    Args:
        series: pd.Series with datetime index
        month: YYYY-MM string

    Returns:
        float or None if no data available
    """
    if series.empty:
        return None

    mask = series.index.strftime("%Y-%m") == month
    monthly = series[mask]

    if monthly.empty:
        return None

    return float(monthly.mean())


def get_monthly_change(series, month):
    """Compute month-over-month change for a given month.

    Args:
        series: pd.Series with datetime index
        month: YYYY-MM string

    Returns:
        float (change) or None
    """
    if series.empty:
        return None

    # Get current and previous month averages
    current = get_monthly_average(series, month)
    if current is None:
        return None

    # Compute previous month string
    year, mon = int(month[:4]), int(month[5:7])
    if mon == 1:
        prev_month = f"{year - 1}-12"
    else:
        prev_month = f"{year}-{mon - 1:02d}"

    previous = get_monthly_average(series, prev_month)
    if previous is None or previous == 0:
        return None

    return (current - previous) / abs(previous) * 100


def fetch_all_macro(api_key, month, series_config):
    """Fetch all macro indicators for a given month.

    Args:
        api_key: FRED API key
        month: YYYY-MM string
        series_config: dict mapping indicator names to FRED series IDs

    Returns:
        dict with indicator values for the month
    """
    # Fetch with enough history for monthly change calculation
    start_date = "2020-01-01"

    results = {}
    for name, series_id in series_config.items():
        series = fetch_fred_series(series_id, api_key, start_date)

        if name == "usd_cny":
            results["usd_cny_change"] = get_monthly_change(series, month)
        elif name == "vix":
            results["vix_avg"] = get_monthly_average(series, month)
        elif name == "china_cpi":
            # CPI is already a level; compute YoY change
            current = get_monthly_average(series, month)
            year, mon = int(month[:4]), int(month[5:7])
            prev_year_month = f"{year - 1}-{mon:02d}"
            prev_year = get_monthly_average(series, prev_year_month)
            if current is not None and prev_year is not None and prev_year != 0:
                results["china_cpi_yoy"] = (current - prev_year) / abs(prev_year) * 100
            else:
                results["china_cpi_yoy"] = None
        elif name == "yield_curve":
            results["yield_curve"] = get_monthly_average(series, month)

    logger.info(f"FRED macro for {month}: {results}")
    return results
