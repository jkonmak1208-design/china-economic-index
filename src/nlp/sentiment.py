"""Sentiment scoring using SnowNLP (local, no API required)."""

import logging

logger = logging.getLogger(__name__)


def score_sentiment(text):
    """Score sentiment of Chinese text using SnowNLP.

    SnowNLP returns a value in [0, 1] where:
    - 0 = very negative
    - 0.5 = neutral
    - 1 = very positive

    Args:
        text: Chinese text string (cleaned or raw)

    Returns:
        float in [0, 1], or 0.5 (neutral) on failure
    """
    if not text or not text.strip():
        return 0.5

    try:
        from snownlp import SnowNLP
        s = SnowNLP(text)
        return s.sentiments
    except ImportError:
        logger.error("snownlp not installed. Run: pip install snownlp")
        return 0.5
    except Exception as e:
        logger.warning(f"Sentiment scoring failed: {e}")
        return 0.5


def score_articles(articles):
    """Score sentiment for a list of articles.

    Args:
        articles: list of dicts with 'title' and optionally 'content' keys

    Returns:
        list of (article_id, score) tuples where article_id is the 'id' field
    """
    results = []
    for article in articles:
        text = f"{article.get('title', '')} {article.get('content', '')}".strip()
        score = score_sentiment(text)
        results.append((article["id"], score))

    if results:
        scores = [s for _, s in results]
        logger.info(
            f"Scored {len(results)} articles: mean={sum(scores)/len(scores):.3f}, "
            f"min={min(scores):.3f}, max={max(scores):.3f}"
        )

    return results
