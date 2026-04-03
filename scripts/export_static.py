#!/usr/bin/env python3
"""Export SQLite data to static JSON files for Vercel deployment.

Run this after each monthly pipeline update, then push to GitHub.
Vercel will auto-deploy the updated static files.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import init_db, get_monthly_index, get_articles_for_month, load_pca_params

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "api"


def export():
    init_db()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. All monthly index data
    all_data = get_monthly_index()
    with open(OUTPUT_DIR / "index.json", "w") as f:
        json.dump({"data": all_data, "count": len(all_data)}, f, indent=2)
    print(f"Exported {len(all_data)} months to index.json")

    # 2. Latest + delta
    latest = all_data[-1] if all_data else None
    previous = all_data[-2] if len(all_data) >= 2 else None
    delta = None
    if previous and latest and latest.get("composite_index") and previous.get("composite_index"):
        delta = round(latest["composite_index"] - previous["composite_index"], 2)

    with open(OUTPUT_DIR / "latest.json", "w") as f:
        json.dump({"latest": latest, "previous": previous, "delta": delta}, f, indent=2)
    print(f"Exported latest.json (month: {latest['month'] if latest else 'N/A'})")

    # 3. PCA params
    pca = load_pca_params()
    with open(OUTPUT_DIR / "pca.json", "w") as f:
        json.dump({"data": pca}, f, indent=2)
    print(f"Exported pca.json")

    # 4. Articles per month
    articles_dir = OUTPUT_DIR / "articles"
    articles_dir.mkdir(exist_ok=True)
    for row in all_data:
        month = row["month"]
        articles = get_articles_for_month(month)
        with open(articles_dir / f"{month}.json", "w") as f:
            json.dump({"data": articles, "count": len(articles)}, f, indent=2)

    months_with_articles = [r["month"] for r in all_data if get_articles_for_month(r["month"])]
    print(f"Exported articles for {len(all_data)} months")

    print("\nDone! Files ready in public/api/")
    print("Next: git add . && git commit && git push")


if __name__ == "__main__":
    export()
