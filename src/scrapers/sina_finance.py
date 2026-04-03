"""Scraper for Sina Finance (新浪财经) news headlines."""

import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)

# Sina Finance main news listing pages
URLS = [
    "https://finance.sina.com.cn/china/",
    "https://finance.sina.com.cn/stock/",
    "https://finance.sina.com.cn/money/",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def scrape_sina(month, max_articles=100):
    """Scrape Sina Finance news articles.

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
            soup = BeautifulSoup(resp.text, "lxml")

            # Sina uses <a> tags with finance.sina.com.cn links for article headlines
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                title = link.get_text(strip=True)

                # Filter for article links (typically contain /doc- or /article/)
                if not title or len(title) < 8:
                    continue
                if "finance.sina" not in href and "sina.com.cn" not in href:
                    continue
                if href in seen_urls:
                    continue
                if not href.startswith("http"):
                    continue

                seen_urls.add(href)
                articles.append(
                    {
                        "source": "sina",
                        "title": title,
                        "content": "",  # Headlines only for efficiency
                        "url": href,
                        "published_date": datetime.utcnow().strftime("%Y-%m-%d"),
                        "month": month,
                    }
                )

                if len(articles) >= max_articles:
                    break

        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")

    logger.info(f"Sina Finance: scraped {len(articles)} articles")
    return articles
