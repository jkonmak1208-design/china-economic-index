"""SQLite database schema and helper functions for the economic sentiment index."""

import json
import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = Path(__file__).parent.parent / "data" / "index.db"


def get_connection(db_path=None):
    """Get a SQLite connection with WAL mode enabled."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Create all tables if they don't exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            url TEXT UNIQUE,
            published_date TEXT,
            month TEXT NOT NULL,
            scraped_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS article_sentiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            score REAL NOT NULL,
            scored_at TEXT NOT NULL,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        );

        CREATE TABLE IF NOT EXISTS monthly_index (
            month TEXT PRIMARY KEY,
            sentiment_raw REAL,
            keyword_net REAL,
            keyword_uncertainty REAL,
            usd_cny_change REAL,
            vix_avg REAL,
            china_cpi_yoy REAL,
            google_trends REAL,
            composite_index REAL,
            pc1_variance_explained REAL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pca_params (
            estimated_month TEXT PRIMARY KEY,
            loadings_json TEXT NOT NULL,
            mean_json TEXT NOT NULL,
            std_json TEXT NOT NULL,
            variance_explained REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_articles_month ON articles(month);
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
        CREATE INDEX IF NOT EXISTS idx_article_sentiment_article_id ON article_sentiment(article_id);
    """)

    conn.commit()
    conn.close()


def insert_articles(articles, db_path=None):
    """Insert articles, skipping duplicates by URL.

    Args:
        articles: list of dicts with keys: source, title, content, url, published_date, month
    Returns:
        Number of articles inserted.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    inserted = 0

    for article in articles:
        try:
            cursor.execute(
                """INSERT INTO articles (source, title, content, url, published_date, month, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    article["source"],
                    article["title"],
                    article.get("content", ""),
                    article.get("url"),
                    article.get("published_date"),
                    article["month"],
                    now,
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # Duplicate URL, skip

    conn.commit()
    conn.close()
    return inserted


def insert_sentiment(article_id, score, db_path=None):
    """Insert a sentiment score for an article."""
    conn = get_connection(db_path)
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO article_sentiment (article_id, score, scored_at) VALUES (?, ?, ?)",
        (article_id, score, now),
    )
    conn.commit()
    conn.close()


def get_articles_for_month(month, db_path=None):
    """Get all articles for a given month (YYYY-MM format)."""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM articles WHERE month = ? ORDER BY published_date", (month,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unscored_articles(month, db_path=None):
    """Get articles for a month that don't have sentiment scores yet."""
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT a.* FROM articles a
           LEFT JOIN article_sentiment s ON a.id = s.article_id
           WHERE a.month = ? AND s.id IS NULL
           ORDER BY a.published_date""",
        (month,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monthly_sentiments(month, db_path=None):
    """Get all sentiment scores for articles in a given month."""
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT s.score FROM article_sentiment s
           JOIN articles a ON s.article_id = a.id
           WHERE a.month = ?""",
        (month,),
    ).fetchall()
    conn.close()
    return [r["score"] for r in rows]


def upsert_monthly_index(month, data, db_path=None):
    """Insert or update a row in monthly_index.

    Args:
        month: YYYY-MM string
        data: dict with column names as keys (excluding month and updated_at)
    """
    conn = get_connection(db_path)
    now = datetime.utcnow().isoformat()

    columns = list(data.keys())
    placeholders = ", ".join(f"{c} = excluded.{c}" for c in columns)
    col_str = ", ".join(["month"] + columns + ["updated_at"])
    val_str = ", ".join(["?"] * (len(columns) + 2))

    values = [month] + [data[c] for c in columns] + [now]

    conn.execute(
        f"""INSERT INTO monthly_index ({col_str}) VALUES ({val_str})
            ON CONFLICT(month) DO UPDATE SET {placeholders}, updated_at = excluded.updated_at""",
        values,
    )
    conn.commit()
    conn.close()


def get_monthly_index(start_month=None, end_month=None, db_path=None):
    """Get monthly index data as a list of dicts.

    Args:
        start_month: YYYY-MM (inclusive), or None for no lower bound
        end_month: YYYY-MM (inclusive), or None for no upper bound
    """
    conn = get_connection(db_path)
    query = "SELECT * FROM monthly_index WHERE 1=1"
    params = []

    if start_month:
        query += " AND month >= ?"
        params.append(start_month)
    if end_month:
        query += " AND month <= ?"
        params.append(end_month)

    query += " ORDER BY month"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_pca_params(month, loadings, mean, std, variance_explained, db_path=None):
    """Save PCA parameters for reproducibility."""
    conn = get_connection(db_path)
    conn.execute(
        """INSERT OR REPLACE INTO pca_params
           (estimated_month, loadings_json, mean_json, std_json, variance_explained)
           VALUES (?, ?, ?, ?, ?)""",
        (
            month,
            json.dumps(loadings.tolist() if hasattr(loadings, "tolist") else loadings),
            json.dumps(mean.tolist() if hasattr(mean, "tolist") else mean),
            json.dumps(std.tolist() if hasattr(std, "tolist") else std),
            float(variance_explained),
        ),
    )
    conn.commit()
    conn.close()


def load_pca_params(db_path=None):
    """Load the most recent PCA parameters."""
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM pca_params ORDER BY estimated_month DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "estimated_month": row["estimated_month"],
        "loadings": json.loads(row["loadings_json"]),
        "mean": json.loads(row["mean_json"]),
        "std": json.loads(row["std_json"]),
        "variance_explained": row["variance_explained"],
    }
