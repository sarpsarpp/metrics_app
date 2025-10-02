# Composite Fundamentals - Streamlit App

A production-ready **Streamlit** application for analyzing fundamental metrics across groups of stocks using accounting-consistent composite calculations.

## Features

- 📊 **Multiple Fundamental Metrics**: P/S, EV/Sales, P/E, PEG, EV/EBITDA, EV/EBIT, P/B, EV/AUM, ROE
- 🎯 **Composite Calculations**: Proper sum-over-sum aggregation for accounting metrics and weighted averages for rates
- 📊 **Per-Symbol Breakdown**: View individual metrics for each stock alongside composite values
- 📈 **Interactive Charts**: Plotly-powered visualizations with multiple viewing modes
- 💾 **Group Management**: Save, load, and share symbol groups
- 🔍 **Data Quality Reports**: Comprehensive warnings about missing data, negative denominators, and forward-filled values
- 📋 **Data Coverage Badges**: Real-time indicators for symbols fetched, data points, and source status
- 💨 **Caching**: Fast performance with Streamlit's built-in caching and optional on-disk storage
- 🔌 **Extensible Adapters**: Primary support for Yahoo Finance, with placeholders for premium APIs (FMP, Alpha Vantage)
- 📥 **Export**: Download time series data and charts as CSV

## Installation

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Setup

1. **Clone or download this repository**

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables (optional)**

For premium data sources, copy the example env file and add your API keys:

```bash
cp .env.example .env
# Edit .env and add your API keys
```

4. **Run the application**

```bash
# From the project root directory
streamlit run app/app.py

# Or use the convenience script
./run.sh
```

The app will open in your browser at `http://localhost:8501`

## Usage

### Quick Start

1. **Select Symbols**: Choose from popular symbols or add custom tickers in the sidebar
2. **Choose Metrics**: Select one or more fundamental metrics to analyze
3. **Configure Options**: Set date range, frequency, rolling window, and strict accounting mode
4. **View Results**: Explore interactive charts, tables, and data quality reports

### Creating Symbol Groups

1. Select symbols in the sidebar
2. Enter a name for your group (e.g., "My Tech Portfolio")
3. Click **💾 Save**
4. Load saved groups anytime from the dropdown

### Understanding Composite Metrics

The app uses **accounting-consistent aggregation**:

- **Additive metrics** (P/S, EV/Sales, P/E, etc.): Sum-over-sum approach
  - Example: Composite P/S = (Σ Market Cap) / (Σ Revenue)

- **Rate metrics** (ROE): Weighted average (market cap or equity weighted)
  - Example: Composite ROE = Σ(Weight × ROE) where Weight = Market Cap / Σ Market Caps

### Tabs Overview

- **📋 Overview**: Data coverage badges, summary statistics, and latest composite values
- **📈 Charts**: Interactive time series visualizations with multiple viewing modes
- **📊 Table**:
  - **Per-Symbol Latest Snapshot**: Individual metrics for each stock + composite row
  - **Composite Time Series**: Historical aggregated values over time
- **🔍 Data Quality**: Warnings, missing data, assumptions, and methodology notes

## Project Structure

```
app/
├── app.py                      # Main Streamlit application
├── core/
│   ├── models.py               # Pydantic data models
│   ├── metrics.py              # Metric calculation functions
│   ├── adapters/
│   │   ├── base.py             # Adapter protocol
│   │   ├── yahoo.py            # Yahoo Finance adapter
│   │   ├── fmp.py              # Financial Modeling Prep (placeholder)
│   │   └── alpha_vantage.py    # Alpha Vantage (placeholder)
│   ├── repository.py           # Data orchestration layer
│   └── cache.py                # Caching utilities
├── ui/
│   ├── sidebar.py              # Sidebar UI components
│   ├── charts.py               # Plotly chart builders
│   ├── tables.py               # Table formatting and display
│   └── quality.py              # Data quality reporting UI
├── assets/
│   └── sample_groups.json      # Pre-configured symbol groups
└── tests/
    ├── test_metrics.py         # Unit tests for metrics
    ├── test_adapters.py        # Unit tests for adapters
    └── test_repository.py      # Unit tests for repository

requirements.txt                # Python dependencies
.env.example                    # Environment variables template
README.md                       # This file
```

## Configuration

### Data Sources

By default, the app uses **Yahoo Finance** (free, no API key required). Optional premium sources can be configured via environment variables:

```bash
# .env file
FMP_API_KEY=your_fmp_api_key_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
```

### Caching

Cache settings can be configured in `.env`:

```bash
CACHE_DIR=~/.streamlit_fundamentals/cache
CACHE_TTL_SECONDS=3600
```

## Key Assumptions

### Market Cap Calculation
- **MVP**: Market Cap = Current Price × Current Shares Outstanding
- Historical market cap uses current shares outstanding (point-in-time shares not yet implemented)

### Enterprise Value
- **EV = Market Cap + Total Debt - Cash**
- Uses most recent balance sheet data

### TTM (Trailing Twelve Months)
- Fundamental metrics use TTM values where available
- Calculated by summing last 4 quarters
- Forward-filled between quarterly reporting dates

### Strict Accounting Mode
- **Enabled**: Excludes symbols with negative/zero denominators from composite calculations
- **Disabled**: Includes all symbols but flags non-standard values

## Testing

Run the test suite:

```bash
# Run all tests
pytest app/tests/ -v

# Run specific test file
pytest app/tests/test_metrics.py -v

# Run with coverage
pytest app/tests/ --cov=app/core --cov-report=html
```

## Sample Groups

The app includes pre-configured groups in `app/assets/sample_groups.json`:

- **Mag7**: AAPL, MSFT, GOOGL, AMZN, META, TSLA, NVDA
- **Semis**: NVDA, AMD, INTC, TSM, AVGO, QCOM, MU, AMAT
- **FAANG**: META, AAPL, AMZN, NFLX, GOOGL
- **Banks**: JPM, BAC, WFC, C, GS, MS
- **Energy**: XOM, CVX, COP, SLB, EOG, PXD

You can import these groups via the sidebar's Import/Export section.

## Troubleshooting

### No data available
- Verify symbol tickers are valid
- Check internet connection
- Try clearing cache (🔄 Refresh Data button)

### Missing fundamentals
- Some companies may not report all metrics (e.g., AUM is only for asset managers)
- Check the Data Quality tab for specifics

### Slow performance
- Reduce date range or number of symbols
- Increase rolling window for smoother data
- Cached data should speed up subsequent queries

## Advanced Features

### Rolling Windows
Smooth ratio volatility using moving averages. Set window size in sidebar (default: 30 days).

### ROE Weighting
Choose between:
- **Market Cap Weighted** (default): Weights by market capitalization
- **Equity Weighted**: Weights by book value

### Export Groups
1. Configure your symbols
2. Expand "Import/Export Groups" in sidebar
3. Click "Download Groups JSON"
4. Share with others or backup for later

## Contributing

To extend this app:

1. **Add new metrics**: Implement in `core/metrics.py` and add to `AVAILABLE_METRICS` in `ui/sidebar.py`
2. **Add new adapters**: Create new file in `core/adapters/` following the `AbstractFundamentalsSource` protocol
3. **Add tests**: Create corresponding test files in `app/tests/`

## License

This project is provided as-is for educational and analytical purposes.

## Acknowledgments

- Data provided by Yahoo Finance (via yfinance)
- Built with Streamlit, Plotly, Pandas, and Pydantic

---

**Built with ❤️ for fundamental analysis**
