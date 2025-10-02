# Implementation Brief: Streamlit “Composite Fundamentals” Web App

## 0) Goal (TL;DR for the model)
Build a **Streamlit** app that lets a user:
1) **Select symbols** (e.g., AAPL, MSFT, NVDA…).
2) **Create & save groups** of symbols (e.g., “Mag7”, “Semis”, “My Watchlist A”).  
3) **Choose fundamentals metrics** (P/S, EV/Sales, PEG, P/E, EV/EBITDA, P/B, EV/AUM, ROE, EV/EBIT, plus price & market cap).
4) **Compute a composite/rolling index** for a selected group (or show a single stock), using the rule:  
   **Composite Ratio = (∑ Numerators) / (∑ Denominators)** for additive accounting metrics, and **weighted averages** for rate-style metrics (e.g., ROE).  
5) **Chart & compare** the composite vs. time and optionally against benchmarks (e.g., S&P 500 P/S).  
6) Provide **downloadable CSV** of computed time series and **shareable group presets**.

Deliver production-grade code (clean architecture, caching, error handling, tests) that “just works” with default free sources and can **optionally** use premium APIs via adapters.

---

## 1) Tech Stack & Libraries
- **Python 3.11+**
- **Streamlit** for UI
- **Pandas**, **NumPy**, **pydantic** for data shaping/validation
- **yfinance** (free) for prices, shares outstanding, some fundamentals (ok for MVP)
- **yahooquery** as a fallback for fundamentals (if installed)
- **Adapters** for optional premium sources (FinancialModelingPrep, Alpha Vantage, Twelve Data, Polygon, FactSet). Implement interface but keep keys in `.env`
- **Requests/httpx** for API calls
- **Joblib** or **Streamlit cache (`st.cache_data` / `st.cache_resource`)** for caching
- **python-dotenv** for configuration
- **Plotting:** Streamlit built-ins + **plotly** for interactive charts
- **pytest** for unit tests
- **pyarrow** for faster parquet/caching (optional)

> Keep all external calls graceful: if a field is missing, surface a friendly UI warning and continue where possible.

---

## 2) Data Model & Composite Math (Important)
### 2.1 Core fields (TTM where possible)
- **Price** (daily close/adjusted close)
- **Shares Outstanding**
- **Market Cap** = Price × Shares Outstanding
- **Enterprise Value (EV)** = Market Cap + Total Debt − Cash & Equivalents
- **Revenue TTM**
- **EBITDA TTM**
- **EBIT TTM**
- **Net Income TTM**
- **Book Value (Total Equity)**
- **AUM** (only for asset managers; if N/A -> exclude from EV/AUM or flag)
- **EPS (TTM)**
- **Growth estimates** (for PEG; fallback to `NaN` if not available)

### 2.2 Ratios to compute per-symbol
- **P/S** = Market Cap / Revenue
- **EV/Sales** = EV / Revenue
- **P/E** = Price / EPS (or Market Cap / Net Income)
- **PEG** = P/E / GrowthRate (GrowthRate as % → decimal; if missing -> `NaN`)
- **EV/EBITDA** = EV / EBITDA
- **EV/EBIT** = EV / EBIT
- **P/B** = Market Cap / Book Value
- **EV/AUM** = EV / AUM
- **ROE** = Net Income / Book Value

### 2.3 **Composite rules** for a group basket
Use accounting-consistent aggregation:
- **Additive numerators & denominators**, then divide:
  - P/S, EV/Sales, EV/EBITDA, EV/EBIT, P/B, EV/AUM:  
    **Composite = (∑ Numerators across symbols) / (∑ Denominators)**  
    e.g., Composite P/S = (∑ MarketCap) / (∑ Revenue).
- **Rates** (ROE): use **Market Cap–weighted** (default) or **Equity-weighted** (toggle):
  - Composite ROE = ∑(Weightᵢ × ROEᵢ), Weightᵢ = MarketCapᵢ / ∑ MarketCap.
- **P/E**: prefer accounting identity: (∑ MarketCap) / (∑ Net Income).  
- **PEG**: define **Composite PEG** as Composite P/E divided by **cap‑weighted growth**. If growth is missing for too many symbols, flag and skip PEG.
- **Missing values**: Exclude symbol from that metric’s composite **only** if **denominator is missing or ≤ 0**; log a note in the UI.

### 2.4 Rolling / Historical series
- Allow **date range** and **frequency** (daily/weekly/monthly).  
- For each date, compute historical **Market Cap**, **EV**, etc.  
  - Historical Market Cap = AdjClose × **current** Shares Outstanding (MVP), with a toggle for “point‑in‑time shares” (future enhancement).  
  - **Revenue/EBITDA/EBIT/Equity/Net Income**: treat as **TTM** point series (step-forward quarterly updates). Forward-fill between report dates.  
  - EV history updates as price changes + last reported debt/cash.
