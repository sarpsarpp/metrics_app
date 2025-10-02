"""
Table components for displaying fundamentals data.
"""
import pandas as pd
import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime


def format_large_number(num: Optional[float]) -> str:
    """Format large numbers with K, M, B suffixes."""
    if num is None or pd.isna(num):
        return "N/A"

    if abs(num) >= 1e12:
        return f"${num/1e12:.2f}T"
    elif abs(num) >= 1e9:
        return f"${num/1e9:.2f}B"
    elif abs(num) >= 1e6:
        return f"${num/1e6:.2f}M"
    elif abs(num) >= 1e3:
        return f"${num/1e3:.2f}K"
    else:
        return f"${num:.2f}"


def format_ratio(num: Optional[float], decimals: int = 2) -> str:
    """Format a ratio value."""
    if num is None or pd.isna(num):
        return "N/A"
    return f"{num:.{decimals}f}"


def format_percentage(num: Optional[float], decimals: int = 2) -> str:
    """Format a percentage value."""
    if num is None or pd.isna(num):
        return "N/A"
    return f"{num*100:.{decimals}f}%"


def create_snapshot_table(
    symbol_data: Dict[str, Dict],
    metrics: List[str]
) -> pd.DataFrame:
    """
    Create a snapshot table showing latest values for each symbol.

    Args:
        symbol_data: Dict mapping symbol to dict of metric values
        metrics: List of metrics to include

    Returns:
        Formatted DataFrame
    """
    rows = []

    for symbol, data in symbol_data.items():
        row = {"Symbol": symbol}

        # Add market cap and price if available
        if "market_cap" in data:
            row["Market Cap"] = format_large_number(data["market_cap"])
        if "price" in data:
            row["Price"] = f"${data['price']:.2f}" if data['price'] else "N/A"

        # Add requested metrics
        for metric in metrics:
            metric_key = metric.lower().replace("/", "_").replace(" ", "_")
            value = data.get(metric_key)
            row[metric] = format_ratio(value)

        rows.append(row)

    df = pd.DataFrame(rows)

    # Sort by symbol
    if not df.empty and "Symbol" in df.columns:
        df = df.sort_values("Symbol")

    return df


def create_composite_row(
    composite_data: Dict[str, float],
    metrics: List[str]
) -> pd.DataFrame:
    """
    Create a single row showing composite values.

    Args:
        composite_data: Dict of metric -> value
        metrics: List of metrics to include

    Returns:
        DataFrame with single composite row
    """
    row = {"Symbol": "COMPOSITE"}

    for metric in metrics:
        metric_key = metric.lower().replace("/", "_").replace(" ", "_")
        value = composite_data.get(metric_key)
        row[metric] = format_ratio(value)

    return pd.DataFrame([row])


def create_full_table(
    symbol_data: Dict[str, Dict],
    composite_data: Dict[str, float],
    metrics: List[str]
) -> pd.DataFrame:
    """
    Create a full table with per-symbol data and composite row.

    Args:
        symbol_data: Dict mapping symbol to dict of metric values
        composite_data: Dict of composite metric values
        metrics: List of metrics to include

    Returns:
        Combined DataFrame
    """
    # Create symbol table
    symbol_df = create_snapshot_table(symbol_data, metrics)

    # Create composite row
    composite_df = create_composite_row(composite_data, metrics)

    # Combine
    if not symbol_df.empty and not composite_df.empty:
        # Ensure same columns
        for col in symbol_df.columns:
            if col not in composite_df.columns:
                composite_df[col] = "—"

        result = pd.concat([symbol_df, composite_df], ignore_index=True)
        return result

    return symbol_df


def style_table(df: pd.DataFrame):
    """
    Apply styling to a DataFrame for better presentation.

    Args:
        df: DataFrame to style

    Returns:
        Styled DataFrame
    """
    if df.empty:
        return df.style

    def highlight_composite(row):
        """Highlight the composite row."""
        if row.get("Symbol") == "COMPOSITE":
            return ['background-color: #f0f0f0; font-weight: bold'] * len(row)
        return [''] * len(row)

    styled = df.style.apply(highlight_composite, axis=1)

    # Center align all columns except Symbol
    styled = styled.set_properties(**{
        'text-align': 'center'
    }, subset=[col for col in df.columns if col != 'Symbol'])

    # Left align Symbol column
    if 'Symbol' in df.columns:
        styled = styled.set_properties(**{
            'text-align': 'left',
            'font-weight': 'bold'
        }, subset=['Symbol'])

    return styled


def create_time_series_table(
    df: pd.DataFrame,
    metrics: List[str],
    last_n: int = 10
) -> pd.DataFrame:
    """
    Create a table showing the most recent time series data.

    Args:
        df: DataFrame with timestamp index and metric columns
        metrics: List of metrics to include
        last_n: Number of most recent rows to show

    Returns:
        Formatted DataFrame
    """
    if df.empty:
        return pd.DataFrame()

    # Get last N rows
    recent = df.tail(last_n).copy()

    # Format timestamp
    recent.index = recent.index.strftime('%Y-%m-%d')

    # Select and format metric columns
    display_cols = []
    for metric in metrics:
        if metric in recent.columns:
            recent[metric] = recent[metric].apply(lambda x: format_ratio(x))
            display_cols.append(metric)

    result = recent[display_cols] if display_cols else recent

    return result


def create_summary_stats(
    df: pd.DataFrame,
    metrics: List[str]
) -> pd.DataFrame:
    """
    Create a summary statistics table for metrics.

    Args:
        df: DataFrame with timestamp index and metric columns
        metrics: List of metrics to analyze

    Returns:
        DataFrame with summary statistics
    """
    stats_data = []

    for metric in metrics:
        if metric not in df.columns:
            continue

        data = df[metric].dropna()
        if data.empty:
            continue

        stats = {
            "Metric": metric,
            "Current": format_ratio(data.iloc[-1] if len(data) > 0 else None),
            "Mean": format_ratio(data.mean()),
            "Median": format_ratio(data.median()),
            "Min": format_ratio(data.min()),
            "Max": format_ratio(data.max()),
            "Std Dev": format_ratio(data.std())
        }

        stats_data.append(stats)

    return pd.DataFrame(stats_data)


def render_dataframe_with_download(
    df: pd.DataFrame,
    title: str,
    download_filename: str,
    key_suffix: str = ""
):
    """
    Render a DataFrame with a download button.

    Args:
        df: DataFrame to display
        title: Title for the table
        download_filename: Filename for CSV download
        key_suffix: Suffix for Streamlit widget keys to ensure uniqueness
    """
    if df.empty:
        st.info("No data available")
        return

    st.subheader(title)

    # Display table
    st.dataframe(df, use_container_width=True)

    # Download button
    csv = df.to_csv(index=True).encode('utf-8')
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name=download_filename,
        mime="text/csv",
        key=f"download_{key_suffix}"
    )
