"""Scraper for East Money (东方财富) news via HTML scraping."""

import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# East Money news listing pages
URLS = [
    "https://finance.eastmoney.com/a/cssgs.html",   # Macro/general finance
    "https://finance.eastmoney.com/a/cgsxw.html",   # Stock news
    "https://finance.eastmoney.com/a/ccjxw.html",   # Finance news
]


def scrape_eastmoney(month, max_articles=100):
    """Scrape East Money news headlines via HTML.

    Args:
        month: YYYY-MM string for tagging articles
        max_articles: maximum number of articles to return

    Returns:
        List of dicts with keys: source, title, content, url, published_date, month
    """
    articles = []
    seen_urls = set()

    for url in URLS:
        if len(articles) >= max_articles:
            break

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                title = link.get_text(strip=True)

                if not title or len(title) < 8:
                    continue
                if "eastmoney.com" not in href:
                    continue
                if href in seen_urls:
                    continue
                if not href.startswith("http"):
                    continue

                seen_urls.add(href)
                articles.append(
                    {
                        "source": "eastmoney",
                        "title": title,
                        "content": "",
                        "url": href,
                        "published_date": datetime.utcnow().strftime("%Y-%m-%d"),
                        "month": month,
                    }
                )

                if len(articles) >= max_articles:
                    break

        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")

    logger.info(f"East Money: scraped {len(articles)} articles")
    return articles