- Offer **rolling windows** (e.g., 30/90/252 trading days) to smooth ratios.

---

## 3) UI/UX Requirements
- **Sidebar**
  - Multi-select symbols (free text input + suggestions)
  - **Groups**: create, rename, delete, save & load presets to `~/.streamlit_fundamentals/groups.json`
  - **Metric selector** (checkboxes): P/S, EV/Sales, PEG, P/E, EV/EBITDA, P/B, EV/AUM, ROE, EV/EBIT
  - Date range, frequency, rolling window
  - Benchmark toggle: S&P500 P/S (approx via SPY + fundamentals) or custom ticker group
  - Data source priority order (Yahoo → premium adapters)
  - Weighting mode for ROE (MCAP or Equity)
  - “Strict accounting mode”: drop symbols with negative denominators for a given metric
- **Main area**
  - **Tabs**: Overview | Charts | Table | Data Quality
  - **Overview**: badges for selected group, data coverage, last refresh, API usage
  - **Charts**: interactive plotly line charts for selected metrics (composite & benchmark). Tooltip with current value.
  - **Table**: per-symbol latest snapshot + composite row
  - **Data Quality**: what’s missing, what was forward-filled, which assumptions used
  - **Export buttons**: CSV of time series; PNG of charts (via plotly export)
- **Notifications**: Use `st.toast` / `st.info` for missing fields & fallbacks.

---

## 4) Architecture
```
app/
  ├─ app.py                      # Streamlit entrypoint
  ├─ core/
  │   ├─ models.py               # Pydantic models for SymbolFundamentals, TimeSeriesPoint, GroupConfig
  │   ├─ metrics.py              # All ratio/composite math (pure functions)
  │   ├─ adapters/
  │   │   ├─ base.py             # AbstractFundamentalsSource
  │   │   ├─ yahoo.py            # yfinance/yahooquery implementations
  │   │   ├─ fmp.py              # FinancialModelingPrep (optional)
  │   │   └─ alpha_vantage.py    # Optional
  │   ├─ repository.py           # Orchestrates fetch → normalize → cache
  │   └─ cache.py                # Thin wrapper around st.cache_data and local parquet
  ├─ ui/
  │   ├─ sidebar.py              # symbol selector, groups, options
  │   ├─ charts.py               # plotly chart builders
  │   ├─ tables.py               # styled dataframes
  │   └─ quality.py              # data-quality panel
  ├─ assets/
  │   └─ sample_groups.json
  ├─ tests/
  │   ├─ test_metrics.py
  │   ├─ test_repository.py
  │   └─ test_adapters.py
  ├─ .env.example
  ├─ requirements.txt
  └─ README.md
```

### 4.1 Adapter interface
```python
# Pseudocode interface (do not import this directly).
class AbstractFundamentalsSource(Protocol):
    def price_history(self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str) -> pd.DataFrame: ...
    def snapshot(self, symbol: str) -> dict:  # returns dict with keys in §2.1
        # Required keys (None allowed if missing):
        # price, shares_outstanding, total_debt, cash, revenue_ttm,
        # ebitda_ttm, ebit_ttm, net_income_ttm, equity_book, aum, eps_ttm,
        # growth_forward_1y  (decimal; 0.15 == 15%)
        ...
```

- `yahoo.py` fills from `yfinance.Ticker` and/or `yahooquery` with best-effort mapping.
- Normalize currencies where possible; otherwise warn when a group mixes currencies.

### 4.2 Metrics module
- **Pure functions**, vectorized where possible.  
- Unit tests for: P/S, EV/Sales, P/E, PEG, EV/EBITDA, P/B, EV/AUM, ROE, EV/EBIT, and composite rules.  
- Input contracts: raise `MetricsInputError` if denominator ≤ 0 (unless `strict=False` to skip).

### 4.3 Caching
- `@st.cache_data(ttl=3600)` for snapshots & histories. Cache key includes adapter + version.  
- Optional on-disk parquet cache under `~/.streamlit_fundamentals/cache`.  
- Invalidate cache when user hits “Refresh” in the UI.

---

## 5) Implementation Details & Edge Cases
- **Negative or tiny denominators** (e.g., negative EBITDA):  
  - If `strict mode` on → exclude from composite and annotate.
  - Else → compute but mark “non-standard” with a warning badge.
