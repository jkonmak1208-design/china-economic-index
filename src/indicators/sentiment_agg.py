"""Monthly sentiment aggregation from article-level scores."""

import logging
from src.database import get_monthly_sentiments, get_monthly_index

logger = logging.getLogger(__name__)


def compute_monthly_sentiment(month, db_path=None):
    """Compute the raw monthly sentiment score.

    Args:
        month: YYYY-MM string

    Returns:
        float in [0, 1] or None if no articles scored
    """
    scores = get_monthly_sentiments(month, db_path)
    if not scores:
        logger.warning(f"No sentiment scores for {month}")
        return None
    return sum(scores) / len(scores)


def normalize_to_100(value, history, window=24):
    """Normalize a value to [0, 100] using rolling min-max over history.

    Args:
        value: current month's raw value
        history: list of historical raw values (most recent last)
        window: number of months for rolling window

    Returns:
        float in [0, 100], or 50 if insufficient history
    """
    if value is None:
        return None

    # Use the last `window` values plus current value
    recent = [v for v in history[-window:] if v is not None]
    recent.append(value)

    if len(recent) < 2:
        # Not enough history; map linearly assuming [0, 1] input range
        return value * 100

    min_val = min(recent)
    max_val = max(recent)

    if max_val == min_val:
        return 50.0

    return (value - min_val) / (max_val - min_val) * 100
