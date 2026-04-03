"""Streamlit dashboard for the Economic Sentiment Index."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.database import init_db, get_monthly_index, get_articles_for_month, load_pca_params

# Page config
st.set_page_config(
    page_title="China Economic Sentiment Index",
    page_icon="📊",
    layout="wide",
)

# Initialize database
init_db()


@st.cache_data(ttl=300)
def load_index_data():
    """Load all monthly index data."""
    data = get_monthly_index()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["month"] = pd.to_datetime(df["month"] + "-01")
    return df.sort_values("month")


@st.cache_data(ttl=300)
def load_articles(month_str):
    """Load articles for a specific month."""
    return get_articles_for_month(month_str)


def main():
    st.title("China Economic Sentiment Index (经济财经舆情指数)")

    # Sidebar
    with st.sidebar:
        st.header("Controls")

        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        st.divider()

        # Manual pipeline run
        st.subheader("Run Pipeline")
        run_month = st.text_input("Month (YYYY-MM)", value="")
        if st.button("Run Update") and run_month:
            with st.spinner(f"Running pipeline for {run_month}..."):
                try:
                    from src.pipeline import run_full_update
                    result = run_full_update(run_month)
                    st.success(f"Pipeline complete! Composite: {result.get('composite_index', 'N/A')}")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")

    # Load data
    df = load_index_data()

    if df.empty:
        st.warning(
            "No data yet. Run the pipeline first:\n\n"
            "```bash\npython scripts/run_update.py --month 2025-03\n```\n\n"
            "Or use the sidebar to run an update."
        )
        return

    # --- Header metrics ---
    latest = df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)

    composite = latest.get("composite_index")
    with col1:
        delta = None
        if len(df) >= 2 and composite is not None:
            prev = df.iloc[-2].get("composite_index")
            if prev is not None:
                delta = round(composite - prev, 2)
        st.metric(
            "Composite Index",
            f"{composite:.1f}" if composite is not None else "N/A",
            delta=f"{delta:+.1f}" if delta is not None else None,
        )

    with col2:
        sentiment = latest.get("sentiment_raw")
        st.metric(
            "Sentiment Score",
            f"{sentiment:.3f}" if sentiment is not None else "N/A",
        )

    with col3:
        kw_net = latest.get("keyword_net")
        st.metric(
            "Keyword Net",
            f"{kw_net:.2f}" if kw_net is not None else "N/A",
        )

    with col4:
        var_exp = latest.get("pc1_variance_explained")
        st.metric(
            "PC1 Var. Explained",
            f"{var_exp:.1%}" if var_exp is not None else "N/A (equal-wt)",
        )

    st.caption(f"Latest data: {latest['month'].strftime('%Y-%m')}")

    # --- Main composite chart ---
    st.subheader("Composite Index Over Time")

    if composite is not None:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["month"],
                y=df["composite_index"],
                mode="lines+markers",
                name="Composite Index",
                line=dict(color="#1f77b4", width=2),
                marker=dict(size=6),
            )
        )
        fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="Neutral (50)")
        fig.add_hrect(y0=0, y1=30, fillcolor="red", opacity=0.05, line_width=0)
        fig.add_hrect(y0=70, y1=100, fillcolor="green", opacity=0.05, line_width=0)
        fig.update_layout(
            yaxis_title="Index (0-100)",
            yaxis_range=[0, 100],
            height=400,
            margin=dict(l=50, r=20, t=20, b=50),
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- Sub-indicators ---
    st.subheader("Sub-Indicators")

    col_left, col_right = st.columns(2)

    with col_left:
        # Sentiment sub-index
        if "sentiment_raw" in df.columns and df["sentiment_raw"].notna().any():
            fig_sent = go.Figure()
            fig_sent.add_trace(
                go.Scatter(
                    x=df["month"], y=df["sentiment_raw"],
                    mode="lines+markers", name="NLP Sentiment",
                    line=dict(color="#2ca02c"),
                )
            )
            fig_sent.update_layout(
                title="NLP Sentiment (SnowNLP, 0-1)",
                height=300, margin=dict(l=50, r=20, t=40, b=30),
            )
            st.plotly_chart(fig_sent, use_container_width=True)

        # Keyword Net
        if "keyword_net" in df.columns and df["keyword_net"].notna().any():
            fig_kw = go.Figure()
            fig_kw.add_trace(
                go.Bar(
                    x=df["month"], y=df["keyword_net"],
                    name="Keyword Net",
                    marker_color=df["keyword_net"].apply(
                        lambda x: "#2ca02c" if x and x > 0 else "#d62728"
                    ),
                )
            )
            fig_kw.update_layout(
                title="Keyword Net Sentiment (pos - neg, per 1000 words)",
                height=300, margin=dict(l=50, r=20, t=40, b=30),
            )
            st.plotly_chart(fig_kw, use_container_width=True)

    with col_right:
        # VIX
        if "vix_avg" in df.columns and df["vix_avg"].notna().any():
            fig_vix = go.Figure()
            fig_vix.add_trace(
                go.Scatter(
                    x=df["month"], y=df["vix_avg"],
                    mode="lines+markers", name="VIX",
                    line=dict(color="#ff7f0e"),
                )
            )
            fig_vix.update_layout(
                title="VIX (Global Risk, inverted in composite)",
                height=300, margin=dict(l=50, r=20, t=40, b=30),
            )
            st.plotly_chart(fig_vix, use_container_width=True)

        # USD/CNY change
        if "usd_cny_change" in df.columns and df["usd_cny_change"].notna().any():
            fig_fx = go.Figure()
            fig_fx.add_trace(
                go.Bar(
                    x=df["month"], y=df["usd_cny_change"],
                    name="USD/CNY Change %",
                    marker_color=df["usd_cny_change"].apply(
                        lambda x: "#d62728" if x and x > 0 else "#2ca02c"  # Red = depreciation
                    ),
                )
            )
            fig_fx.update_layout(
                title="USD/CNY Monthly Change (%, positive = CNY weakening)",
                height=300, margin=dict(l=50, r=20, t=40, b=30),
            )
            st.plotly_chart(fig_fx, use_container_width=True)

    # --- PCA Diagnostics ---
    pca_data = load_pca_params()
    if pca_data:
        st.subheader("PCA Diagnostics")
        col_pca1, col_pca2 = st.columns([2, 1])

        with col_pca1:
            indicator_names = [
                "Sentiment", "Keyword Net", "Uncertainty",
                "USD/CNY", "VIX", "CPI YoY", "Google Trends"
            ]
            loadings = pca_data["loadings"]
            # Trim labels to match loadings length
            labels = indicator_names[:len(loadings)]

            fig_load = go.Figure()
            fig_load.add_trace(
                go.Bar(
                    x=labels, y=loadings,
                    marker_color=[
                        "#2ca02c" if v > 0 else "#d62728" for v in loadings
                    ],
                )
            )
            fig_load.update_layout(
                title="PC1 Loadings (contribution to composite index)",
                height=350, margin=dict(l=50, r=20, t=40, b=50),
            )
            st.plotly_chart(fig_load, use_container_width=True)

        with col_pca2:
            st.metric("Variance Explained", f"{pca_data['variance_explained']:.1%}")
            st.caption(f"Estimated: {pca_data['estimated_month']}")

    # --- Recent Articles ---
    st.subheader("Recent Articles")

    if not df.empty:
        selected_month = st.selectbox(
            "Select month",
            df["month"].dt.strftime("%Y-%m").tolist()[::-1],
        )
        articles = load_articles(selected_month)
        if articles:
            articles_df = pd.DataFrame(articles)[["source", "title", "published_date"]]
            st.dataframe(articles_df, use_container_width=True, height=400)
        else:
            st.info(f"No articles stored for {selected_month}")


if __name__ == "__main__":
    main()
