"""
Streamlit Composite Fundamentals App

Main application entry point.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import logging
from dotenv import load_dotenv

from core.repository import FundamentalsRepository
from core.models import DataQualityReport
from ui.sidebar import render_sidebar
from ui.charts import create_metric_chart, create_multi_metric_chart
from ui.tables import (
    create_snapshot_table, create_composite_row, create_full_table,
    create_time_series_table, create_summary_stats, render_dataframe_with_download,
    style_table
)
from ui.quality import (
    render_quality_report, render_coverage_summary,
    show_assumptions, render_calculation_examples
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Composite Fundamentals",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        background-color: #e8f4f8;
        border-radius: 1rem;
        font-size: 0.9rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if 'repository' not in st.session_state:
        st.session_state.repository = None
    if 'composite_data' not in st.session_state:
        st.session_state.composite_data = None
    if 'quality_report' not in st.session_state:
        st.session_state.quality_report = None


def main():
    """Main application function."""
    initialize_session_state()

    # Header
    st.markdown('<div class="main-header">📊 Composite Fundamentals</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Analyze fundamental metrics for stock groups with accounting-consistent aggregation</div>',
        unsafe_allow_html=True
    )

    # Render sidebar and get configuration
    config = render_sidebar()

    # Validate inputs
    if not config['symbols']:
        st.warning("👈 Please select at least one symbol from the sidebar to begin analysis")
        st.info("""
        **Getting Started:**
        1. Select symbols from the dropdown or enter custom tickers
        2. Choose metrics to analyze (P/S, EV/Sales, P/E, etc.)
        3. Configure date range and options
        4. View results in the tabs below
        """)
        return

    if not config['metrics']:
        st.warning("👈 Please select at least one metric to analyze")
        return

    # Initialize repository if needed or refresh requested
    if st.session_state.repository is None or config['refresh']:
        with st.spinner("Initializing data source..."):
            st.session_state.repository = FundamentalsRepository(
                primary_adapter=config['adapter']
            )
            if config['refresh']:
                st.session_state.repository.clear_cache()
                st.success("Cache cleared!")

    repo = st.session_state.repository

    # Display current selection
    group_name = config['selected_group'] or "Custom Selection"
    st.subheader(f"📈 Analyzing: **{group_name}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Symbols", len(config['symbols']))
    with col2:
        st.metric("Metrics", len(config['metrics']))
    with col3:
        date_range_days = (config['end_date'] - config['start_date']).days
        st.metric("Date Range", f"{date_range_days} days")

    # Show selected symbols and metrics
    st.write("**Symbols:**", ", ".join(sorted(config['symbols'])))
    st.write("**Metrics:**", ", ".join(config['metrics']))

    st.divider()

    # Fetch and compute data
    try:
        with st.spinner("Fetching data and computing composite metrics..."):
            composite_df, quality_report = repo.compute_composite_series(
                symbols=config['symbols'],
                start=config['start_date'],
                end=config['end_date'],
                selected_metrics=config['metrics'],
                interval=config['interval'],
                rolling_window=config['rolling_window'],
                strict_mode=config['strict_mode'],
                roe_weighting=config['roe_weighting'],
                adapter_name=config['adapter']
            )

            st.session_state.composite_data = composite_df
            st.session_state.quality_report = quality_report

        # Fetch per-symbol metrics for latest snapshot
        with st.spinner("Computing per-symbol metrics..."):
            per_symbol_metrics = repo.compute_per_symbol_metrics(
                symbols=config['symbols'],
                selected_metrics=config['metrics'],
                strict_mode=config['strict_mode'],
                adapter_name=config['adapter']
            )
            st.session_state.per_symbol_metrics = per_symbol_metrics

    except Exception as e:
        st.error(f"Error computing metrics: {e}")
        logger.error(f"Error in compute_composite_series: {e}", exc_info=True)
        return

    composite_df = st.session_state.composite_data
    quality_report = st.session_state.quality_report

    if composite_df.empty:
        st.warning("No data available for the selected configuration. Please check:")
        st.write("- Symbol tickers are valid")
        st.write("- Date range includes trading days")
        st.write("- Selected data source is accessible")
        return

    # Create tabs
    tab_overview, tab_charts, tab_table, tab_quality = st.tabs([
        "📋 Overview",
        "📈 Charts",
        "📊 Table",
        "🔍 Data Quality"
    ])

    # ========== OVERVIEW TAB ==========
    with tab_overview:
        # Data Coverage Badges (NEW)
        st.subheader("📋 Data Coverage")

        per_symbol_metrics = st.session_state.get('per_symbol_metrics', {})

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            symbols_fetched = len(per_symbol_metrics)
            symbols_requested = len(config['symbols'])
            st.metric(
                "Symbols Fetched",
                f"{symbols_fetched}/{symbols_requested}",
                delta=None if symbols_fetched == symbols_requested else f"{symbols_requested - symbols_fetched} missing",
                delta_color="normal" if symbols_fetched == symbols_requested else "inverse"
            )

        with col2:
            if not composite_df.empty:
                data_points = len(composite_df)
                st.metric("Data Points", data_points)
            else:
                st.metric("Data Points", 0)

        with col3:
            date_range_days = (config['end_date'] - config['start_date']).days
            st.metric("Date Range", f"{date_range_days} days")

        with col4:
            st.metric("Data Source", config['adapter'].upper())

        # Show which symbols succeeded/failed
        if symbols_fetched < symbols_requested:
            failed_symbols = set(config['symbols']) - set(per_symbol_metrics.keys())
            if failed_symbols:
                st.warning(f"⚠️ Failed to fetch data for: {', '.join(sorted(failed_symbols))}")

        st.divider()

        # Summary Statistics
        st.subheader("Summary Statistics")

        # Summary stats for each metric
        summary_df = create_summary_stats(composite_df, config['metrics'])

        if not summary_df.empty:
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        else:
            st.info("No summary statistics available")

        st.divider()

        # Latest values
        st.subheader("Latest Composite Values")

        if not composite_df.empty:
            latest = composite_df.iloc[-1]
            latest_date = composite_df.index[-1]

            st.write(f"**As of:** {latest_date.strftime('%Y-%m-%d')}")

            # Display metrics in columns
            metric_cols = st.columns(min(len(config['metrics']), 4))
            for i, metric in enumerate(config['metrics']):
                if metric in composite_df.columns:
                    value = latest[metric]
                    if pd.notna(value):
                        with metric_cols[i % len(metric_cols)]:
                            st.metric(metric, f"{value:.2f}")

        st.divider()

        # Show recent data
        st.subheader("Recent Time Series (Last 10 Days)")
        recent_df = create_time_series_table(composite_df, config['metrics'], last_n=10)

        if not recent_df.empty:
            st.dataframe(recent_df, use_container_width=True)

    # ========== CHARTS TAB ==========
    with tab_charts:
        st.subheader("Composite Metrics Over Time")

        # Option to show all metrics together or separately
        chart_mode = st.radio(
            "Chart Mode",
            options=["Individual Charts", "Combined Chart", "Combined (Normalized)"],
            horizontal=True
        )

        if chart_mode == "Individual Charts":
            # Individual charts for each metric
            for metric in config['metrics']:
                if metric in composite_df.columns:
                    show_rolling = config['rolling_window'] > 1
                    fig = create_metric_chart(
                        df=composite_df,
                        metric_name=metric,
                        title=f"{group_name} - {metric}",
                        show_rolling=show_rolling
                    )
                    st.plotly_chart(fig, use_container_width=True)

        elif chart_mode == "Combined Chart":
            # All metrics on one chart
            fig = create_multi_metric_chart(
                df=composite_df,
                metrics=config['metrics'],
                title=f"{group_name} - All Metrics",
                normalize=False
            )
            st.plotly_chart(fig, use_container_width=True)

        else:  # Normalized
            # All metrics normalized to 100
            fig = create_multi_metric_chart(
                df=composite_df,
                metrics=config['metrics'],
                title=f"{group_name} - All Metrics (Indexed to 100)",
                normalize=True
            )
            st.plotly_chart(fig, use_container_width=True)

        # Download chart data
        st.divider()
        csv = composite_df.to_csv().encode('utf-8')
        st.download_button(
            label="📥 Download Chart Data (CSV)",
            data=csv,
            file_name=f"composite_metrics_{group_name}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    # ========== TABLE TAB ==========
    with tab_table:
        # Per-Symbol Breakdown (NEW)
        st.subheader("📊 Per-Symbol Latest Snapshot")

        per_symbol_metrics = st.session_state.get('per_symbol_metrics', {})

        if per_symbol_metrics:
            # Create composite row data from latest composite values
            composite_latest = {}
            if not composite_df.empty:
                latest_composite = composite_df.iloc[-1]
                for metric in config['metrics']:
                    # Get value directly from composite_df (columns are named with slashes)
                    value = latest_composite.get(metric)
                    # Store with underscore key for create_full_table
                    metric_key = metric.lower().replace("/", "_").replace(" ", "_")
                    composite_latest[metric_key] = value

            # Build full table with per-symbol + composite
            full_table_df = create_full_table(
                symbol_data=per_symbol_metrics,
                composite_data=composite_latest,
                metrics=config['metrics']
            )

            if not full_table_df.empty:
                # Display table without special styling for composite row
                st.dataframe(full_table_df, use_container_width=True, hide_index=True)

                # Download per-symbol data
                csv_per_symbol = full_table_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Per-Symbol Data (CSV)",
                    data=csv_per_symbol,
                    file_name=f"per_symbol_snapshot_{group_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_per_symbol"
                )
            else:
                st.info("No per-symbol data available")
        else:
            st.info("No per-symbol metrics computed yet")

        st.divider()

        # Composite Time Series (Existing)
        st.subheader("📈 Composite Time Series (Historical)")

        # Show full time series as table
        if not composite_df.empty:
            # Prepare display dataframe
            display_df = composite_df.copy()

            # Format index
            display_df.index = display_df.index.strftime('%Y-%m-%d')

            # Select only the requested metrics
            available_metrics = [m for m in config['metrics'] if m in display_df.columns]
            if available_metrics:
                display_df = display_df[available_metrics]

                # Format values
                for col in display_df.columns:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
                    )

                st.dataframe(display_df, use_container_width=True)

                # Download button
                csv = composite_df[available_metrics].to_csv().encode('utf-8')
                st.download_button(
                    label="📥 Download Table Data (CSV)",
                    data=csv,
                    file_name=f"composite_table_{group_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_table"
                )
            else:
                st.info("No metrics available in the dataset")

        st.divider()

        # Show summary statistics table
        st.subheader("Summary Statistics")
        summary_df = create_summary_stats(composite_df, config['metrics'])
        if not summary_df.empty:
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # ========== DATA QUALITY TAB ==========
    with tab_quality:
        # Render quality report
        render_quality_report(quality_report)

        st.divider()

        # Show assumptions and methodology
        show_assumptions()

        st.divider()

        # Calculation examples
        render_calculation_examples()

    # Footer
    st.divider()
    st.caption(
        "Composite Fundamentals App | "
        f"Data Source: {config['adapter']} | "
        f"Rolling Window: {config['rolling_window']} days | "
        f"Strict Mode: {'ON' if config['strict_mode'] else 'OFF'}"
    )


if __name__ == "__main__":
    main()
