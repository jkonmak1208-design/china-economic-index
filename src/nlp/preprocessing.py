"""Chinese text preprocessing for financial news articles."""

import re
import logging

logger = logging.getLogger(__name__)

# Common Chinese stopwords (finance-context subset)
STOPWORDS = set(
    "的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 "
    "自己 这 他 她 它 们 那 个 里 吗 吧 呢 啊 哦 嗯 把 被 让 给 从 对 为 以 与 及 等 "
    "但 而 或 如果 因为 所以 虽然 但是 然后 于是 已经 可以 可能 应该 需要 "
    "这个 那个 什么 怎么 为什么 哪 哪里 这些 那些 每 各 某 其 "
    "年 月 日 时 分 秒 元 万 亿 号 第".split()
)


def clean_html(text):
    """Remove HTML tags and entities."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"&#\d+;", " ", text)
    return text.strip()


def clean_text(text):
    """Clean raw text: remove HTML, URLs, special characters, normalize whitespace."""
    text = clean_html(text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove email addresses
    text = re.sub(r"\S+@\S+", "", text)
    # Keep Chinese characters, letters, numbers, and basic punctuation
    text = re.sub(r"[^\u4e00-\u9fff\u3000-\u303fa-zA-Z0-9\s，。！？、；：""''（）]", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def segment(text):
    """Segment Chinese text into words using jieba.

    Returns:
        list of words (stopwords removed)
    """
    try:
        import jieba
    except ImportError:
        logger.warning("jieba not installed, falling back to character-level tokenization")
        return [c for c in text if c.strip() and c not in STOPWORDS]

    words = jieba.lcut(text)
    return [w.strip() for w in words if w.strip() and w.strip() not in STOPWORDS and len(w.strip()) > 1]


def preprocess_article(title, content=""):
    """Full preprocessing pipeline for a single article.

    Args:
        title: article title string
        content: article body text (may be empty)

    Returns:
        dict with 'clean_text' (str) and 'words' (list of str)
    """
    raw = f"{title} {content}".strip()
    cleaned = clean_text(raw)
    words = segment(cleaned)
    return {"clean_text": cleaned, "words": words}
