"""FastAPI backend for the Economic Sentiment Index PWA."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.database import init_db, get_monthly_index, get_articles_for_month, load_pca_params

app = FastAPI(title="China Economic Sentiment Index API")

# Initialize database on startup
init_db()

# --- API Endpoints ---

@app.get("/api/index")
def get_all_index():
    """Get all monthly index data."""
    data = get_monthly_index()
    return {"data": data, "count": len(data)}


@app.get("/api/index/{month}")
def get_month_index(month: str):
    """Get index data for a specific month (YYYY-MM)."""
    data = get_monthly_index(start_month=month, end_month=month)
    if not data:
        return {"data": None}
    return {"data": data[0]}


@app.get("/api/articles/{month}")
def get_articles(month: str):
    """Get articles for a specific month."""
    articles = get_articles_for_month(month)
    return {"data": articles, "count": len(articles)}


@app.get("/api/pca")
def get_pca():
    """Get latest PCA parameters."""
    params = load_pca_params()
    return {"data": params}


@app.get("/api/latest")
def get_latest():
    """Get the most recent month's data with delta from previous month."""
    data = get_monthly_index()
    if not data:
        return {"latest": None, "previous": None, "delta": None}

    latest = data[-1]
    previous = data[-2] if len(data) >= 2 else None

    delta = None
    if previous and latest.get("composite_index") is not None and previous.get("composite_index") is not None:
        delta = round(latest["composite_index"] - previous["composite_index"], 2)

    return {"latest": latest, "previous": previous, "delta": delta}


# --- Serve PWA static files ---

PWA_DIR = Path(__file__).parent.parent / "pwa"

# Mount static files (CSS, JS, icons)
app.mount("/icons", StaticFiles(directory=str(PWA_DIR / "icons")), name="icons")


@app.get("/manifest.json")
def manifest():
    return FileResponse(str(PWA_DIR / "manifest.json"))


@app.get("/sw.js")
def service_worker():
    return FileResponse(str(PWA_DIR / "sw.js"), media_type="application/javascript")


@app.get("/style.css")
def stylesheet():
    return FileResponse(str(PWA_DIR / "style.css"), media_type="text/css")


@app.get("/app.js")
def app_js():
    return FileResponse(str(PWA_DIR / "app.js"), media_type="application/javascript")


@app.get("/")
def root():
    return FileResponse(str(PWA_DIR / "index.html"))
