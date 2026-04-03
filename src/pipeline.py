"""Pipeline orchestrator: scrape → process → score → compute → store for a given month."""

import logging
from pathlib import Path

import yaml

from src.database import (
    init_db,
    insert_articles,
    get_unscored_articles,
    insert_sentiment,
    upsert_monthly_index,
    get_monthly_index,
)
from src.scrapers.sina_finance import scrape_sina
from src.scrapers.eastmoney import scrape_eastmoney
from src.scrapers.fred_macro import fetch_all_macro
from src.scrapers.google_trends import fetch_google_trends
from src.nlp.sentiment import score_articles
from src.indicators.sentiment_agg import compute_monthly_sentiment, normalize_to_100
from src.indicators.keyword_freq import compute_keyword_frequencies
from src.indicators.composite import compute_composite_index

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


def load_config():
    """Load settings from YAML config file."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_full_update(month, skip_scrape=False):
    """Run the full pipeline for a given month.

    Args:
        month: YYYY-MM string (e.g., "2025-03")
        skip_scrape: if True, skip scraping and use existing articles in DB

    Returns:
        dict with the computed monthly index values
    """
    config = load_config()
    init_db()

    logger.info(f"=== Starting pipeline for {month} ===")

    # Step 1: Scrape articles
    if not skip_scrape:
        logger.info("Step 1: Scraping news articles...")
        sina_articles = scrape_sina(
            month, max_articles=config["scraping"]["sina"]["max_articles"]
        )
        em_articles = scrape_eastmoney(
            month, max_articles=config["scraping"]["eastmoney"]["max_articles"]
        )

        all_articles = sina_articles + em_articles
        inserted = insert_articles(all_articles)
        logger.info(f"Inserted {inserted} new articles (of {len(all_articles)} scraped)")
    else:
        logger.info("Step 1: Skipping scrape (using existing articles)")

    # Step 2: Score sentiment on unscored articles
    logger.info("Step 2: Scoring sentiment...")
    unscored = get_unscored_articles(month)
    if unscored:
        scores = score_articles(unscored)
        for article_id, score in scores:
            insert_sentiment(article_id, score)
        logger.info(f"Scored {len(scores)} articles")
    else:
        logger.info("No unscored articles")

    # Step 3: Compute sub-indicators
    logger.info("Step 3: Computing sub-indicators...")

    # 3a: Monthly sentiment
    sentiment_raw = compute_monthly_sentiment(month)

    # 3b: Keyword frequencies
    kw = compute_keyword_frequencies(month)
    keyword_net = kw["keyword_net"] if kw else None
    keyword_uncertainty = kw["uncertainty_freq"] if kw else None

    # 3c: FRED macro indicators
    fred_api_key = config["fred"]["api_key"]
    macro = fetch_all_macro(fred_api_key, month, config["fred"]["series"])

    # 3d: Google Trends
    gt_value = fetch_google_trends(config["google_trends"]["queries"], month)

    # Step 4: Store sub-indicators
    logger.info("Step 4: Storing sub-indicators...")
    index_data = {
        "sentiment_raw": sentiment_raw,
        "keyword_net": keyword_net,
        "keyword_uncertainty": keyword_uncertainty,
        "usd_cny_change": macro.get("usd_cny_change"),
        "vix_avg": macro.get("vix_avg"),
        "china_cpi_yoy": macro.get("china_cpi_yoy"),
        "google_trends": gt_value,
    }

    upsert_monthly_index(month, index_data)
    logger.info(f"Sub-indicators stored: {index_data}")

    # Step 5: Compute composite index
    logger.info("Step 5: Computing composite index...")
    pca_config = config["index"]
    composite = compute_composite_index(
        month,
        min_months=pca_config["pca_min_months"],
        pca_window=pca_config["pca_window"],
    )

    # Update with composite values
    upsert_monthly_index(month, composite)

    # Merge for return
    index_data.update(composite)
    logger.info(f"=== Pipeline complete for {month} ===")
    logger.info(f"Composite index: {composite.get('composite_index')}")

    return index_data
