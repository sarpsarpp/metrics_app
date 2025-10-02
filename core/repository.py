"""
Repository for orchestrating data fetching, caching, and metric computation.
"""
from typing import List, Dict, Optional, Tuple
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import logging

from .models import SymbolSnapshot, DataQualityReport, CompositeTimeSeriesPoint
from .adapters.yahoo import YahooFinanceAdapter
from .adapters.fmp import FinancialModelingPrepAdapter
from .adapters.alpha_vantage import AlphaVantageAdapter
from .cache import get_cache_manager
from . import metrics

logger = logging.getLogger(__name__)


class FundamentalsRepository:
    """
    Central repository for fetching and caching fundamentals data.
    Orchestrates adapters, caching, and metric computation.
    """

    def __init__(self, primary_adapter: str = "yahoo"):
        """
        Initialize repository with specified primary adapter.

        Args:
            primary_adapter: Primary data source ("yahoo", "fmp", "alpha_vantage")
        """
        self.cache_manager = get_cache_manager()
        self.primary_adapter_name = primary_adapter
        self._init_adapters()

    def _init_adapters(self):
        """Initialize available adapters."""
        self.adapters = {}

        try:
            self.adapters['yahoo'] = YahooFinanceAdapter()
            logger.info("Yahoo Finance adapter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Yahoo adapter: {e}")

        try:
            self.adapters['fmp'] = FinancialModelingPrepAdapter()
            logger.info("FMP adapter initialized (may not be configured)")
        except Exception as e:
            logger.debug(f"FMP adapter not available: {e}")

        try:
            self.adapters['alpha_vantage'] = AlphaVantageAdapter()
            logger.info("Alpha Vantage adapter initialized (may not be configured)")
        except Exception as e:
            logger.debug(f"Alpha Vantage adapter not available: {e}")

    def get_adapter(self, name: Optional[str] = None):
        """Get adapter by name, falling back to primary."""
        adapter_name = name or self.primary_adapter_name
        return self.adapters.get(adapter_name, self.adapters.get('yahoo'))

    @st.cache_data(ttl=3600, show_spinner="Fetching price data...")
    def fetch_price_history(_self, symbol: str, start: pd.Timestamp, end: pd.Timestamp,
                           interval: str = "1d", adapter_name: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch price history with caching.

        Args:
            symbol: Stock ticker
            start: Start date
            end: End date
            interval: Data interval
            adapter_name: Data source adapter name

        Returns:
            DataFrame with price history
        """
        adapter = _self.get_adapter(adapter_name)

        try:
            df = adapter.price_history(symbol, start, end, interval)
            return df
        except Exception as e:
            logger.error(f"Error fetching price history for {symbol}: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=3600, show_spinner="Fetching fundamentals...")
    def fetch_snapshot(_self, symbol: str, adapter_name: Optional[str] = None) -> Dict:
        """
        Fetch current fundamentals snapshot with caching.

        Args:
            symbol: Stock ticker
            adapter_name: Data source adapter name

        Returns:
            Dictionary with fundamentals data
        """
        adapter = _self.get_adapter(adapter_name)

        try:
            snapshot = adapter.snapshot(symbol)
            return snapshot
        except Exception as e:
            logger.error(f"Error fetching snapshot for {symbol}: {e}")
            return {}

    def build_symbol_snapshot(self, symbol: str, timestamp: datetime,
                            adapter_name: Optional[str] = None) -> SymbolSnapshot:
        """
        Build a SymbolSnapshot object for a symbol at a point in time.

        Args:
            symbol: Stock ticker
            timestamp: Timestamp for snapshot
            adapter_name: Data source adapter

        Returns:
            SymbolSnapshot object
        """
        data = self.fetch_snapshot(symbol, adapter_name)

        # Calculate market cap if not provided
        market_cap = data.get('market_cap')
        if market_cap is None and data.get('price') and data.get('shares_outstanding'):
            market_cap = data['price'] * data['shares_outstanding']

        snapshot = SymbolSnapshot(
            symbol=symbol,
            timestamp=timestamp,
            price=data.get('price'),
            shares_outstanding=data.get('shares_outstanding'),
            market_cap=market_cap,
            total_debt=data.get('total_debt'),
            cash=data.get('cash'),
            equity_book=data.get('equity_book'),
            aum=data.get('aum'),
            revenue_ttm=data.get('revenue_ttm'),
            ebitda_ttm=data.get('ebitda_ttm'),
            ebit_ttm=data.get('ebit_ttm'),
            net_income_ttm=data.get('net_income_ttm'),
            eps_ttm=data.get('eps_ttm'),
            growth_forward_1y=data.get('growth_forward_1y'),
            currency=data.get('currency', 'USD')
        )

        # Add warnings for missing critical fields
        if snapshot.price is None:
            snapshot.warnings.append("Missing price data")
        if snapshot.shares_outstanding is None:
            snapshot.warnings.append("Missing shares outstanding")
        if snapshot.revenue_ttm is None:
            snapshot.warnings.append("Missing revenue data")

        return snapshot

    def build_time_series(
        self,
        symbols: List[str],
        start: pd.Timestamp,
        end: pd.Timestamp,
        interval: str = "1d",
        adapter_name: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Build time series of snapshots for multiple symbols.

        Args:
            symbols: List of stock tickers
            start: Start date
            end: End date
            interval: Data interval
            adapter_name: Data source adapter

        Returns:
            Dict mapping symbol to DataFrame with time series
        """
        result = {}

        for symbol in symbols:
            try:
                # Get price history
                price_df = self.fetch_price_history(symbol, start, end, interval, adapter_name)

                if price_df.empty:
                    logger.warning(f"No price data for {symbol}")
                    continue

                # Get current snapshot for fundamentals
                snapshot_data = self.fetch_snapshot(symbol, adapter_name)

                # Build time series DataFrame
                ts_df = price_df.copy()
                ts_df['symbol'] = symbol

                # Add shares outstanding (assume constant for MVP)
                shares = snapshot_data.get('shares_outstanding')
                ts_df['shares_outstanding'] = shares

                # Calculate market cap using Adj Close
                if 'Adj Close' in ts_df.columns and shares:
                    ts_df['market_cap'] = ts_df['Adj Close'] * shares
                else:
                    ts_df['market_cap'] = None

                # Add fundamentals (will be forward-filled)
                for field in ['total_debt', 'cash', 'revenue_ttm', 'ebitda_ttm', 'ebit_ttm',
                             'net_income_ttm', 'equity_book', 'aum', 'eps_ttm']:
                    ts_df[field] = snapshot_data.get(field)

                # Forward-fill fundamentals
                fundamental_cols = ['revenue_ttm', 'ebitda_ttm', 'ebit_ttm', 'net_income_ttm',
                                  'equity_book', 'total_debt', 'cash', 'aum']
                ts_df = metrics.forward_fill_fundamentals(ts_df, fundamental_cols)

                # Calculate enterprise value
                if 'market_cap' in ts_df.columns:
                    ts_df['enterprise_value'] = (
                        ts_df['market_cap'] +
                        ts_df['total_debt'].fillna(0) -
                        ts_df['cash'].fillna(0)
                    )

                result[symbol] = ts_df

            except Exception as e:
                logger.error(f"Error building time series for {symbol}: {e}")
                continue

        return result

    def compute_composite_series(
        self,
        symbols: List[str],
        start: pd.Timestamp,
        end: pd.Timestamp,
        selected_metrics: List[str],
        interval: str = "1d",
        rolling_window: int = 1,
        strict_mode: bool = True,
        roe_weighting: str = "market_cap",
        adapter_name: Optional[str] = None
    ) -> Tuple[pd.DataFrame, DataQualityReport]:
        """
        Compute composite metrics time series for a group of symbols.

        Args:
            symbols: List of stock tickers
            start: Start date
            end: End date
            selected_metrics: List of metrics to compute
            interval: Data interval
            rolling_window: Window for rolling average (days)
            strict_mode: Exclude negative denominators
            roe_weighting: Weighting mode for ROE ('market_cap' or 'equity')
            adapter_name: Data source adapter

        Returns:
            Tuple of (composite DataFrame, DataQualityReport)
        """
        # Build time series for all symbols
        symbol_series = self.build_time_series(symbols, start, end, interval, adapter_name)

        if not symbol_series:
            return pd.DataFrame(), DataQualityReport(
                symbols_analyzed=symbols,
                timestamp=datetime.now()
            )

        # Get common date index
        all_dates = set()
        for df in symbol_series.values():
            all_dates.update(df.index)
        date_index = sorted(all_dates)

        # Initialize quality report
        quality_report = DataQualityReport(
            symbols_analyzed=symbols,
            timestamp=datetime.now()
        )

        # Compute composite for each date
        composite_data = []

        for date in date_index:
            # Build snapshots for this date
            snapshots = []
            for symbol, df in symbol_series.items():
                if date not in df.index:
                    continue

                row = df.loc[date]
                snapshot = SymbolSnapshot(
                    symbol=symbol,
                    timestamp=date,
                    price=row.get('Adj Close'),
                    shares_outstanding=row.get('shares_outstanding'),
                    market_cap=row.get('market_cap'),
                    total_debt=row.get('total_debt'),
                    cash=row.get('cash'),
                    revenue_ttm=row.get('revenue_ttm'),
                    ebitda_ttm=row.get('ebitda_ttm'),
                    ebit_ttm=row.get('ebit_ttm'),
                    net_income_ttm=row.get('net_income_ttm'),
                    equity_book=row.get('equity_book'),
                    aum=row.get('aum'),
                    eps_ttm=row.get('eps_ttm'),
                    currency='USD'
                )
                snapshots.append(snapshot)

            if not snapshots:
                continue

            # Compute composite metrics
            composite_point = {'timestamp': date}

            metric_map = {
                'P/S': lambda: metrics.compute_composite_ps(snapshots, strict_mode, quality_report),
                'EV/Sales': lambda: metrics.compute_composite_ev_sales(snapshots, strict_mode, quality_report),
                'P/E': lambda: metrics.compute_composite_pe(snapshots, strict_mode, quality_report),
                'PEG': lambda: metrics.compute_composite_peg(snapshots, strict_mode, quality_report),
                'EV/EBITDA': lambda: metrics.compute_composite_ev_ebitda(snapshots, strict_mode, quality_report),
                'EV/EBIT': lambda: metrics.compute_composite_ev_ebit(snapshots, strict_mode, quality_report),
                'P/B': lambda: metrics.compute_composite_pb(snapshots, strict_mode, quality_report),
                'EV/AUM': lambda: metrics.compute_composite_ev_aum(snapshots, strict_mode, quality_report),
                'ROE': lambda: metrics.compute_composite_roe(snapshots, roe_weighting, strict_mode, quality_report)
            }

            for metric_name in selected_metrics:
                if metric_name in metric_map:
                    value, included, warnings = metric_map[metric_name]()
                    composite_point[metric_name] = value

            composite_data.append(composite_point)

        # Build result DataFrame
        composite_df = pd.DataFrame(composite_data)
        if not composite_df.empty:
            composite_df.set_index('timestamp', inplace=True)
            composite_df.sort_index(inplace=True)

            # Apply rolling window if > 1
            if rolling_window > 1:
                for col in composite_df.columns:
                    composite_df[f"{col}_ma"] = composite_df[col].rolling(
                        window=rolling_window, min_periods=1
                    ).mean()

        return composite_df, quality_report

    def compute_per_symbol_metrics(
        self,
        symbols: List[str],
        selected_metrics: List[str],
        strict_mode: bool = True,
        adapter_name: Optional[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute individual metrics for each symbol (latest snapshot).

        Args:
            symbols: List of stock tickers
            selected_metrics: List of metrics to compute
            strict_mode: Exclude negative denominators
            adapter_name: Data source adapter

        Returns:
            Dict mapping symbol -> dict of metric values
        """
        result = {}

        for symbol in symbols:
            try:
                # Build snapshot for current date
                snapshot = self.build_symbol_snapshot(
                    symbol,
                    datetime.now(),
                    adapter_name
                )

                # Calculate all metrics for this symbol
                symbol_metrics = {
                    'price': snapshot.price,
                    'market_cap': snapshot.market_cap,
                }

                # Calculate each requested metric
                if 'P/S' in selected_metrics:
                    symbol_metrics['p_s'] = metrics.compute_ps_ratio(
                        snapshot.market_cap,
                        snapshot.revenue_ttm,
                        strict_mode
                    )

                if 'EV/Sales' in selected_metrics:
                    ev = snapshot.compute_enterprise_value()
                    symbol_metrics['ev_sales'] = metrics.compute_ev_sales(
                        ev,
                        snapshot.revenue_ttm,
                        strict_mode
                    )

                if 'P/E' in selected_metrics:
                    symbol_metrics['p_e'] = metrics.compute_pe_ratio(
                        snapshot.market_cap,
                        snapshot.net_income_ttm,
                        strict_mode
                    )

                if 'PEG' in selected_metrics:
                    pe = metrics.compute_pe_ratio(
                        snapshot.market_cap,
                        snapshot.net_income_ttm,
                        strict_mode
                    )
                    symbol_metrics['peg'] = metrics.compute_peg_ratio(
                        pe,
                        snapshot.growth_forward_1y,
                        strict_mode
                    )

                if 'EV/EBITDA' in selected_metrics:
                    ev = snapshot.compute_enterprise_value()
                    symbol_metrics['ev_ebitda'] = metrics.compute_ev_ebitda(
                        ev,
                        snapshot.ebitda_ttm,
                        strict_mode
                    )

                if 'EV/EBIT' in selected_metrics:
                    ev = snapshot.compute_enterprise_value()
                    symbol_metrics['ev_ebit'] = metrics.compute_ev_ebit(
                        ev,
                        snapshot.ebit_ttm,
                        strict_mode
                    )

                if 'P/B' in selected_metrics:
                    symbol_metrics['p_b'] = metrics.compute_pb_ratio(
                        snapshot.market_cap,
                        snapshot.equity_book,
                        strict_mode
                    )

                if 'EV/AUM' in selected_metrics:
                    ev = snapshot.compute_enterprise_value()
                    symbol_metrics['ev_aum'] = metrics.compute_ev_aum(
                        ev,
                        snapshot.aum,
                        strict_mode
                    )

                if 'ROE' in selected_metrics:
                    symbol_metrics['roe'] = metrics.compute_roe(
                        snapshot.net_income_ttm,
                        snapshot.equity_book,
                        strict_mode
                    )

                result[symbol] = symbol_metrics

            except Exception as e:
                logger.error(f"Error computing metrics for {symbol}: {e}")
                continue

        return result

    def clear_cache(self):
        """Clear all cached data."""
        st.cache_data.clear()
        self.cache_manager.clear_cache()
        logger.info("All caches cleared")
