"""
Data quality reporting UI components.
"""
import streamlit as st
from typing import Dict, List
from datetime import datetime
import pandas as pd
from core.models import DataQualityReport


def render_quality_report(report: DataQualityReport):
    """
    Render a data quality report with warnings and missing data.

    Args:
        report: DataQualityReport object
    """
    st.subheader("📊 Data Quality Report")

    # Summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Symbols Analyzed",
            len(report.symbols_analyzed)
        )

    with col2:
        total_missing = sum(len(fields) for fields in report.missing_fields.values())
        st.metric(
            "Missing Fields",
            total_missing,
            delta=None,
            delta_color="inverse"
        )

    with col3:
        total_negative = sum(len(fields) for fields in report.negative_denominators.values())
        st.metric(
            "Negative Denominators",
            total_negative,
            delta=None,
            delta_color="inverse"
        )

    st.divider()

    # Missing fields section
    if report.missing_fields:
        with st.expander("⚠️ Missing Data Fields", expanded=True):
            st.write("The following symbols are missing critical data fields:")

            missing_data = []
            for symbol, fields in report.missing_fields.items():
                missing_data.append({
                    "Symbol": symbol,
                    "Missing Fields": ", ".join(fields),
                    "Count": len(fields)
                })

            if missing_data:
                df = pd.DataFrame(missing_data)
                df = df.sort_values("Count", ascending=False)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.success("No missing fields detected")
    else:
        st.success("✅ No missing data fields detected")

    # Negative denominators section
    if report.negative_denominators:
        with st.expander("⚠️ Negative or Zero Denominators", expanded=True):
            st.write("These symbols have negative or zero values that affect ratio calculations:")

            negative_data = []
            for symbol, fields in report.negative_denominators.items():
                negative_data.append({
                    "Symbol": symbol,
                    "Affected Fields": ", ".join(fields),
                    "Count": len(fields)
                })

            if negative_data:
                df = pd.DataFrame(negative_data)
                df = df.sort_values("Count", ascending=False)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.info(
                    "💡 **Note**: In strict accounting mode, symbols with negative denominators "
                    "are excluded from composite calculations for affected metrics."
                )
    else:
        st.success("✅ No negative denominators detected")

    # Excluded symbols section
    if report.excluded_from_metrics:
        with st.expander("🚫 Symbols Excluded from Metrics", expanded=False):
            st.write("These symbols were excluded from specific metric calculations:")

            for metric, symbols in report.excluded_from_metrics.items():
                if symbols:
                    st.write(f"**{metric}**: {', '.join(symbols)}")

    # Currency warnings
    if report.currency_warnings:
        with st.expander("💱 Currency Warnings", expanded=False):
            st.warning("Mixed currencies detected in this group:")
            for warning in report.currency_warnings:
                st.write(f"- {warning}")

    # Forward-filled dates
    if report.forward_filled_dates:
        with st.expander("📅 Forward-Filled Data", expanded=False):
            st.info(
                "Fundamental data (revenue, EBITDA, etc.) is forward-filled between "
                "quarterly reporting dates. This is standard practice for TTM calculations."
            )

            ff_summary = []
            for symbol, dates in report.forward_filled_dates.items():
                ff_summary.append({
                    "Symbol": symbol,
                    "Forward-Fill Periods": len(dates)
                })

            if ff_summary:
                df = pd.DataFrame(ff_summary)
                st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # Timestamp
    st.caption(f"Report generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")


def render_coverage_summary(
    symbols: List[str],
    data_coverage: Dict[str, Dict[str, bool]]
):
    """
    Render a summary of data coverage across symbols.

    Args:
        symbols: List of symbols
        data_coverage: Dict mapping symbol -> field -> has_data (bool)
    """
    st.subheader("📈 Data Coverage Summary")

    # Create coverage matrix
    if not data_coverage:
        st.info("No coverage data available")
        return

    # Build DataFrame
    rows = []
    for symbol in symbols:
        if symbol not in data_coverage:
            continue

        row = {"Symbol": symbol}
        coverage = data_coverage[symbol]

        for field, has_data in coverage.items():
            row[field] = "✅" if has_data else "❌"

        rows.append(row)

    if rows:
        df = pd.DataFrame(rows)

        # Style the table
        def color_coverage(val):
            if val == "✅":
                return 'background-color: #d4edda'
            elif val == "❌":
                return 'background-color: #f8d7da'
            return ''

        styled_df = df.style.applymap(
            color_coverage,
            subset=[col for col in df.columns if col != 'Symbol']
        )

        st.dataframe(styled_df, use_container_width=True, hide_index=True)


