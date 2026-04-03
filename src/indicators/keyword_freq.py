"""Keyword frequency index computation."""

import logging
from pathlib import Path

import yaml

from src.nlp.preprocessing import preprocess_article
from src.database import get_articles_for_month

logger = logging.getLogger(__name__)

KEYWORDS_PATH = Path(__file__).parent.parent.parent / "config" / "keywords.yaml"


def load_keywords():
    """Load keyword lists from config."""
    with open(KEYWORDS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def count_keywords_in_text(words, keyword_list):
    """Count occurrences of keywords in a word list.

    Handles multi-character keywords by joining adjacent words and checking.

    Args:
        words: list of segmented words
        keyword_list: list of keyword strings

    Returns:
        int: total count of keyword matches
    """
    text_joined = "".join(words)
    count = 0
    for keyword in keyword_list:
        count += text_joined.count(keyword)
    return count


def compute_keyword_frequencies(month, db_path=None):
    """Compute keyword frequency indices for a given month.

    Args:
        month: YYYY-MM string

    Returns:
        dict with keys: positive_freq, negative_freq, uncertainty_freq,
                        keyword_net, total_words
        or None if no articles
    """
    keywords = load_keywords()
    articles = get_articles_for_month(month, db_path)

    if not articles:
        logger.warning(f"No articles for {month}")
        return None

    total_positive = 0
    total_negative = 0
    total_uncertainty = 0
    total_words = 0

    for article in articles:
        processed = preprocess_article(article["title"], article.get("content", ""))
        words = processed["words"]

        if not words:
            continue

        total_words += len(words)
        total_positive += count_keywords_in_text(words, keywords["positive"])
        total_negative += count_keywords_in_text(words, keywords["negative"])
        total_uncertainty += count_keywords_in_text(words, keywords["uncertainty"])

    if total_words == 0:
        return None

    # Frequencies per 1000 words
    positive_freq = total_positive / total_words * 1000
    negative_freq = total_negative / total_words * 1000
    uncertainty_freq = total_uncertainty / total_words * 1000
    keyword_net = positive_freq - negative_freq

    result = {
        "positive_freq": positive_freq,
        "negative_freq": negative_freq,
        "uncertainty_freq": uncertainty_freq,
        "keyword_net": keyword_net,
        "total_words": total_words,
    }

    logger.info(
        f"Keywords for {month}: pos={positive_freq:.2f}, neg={negative_freq:.2f}, "
        f"unc={uncertainty_freq:.2f}, net={keyword_net:.2f} (per 1000 words, "
        f"{total_words} total words from {len(articles)} articles)"
    )
    return result