- **AUM missing** for EV/AUM → exclude symbol from that metric & warn.
- **PEG** when GrowthRate ≤ 0 or missing → mark as N/A (don’t divide by 0/negatives).
- **Currency**: If symbols come from different home currencies, still compute using reported fundamentals but display a **“mixed currency”** badge.
- **Outliers**: Add a user toggle to winsorize inputs at 1st/99th percentile for per-symbol rates before weighting.
- **Benchmarks**: For S&P 500 P/S (MVP) approximate using `SPY` market cap and `S&P500 aggregate revenue` (if available) or drop-in custom ticker group.
- **Time Alignment**: Resample to business days; forward-fill TTM fields between reports.
- **Persistence**: Save groups as JSON (list of symbols). Provide Import/Export buttons.

---

## 6) Streamlit Flow (pseudo)
```python
st.set_page_config(page_title="Composite Fundamentals", layout="wide")
with st.sidebar:
    symbols = st.multiselect("Symbols", options=load_universe(), default=["AAPL","MSFT","NVDA"])
    group_name = st.text_input("New group name")
    if st.button("Save group") and group_name:
        save_group(group_name, symbols)
    selected_group = st.selectbox("Load group", options=list_groups())
    metrics = st.multiselect("Metrics", ["P/S","EV/Sales","PEG","P/E","EV/EBITDA","P/B","EV/AUM","ROE","EV/EBIT"], ["P/S","EV/Sales"])
    start, end = st.date_input("Date range", value=(default_start(), pd.Timestamp.today()))
    freq = st.selectbox("Frequency", ["D","W","M"], index=0)
    roll = st.number_input("Rolling window (days)", min_value=1, value=30)
    strict = st.toggle("Strict accounting mode", value=True)
    refresh = st.button("Refresh data")

group_symbols = resolve_symbols(symbols, selected_group)
data = repo.fetch_timeseries(group_symbols, start, end, freq, refresh=refresh)
composite = metrics_engine.compute_composite_series(data, metrics, roll, strict=strict)

tab_overview, tab_charts, tab_table, tab_quality = st.tabs(["Overview","Charts","Table","Data Quality"])
with tab_charts:
    for metric in metrics:
        fig = charts.line(composite[metric], title=f"{selected_group or 'Custom'} — {metric}")
        st.plotly_chart(fig, use_container_width=True)

with tab_table:
    st.dataframe(tables.snapshot_table(data, composite))

st.download_button("Download CSV", composite.to_csv().encode(), file_name="composite_metrics.csv", mime="text/csv")
```
*(Provide real implementations with caching, error handling, and unit tests.)*

---

## 7) Testing & Quality
- **Unit tests** for:
  - Metric math on known fixtures
  - Composite rules (sum-over-sum; weights)
  - Adapter normalization & missing-field behavior
- **Type hints** everywhere; run `mypy` (optional)
- **CI hints**: pre-commit hooks for black/isort/ruff

---

## 8) Deliverables
1) `app/` project as above with working Streamlit app.
2) Clear **README** with setup steps:
   - `pip install -r requirements.txt`
   - `cp .env.example .env` (add keys if using premium APIs)
   - `streamlit run app/app.py`
3) **Sample groups** (Mag7, Semis)
4) **Tests passing**: `pytest -q`
5) **Screenshots** of app UI (optional)

---

## 9) Acceptance Criteria
- User can add symbols, save/load groups, pick metrics, pick date range, and see **interactive charts** of **composite metrics** for the group and any single stock.
- Composite math follows §2.3.
- Missing data handled gracefully with visible explanations.
- CSV export works. Groups persist on disk.
- Code is clean, modular, and documented.


## 10) Nice-to-haves (if time permits)
- Dockerfile
- Multi-currency normalization (FX conversion by date)
- Point-in-time shares outstanding (historical)
- Compare two groups on the same chart
- OAuth-backed cloud save of groups (e.g., Google Drive)

---

## 11) Quick Field Map for Yahoo (guidance; validate at runtime)
- **Price**: history (Adj Close)
- **Shares Outstanding**: `info["sharesOutstanding"]` or methods available
- **Total Debt**: from balance sheet (longTermDebt + shortLongTermDebt)
- **Cash & Equivalents**: `cashAndCashEquivalents`
- **Revenue TTM**: trailing financials totalRevenue
- **EBITDA TTM**: trailing `ebitda` (or calculate)
- **EBIT TTM**: trailing `ebit`
- **Net Income TTM**: trailing `netIncome`
- **Book Value (Equity)**: `totalStockholderEquity`
- **AUM**: often missing; adapter optional field
- **EPS TTM**: `trailingEps`
- **Growth**: analyst estimates; may be sparse

Implement robust null-checks and surface clarity in Data Quality tab.
