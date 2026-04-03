"""PCA-based composite index construction."""

import logging
import numpy as np
import pandas as pd

from src.database import get_monthly_index, save_pca_params, load_pca_params

logger = logging.getLogger(__name__)

# Sub-indicator columns used as PCA inputs
INDICATOR_COLS = [
    "sentiment_raw",
    "keyword_net",
    "keyword_uncertainty",
    "usd_cny_change",
    "vix_avg",
    "china_cpi_yoy",
    "google_trends",
]

# Columns that should be inverted (higher = worse sentiment)
INVERT_COLS = {"usd_cny_change", "vix_avg", "keyword_uncertainty"}


def estimate_pca(data_matrix):
    """Estimate PCA on a standardized data matrix.

    Args:
        data_matrix: numpy array of shape (n_months, n_indicators), already z-scored

    Returns:
        dict with 'loadings' (1D array), 'variance_explained' (float)
    """
    # Compute correlation matrix
    corr = np.corrcoef(data_matrix, rowvar=False)

    # Eigendecomposition
    eigenvalues, eigenvectors = np.linalg.eigh(corr)

    # eigh returns eigenvalues in ascending order; PC1 is the last
    pc1_loading = eigenvectors[:, -1]
    pc1_variance = eigenvalues[-1] / eigenvalues.sum()

    return {
        "loadings": pc1_loading,
        "variance_explained": float(pc1_variance),
    }


def compute_composite_index(month, min_months=18, pca_window=24, db_path=None):
    """Compute the composite index for a given month.

    If enough history exists (>= min_months), uses PCA.
    Otherwise, uses equal-weighted average of z-scored sub-indicators.

    Args:
        month: YYYY-MM string
        min_months: minimum months of history required for PCA
        pca_window: rolling window for PCA estimation

    Returns:
        dict with 'composite_index' (float, 0-100 scale) and
              'pc1_variance_explained' (float or None)
    """
    # Get all historical data up to and including this month
    all_data = get_monthly_index(end_month=month, db_path=db_path)

    if not all_data:
        logger.warning(f"No monthly index data available for composite computation")
        return {"composite_index": None, "pc1_variance_explained": None}

    df = pd.DataFrame(all_data)
    df = df.set_index("month").sort_index()

    # Check which indicators are available for the current month
    current = df.loc[month] if month in df.index else None
    if current is None:
        return {"composite_index": None, "pc1_variance_explained": None}

    # Collect available indicator values
    available_cols = [c for c in INDICATOR_COLS if pd.notna(current.get(c))]
    if len(available_cols) < 3:
        logger.warning(f"Only {len(available_cols)} indicators available for {month}")
        return {"composite_index": None, "pc1_variance_explained": None}

    # Build data matrix from available history
    sub_df = df[available_cols].dropna()

    # Invert columns where higher = worse
    for col in available_cols:
        if col in INVERT_COLS:
            sub_df[col] = -sub_df[col]

    n_months_available = len(sub_df)
    logger.info(f"Composite index: {n_months_available} months of data, {len(available_cols)} indicators")

    # Z-score standardization using rolling window
    window_data = sub_df.iloc[-pca_window:] if len(sub_df) > pca_window else sub_df
    means = window_data.mean()
    stds = window_data.std()

    # With only 1 month of data, std is NaN or 0. Use raw values centered at mean.
    if n_months_available <= 1:
        # Not enough data for z-scoring; return a neutral-ish composite
        # Map sentiment (0-1) linearly to index (0-100)
        sentiment_val = current.get("sentiment_raw")
        if sentiment_val is not None:
            composite = round(float(sentiment_val) * 100, 2)
        else:
            composite = 50.0
        logger.info(f"Single-month fallback for {month}: composite={composite}")
        return {"composite_index": composite, "pc1_variance_explained": None}

    stds = stds.replace(0, 1)  # Avoid division by zero

    z_scored = (sub_df - means) / stds

    if n_months_available >= min_months:
        # Use PCA
        z_matrix = z_scored.iloc[-pca_window:].values
        pca_result = estimate_pca(z_matrix)
        loadings = pca_result["loadings"]
        variance_explained = pca_result["variance_explained"]

        # Enforce sign convention: PC1 should correlate positively with sentiment
        sentiment_idx = available_cols.index("sentiment_raw") if "sentiment_raw" in available_cols else 0
        if loadings[sentiment_idx] < 0:
            loadings = -loadings

        # Project current month onto PC1
        current_z = z_scored.loc[month].values if month in z_scored.index else None
        if current_z is None:
            return {"composite_index": None, "pc1_variance_explained": None}

        pc1_score = float(np.dot(current_z, loadings))

        # Save PCA params
        save_pca_params(month, loadings, means.values, stds.values, variance_explained, db_path)

        logger.info(
            f"PCA composite for {month}: PC1 score={pc1_score:.3f}, "
            f"variance explained={variance_explained:.1%}"
        )
    else:
        # Equal-weighted average of z-scores
        current_z = z_scored.loc[month].values if month in z_scored.index else None
        if current_z is None:
            return {"composite_index": None, "pc1_variance_explained": None}

        pc1_score = float(np.mean(current_z))
        variance_explained = None
        logger.info(f"Equal-weighted composite for {month}: score={pc1_score:.3f} (only {n_months_available} months)")

    # Rescale to [0, 100] where 50 = neutral
    # Use the z-score range: typically [-3, 3] maps to [0, 100]
    composite = max(0, min(100, 50 + pc1_score * (50 / 3)))

    return {
        "composite_index": round(composite, 2),
        "pc1_variance_explained": variance_explained,
    }