def render_data_freshness(
    last_updated: Dict[str, datetime]
):
    """
    Render information about data freshness.

    Args:
        last_updated: Dict mapping symbol -> last update timestamp
    """
    st.subheader("🕒 Data Freshness")

    if not last_updated:
        st.info("No freshness data available")
        return

    freshness_data = []
    now = datetime.now()

    for symbol, timestamp in last_updated.items():
        age = now - timestamp
        age_str = f"{age.days} days, {age.seconds // 3600} hours ago"

        freshness_data.append({
            "Symbol": symbol,
            "Last Updated": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "Age": age_str
        })

    df = pd.DataFrame(freshness_data)
    df = df.sort_values("Last Updated", ascending=False)

    st.dataframe(df, use_container_width=True, hide_index=True)


def show_assumptions():
    """Display key assumptions and methodology notes."""
    st.subheader("📝 Key Assumptions & Methodology")

    with st.expander("Click to view assumptions"):
        st.markdown("""
        ### Data Sources
        - Primary source: Yahoo Finance (free)
        - Optional premium sources: FMP, Alpha Vantage (requires API keys)

        ### Market Cap Calculation
        - **MVP**: Market Cap = Current Price × Current Shares Outstanding
        - Historical market cap uses current shares (point-in-time shares not yet implemented)

        ### Enterprise Value
        - **EV = Market Cap + Total Debt - Cash**
        - Uses most recent balance sheet data
        - Updated as price changes with last reported debt/cash

        ### TTM (Trailing Twelve Months)
        - Fundamental metrics (Revenue, EBITDA, EBIT, Net Income) use TTM values
        - Calculated by summing last 4 quarters where available
        - Forward-filled between quarterly reporting dates

        ### Composite Calculations
        - **Additive metrics** (P/S, EV/Sales, P/E, etc.): Sum-over-sum approach
          - Example: Composite P/S = (Σ Market Cap) / (Σ Revenue)
        - **Rate metrics** (ROE): Weighted average
          - Default: Market cap weighted
          - Optional: Equity weighted

        ### Strict Accounting Mode
        - When enabled: Excludes symbols with negative/zero denominators
        - When disabled: Includes all symbols but flags non-standard values

        ### Missing Data
        - Symbols with missing critical fields are excluded from affected metrics
        - Warnings are displayed in the Data Quality tab

        ### Rolling Windows
        - Smooths ratio volatility using moving averages
        - Applied to composite metrics, not individual fundamentals

        ### Currency
        - Mixed currency groups are supported but flagged
        - No automatic FX conversion in MVP (uses reported currency)
        """)


def render_calculation_examples():
    """Show examples of how metrics are calculated."""
    st.subheader("🧮 Calculation Examples")

    with st.expander("P/S Ratio Example"):
        st.markdown("""
        **Individual Stock:**
        ```
        P/S = Market Cap / Revenue
        Example: AAPL with $3T market cap, $400B revenue
        P/S = 3,000B / 400B = 7.5
        ```

        **Composite (Group):**
        ```
        Composite P/S = (Σ Market Caps) / (Σ Revenues)
        Example: 3 stocks with $1T, $2T, $3T market caps
                 and $200B, $300B, $400B revenues
        Composite P/S = (1T + 2T + 3T) / (200B + 300B + 400B)
                      = 6T / 900B = 6.67
        ```
        """)

    with st.expander("ROE Example"):
        st.markdown("""
        **Individual Stock:**
        ```
        ROE = Net Income / Book Value (Equity)
        Example: Stock with $10B net income, $100B equity
        ROE = 10B / 100B = 0.10 = 10%
        ```

        **Composite (Market Cap Weighted):**
        ```
        Composite ROE = Σ(Weightᵢ × ROEᵢ)
        where Weightᵢ = Market Capᵢ / Σ Market Caps

        Example: 2 stocks
        Stock A: ROE = 15%, Market Cap = $1T
        Stock B: ROE = 10%, Market Cap = $2T

        Weight A = 1T / 3T = 0.333
        Weight B = 2T / 3T = 0.667

        Composite ROE = (0.333 × 15%) + (0.667 × 10%)
                      = 5% + 6.67% = 11.67%
        ```
        """)
