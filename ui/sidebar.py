"""
Sidebar UI for symbol selection, groups, and options.
"""
import streamlit as st
from typing import List, Optional, Dict
from pathlib import Path
import json
import os
from datetime import datetime, timedelta
import pandas as pd

from core.models import GroupConfig


# List of popular stock symbols for suggestions
POPULAR_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA",
    "AMD", "INTC", "TSM", "AVGO", "QCOM", "NFLX", "DIS", "PYPL",
    "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "BRK.B",
    "JNJ", "PFE", "UNH", "ABBV", "TMO", "XOM", "CVX", "COP",
    "SPY", "QQQ", "IWM", "DIA"
]

AVAILABLE_METRICS = [
    "P/S",
    "EV/Sales",
    "P/E",
    "PEG",
    "EV/EBITDA",
    "EV/EBIT",
    "P/B",
    "EV/AUM",
    "ROE"
]


def get_groups_file_path() -> Path:
    """Get path to groups JSON file."""
    config_dir = Path.home() / ".streamlit_fundamentals"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "groups.json"


def load_groups() -> Dict[str, GroupConfig]:
    """Load saved groups from disk."""
    groups_file = get_groups_file_path()
    if groups_file.exists():
        try:
            with open(groups_file, 'r') as f:
                data = json.load(f)
                # Convert to GroupConfig objects
                groups = {}
                for name, group_data in data.items():
                    # Handle legacy format (just a list of symbols)
                    if isinstance(group_data, list):
                        groups[name] = GroupConfig(
                            name=name,
                            symbols=group_data,
                            created_at=datetime.now()
                        )
                    # Handle new format (dict with full GroupConfig)
                    else:
                        groups[name] = GroupConfig(**group_data)
                return groups
        except Exception as e:
            st.error(f"Error loading groups: {e}")
            return {}
    return {}


def save_groups(groups: Dict[str, GroupConfig]) -> None:
    """Save groups to disk."""
    groups_file = get_groups_file_path()
    try:
        # Convert GroupConfig objects to dict for JSON serialization
        groups_data = {}
        for name, group_config in groups.items():
            groups_data[name] = group_config.model_dump(mode='json')

        with open(groups_file, 'w') as f:
            json.dump(groups_data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving groups: {e}")


def render_sidebar() -> Dict:
    """
    Render sidebar UI and return selected options.

    Returns:
        Dict with keys: symbols, selected_group, metrics, start_date, end_date,
                       frequency, rolling_window, strict_mode, roe_weighting,
                       adapter, refresh
    """
    st.sidebar.title("⚙️ Configuration")

    # Load existing groups
    groups = load_groups()

    # Symbol Selection
    st.sidebar.subheader("📊 Symbols")

    # Group selection
    group_options = ["Custom"] + list(groups.keys())
    selected_group = st.sidebar.selectbox(
        "Load Group",
        options=group_options,
        index=0,
        key="group_selector"
    )

    # Get symbols for selected group or custom
    if selected_group == "Custom":
        default_symbols = st.session_state.get('custom_symbols', ["AAPL", "MSFT", "NVDA"])
    else:
        group_config = groups.get(selected_group)
        default_symbols = group_config.symbols if group_config else []

    # Combine popular symbols with any saved symbols not in the popular list
    all_available_symbols = POPULAR_SYMBOLS.copy()
    for sym in default_symbols:
        if sym not in all_available_symbols:
            all_available_symbols.append(sym)
    all_available_symbols.sort()

    # Symbol multi-select - key changes with group to force widget reset
    symbols = st.sidebar.multiselect(
        "Select Symbols",
        options=all_available_symbols,
        default=default_symbols,
        key=f"symbol_multiselect_{selected_group}",
        help="Select one or more stock symbols"
    )

    # Add custom symbol input
    custom_symbol = st.sidebar.text_input(
        "Add Custom Symbol",
        placeholder="e.g., AAPL",
        key="custom_symbol_input"
    )
    if custom_symbol and st.sidebar.button("➕ Add Symbol"):
        symbol_upper = custom_symbol.upper().strip()
        if symbol_upper:
            # Add to current selection in session state
            current_symbols = list(symbols)  # Convert from tuple to list
            if symbol_upper not in current_symbols:
                current_symbols.append(symbol_upper)
                st.session_state['custom_symbols'] = current_symbols
                st.rerun()
            else:
                st.sidebar.info(f"{symbol_upper} already selected")

    # Save current symbols to session state (if Custom mode)
    if selected_group == "Custom":
        st.session_state['custom_symbols'] = list(symbols)

    # Group Management
    st.sidebar.subheader("💾 Group Management")

    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        new_group_name = st.text_input(
            "New Group Name",
            placeholder="e.g., My Portfolio",
            key="new_group_name"
        )
    with col2:
        if st.button("💾 Save", help="Save current symbols as a group"):
            if new_group_name and symbols:
                groups[new_group_name] = GroupConfig(
                    name=new_group_name,
                    symbols=list(symbols),
                    created_at=datetime.now()
                )
                save_groups(groups)
                st.success(f"Saved group '{new_group_name}'")
                st.rerun()
            elif not new_group_name:
                st.warning("Please enter a group name")
            elif not symbols:
                st.warning("Please select symbols first")

    # Delete group
    if selected_group != "Custom" and selected_group in groups:
        if st.sidebar.button(f"🗑️ Delete '{selected_group}'", type="secondary"):
            del groups[selected_group]
            save_groups(groups)
            st.success(f"Deleted group '{selected_group}'")
            st.rerun()

    st.sidebar.divider()

    # Metrics Selection
    st.sidebar.subheader("📈 Metrics")
    metrics = st.sidebar.multiselect(
        "Select Metrics to Compute",
        options=AVAILABLE_METRICS,
        default=["P/S", "EV/Sales", "P/E"],
        key="metrics_selector",
        help="Select one or more fundamental metrics"
    )

    st.sidebar.divider()

    # Date Range
    st.sidebar.subheader("📅 Date Range")
    default_start = datetime.now() - timedelta(days=365)
    default_end = datetime.now()

    date_col1, date_col2 = st.sidebar.columns(2)
    with date_col1:
        start_date = st.date_input(
            "Start",
            value=default_start,
            key="start_date"
        )
    with date_col2:
        end_date = st.date_input(
            "End",
            value=default_end,
            key="end_date"
        )

    # Frequency
    frequency = st.sidebar.selectbox(
        "Frequency",
        options=["Daily", "Weekly", "Monthly"],
        index=0,
        key="frequency"
    )

    # Map to interval codes
    freq_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
    interval = freq_map[frequency]

    st.sidebar.divider()

    # Advanced Options
    with st.sidebar.expander("⚙️ Advanced Options"):
        rolling_window = st.number_input(
            "Rolling Window (days)",
            min_value=1,
            max_value=252,
            value=30,
            step=1,
            help="Number of days for rolling average smoothing"
        )

        strict_mode = st.checkbox(
            "Strict Accounting Mode",
            value=True,
            help="Exclude symbols with negative/zero denominators from composite"
        )

        roe_weighting = st.selectbox(
            "ROE Weighting",
            options=["Market Cap", "Equity"],
            index=0,
            help="Weighting method for composite ROE calculation"
        )

        adapter = st.selectbox(
            "Data Source",
            options=["Yahoo Finance", "FMP", "Alpha Vantage"],
            index=0,
            help="Primary data source for fundamentals"
        )

    # Map adapter names
    adapter_map = {
        "Yahoo Finance": "yahoo",
        "FMP": "fmp",
        "Alpha Vantage": "alpha_vantage"
    }
    adapter_key = adapter_map[adapter]

    st.sidebar.divider()

    # Refresh button
    refresh = st.sidebar.button(
        "🔄 Refresh Data",
        type="primary",
        help="Clear cache and fetch fresh data"
    )

    # Export/Import groups
    with st.sidebar.expander("📤 Import/Export Groups"):
        # Export
        if groups:
            # Convert GroupConfig objects to dict for JSON export
            groups_export = {
                name: config.model_dump(mode='json')
                for name, config in groups.items()
            }
            groups_json = json.dumps(groups_export, indent=2)
            st.download_button(
                label="📥 Download Groups JSON",
                data=groups_json,
                file_name="symbol_groups.json",
                mime="application/json"
            )

        # Import
        uploaded_file = st.file_uploader(
            "📤 Upload Groups JSON",
            type=["json"],
            key="groups_upload"
        )
        if uploaded_file is not None:
            try:
                imported_data = json.load(uploaded_file)
                if st.button("Import Groups"):
                    # Convert imported data to GroupConfig objects
                    for name, group_data in imported_data.items():
                        # Handle legacy format (just a list)
                        if isinstance(group_data, list):
                            groups[name] = GroupConfig(
                                name=name,
                                symbols=group_data,
                                created_at=datetime.now()
                            )
                        # Handle new format (dict with full config)
                        else:
                            groups[name] = GroupConfig(**group_data)

                    save_groups(groups)
                    st.success(f"Imported {len(imported_data)} groups")
                    st.rerun()
            except Exception as e:
                st.error(f"Error importing groups: {e}")

    return {
        "symbols": symbols,
        "selected_group": selected_group if selected_group != "Custom" else None,
        "metrics": metrics,
        "start_date": pd.Timestamp(start_date),
        "end_date": pd.Timestamp(end_date),
        "frequency": frequency,
        "interval": interval,
        "rolling_window": rolling_window,
        "strict_mode": strict_mode,
        "roe_weighting": roe_weighting.lower().replace(" ", "_"),
        "adapter": adapter_key,
        "refresh": refresh
    }
