"""
Yahoo Finance adapter using yfinance and yahooquery.
"""
from typing import Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import logging

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from yahooquery import Ticker as YQTicker
    YAHOOQUERY_AVAILABLE = True
except ImportError:
    YAHOOQUERY_AVAILABLE = False

from .base import DataSourceError

logger = logging.getLogger(__name__)


class YahooFinanceAdapter:
    """Adapter for Yahoo Finance using yfinance and yahooquery."""

    def __init__(self):
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance is required. Install with: pip install yfinance")

    def price_history(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch price history from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end, interval=interval)

            if df.empty:
                logger.warning(f"No price data found for {symbol}")
                return pd.DataFrame()

            # Ensure Adj Close exists
            if 'Close' in df.columns and 'Adj Close' not in df.columns:
                df['Adj Close'] = df['Close']

            return df

        except Exception as e:
            logger.error(f"Error fetching price history for {symbol}: {e}")
            raise DataSourceError(f"Failed to fetch price data for {symbol}: {e}")

    def snapshot(self, symbol: str) -> Dict[str, Optional[float]]:
        """Fetch current fundamentals snapshot."""
        result = {
            'price': None,
            'shares_outstanding': None,
            'total_debt': None,
            'cash': None,
            'revenue_ttm': None,
            'ebitda_ttm': None,
            'ebit_ttm': None,
            'net_income_ttm': None,
            'equity_book': None,
            'aum': None,
            'eps_ttm': None,
            'growth_forward_1y': None,
            'currency': 'USD'
        }

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Price and shares
            result['price'] = self._safe_get(info, 'currentPrice') or self._safe_get(info, 'regularMarketPrice')
            result['shares_outstanding'] = self._safe_get(info, 'sharesOutstanding')

            # Currency
            result['currency'] = info.get('currency', 'USD')

            # EPS
            result['eps_ttm'] = self._safe_get(info, 'trailingEps')

            # Growth estimate
            result['growth_forward_1y'] = self._safe_get(info, 'earningsGrowth')

            # Try to get balance sheet data
            try:
                balance_sheet = ticker.balance_sheet
                if not balance_sheet.empty:
                    # Most recent column (latest data)
                    latest = balance_sheet.iloc[:, 0]

                    # Total debt
                    long_term_debt = latest.get('Long Term Debt', 0) or 0
                    short_term_debt = latest.get('Current Debt', 0) or 0
                    result['total_debt'] = long_term_debt + short_term_debt if (long_term_debt or short_term_debt) else None

                    # Cash
                    result['cash'] = latest.get('Cash And Cash Equivalents')

                    # Book value / equity
                    result['equity_book'] = latest.get('Total Stockholder Equity') or latest.get('Stockholders Equity')

            except Exception as e:
                logger.debug(f"Could not fetch balance sheet for {symbol}: {e}")

            # Try to get income statement data
            try:
                financials = ticker.financials
                if not financials.empty:
                    latest = financials.iloc[:, 0]

                    result['revenue_ttm'] = latest.get('Total Revenue')
                    result['net_income_ttm'] = latest.get('Net Income')
                    result['ebitda_ttm'] = latest.get('EBITDA')
                    result['ebit_ttm'] = latest.get('EBIT')

            except Exception as e:
                logger.debug(f"Could not fetch financials for {symbol}: {e}")

            # Try to get quarterly data for TTM calculations
            try:
                quarterly_financials = ticker.quarterly_financials
                if not quarterly_financials.empty and len(quarterly_financials.columns) >= 4:
                    # Sum last 4 quarters for TTM
                    last_4q = quarterly_financials.iloc[:, :4]

                    if 'Total Revenue' in last_4q.index:
                        ttm_revenue = last_4q.loc['Total Revenue'].sum()
                        if pd.notna(ttm_revenue) and ttm_revenue != 0:
                            result['revenue_ttm'] = ttm_revenue

                    if 'Net Income' in last_4q.index:
                        ttm_ni = last_4q.loc['Net Income'].sum()
                        if pd.notna(ttm_ni):
                            result['net_income_ttm'] = ttm_ni

                    if 'EBITDA' in last_4q.index:
                        ttm_ebitda = last_4q.loc['EBITDA'].sum()
                        if pd.notna(ttm_ebitda):
                            result['ebitda_ttm'] = ttm_ebitda

                    if 'EBIT' in last_4q.index:
                        ttm_ebit = last_4q.loc['EBIT'].sum()
                        if pd.notna(ttm_ebit):
                            result['ebit_ttm'] = ttm_ebit

            except Exception as e:
                logger.debug(f"Could not calculate TTM from quarterly data for {symbol}: {e}")

            # Fallback: try yahooquery if available and key fields are missing
            if YAHOOQUERY_AVAILABLE and result['revenue_ttm'] is None:
                try:
                    yq_ticker = YQTicker(symbol)
                    summary = yq_ticker.summary_detail.get(symbol, {})
                    financials_yq = yq_ticker.financial_data.get(symbol, {})

                    if isinstance(financials_yq, dict):
                        result['revenue_ttm'] = result['revenue_ttm'] or financials_yq.get('totalRevenue')
                        result['ebitda_ttm'] = result['ebitda_ttm'] or financials_yq.get('ebitda')

                except Exception as e:
                    logger.debug(f"yahooquery fallback failed for {symbol}: {e}")

        except Exception as e:
            logger.error(f"Error fetching snapshot for {symbol}: {e}")
            # Return partial data rather than failing completely

        return result

    def historical_fundamentals(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        frequency: str = "Q"
    ) -> pd.DataFrame:
        """
        Fetch historical fundamentals.
        Note: Yahoo Finance has limited historical fundamentals.
        Returns quarterly or annual financials available.
        """
        try:
            ticker = yf.Ticker(symbol)

            if frequency == "Q":
                financials = ticker.quarterly_financials
                balance_sheet = ticker.quarterly_balance_sheet
            else:
                financials = ticker.financials
                balance_sheet = ticker.balance_sheet

            # Combine financials and balance sheet
            result_df = pd.DataFrame()

            if not financials.empty:
                # Transpose so dates are rows
                fin_t = financials.T
                result_df = fin_t.copy()

            if not balance_sheet.empty:
                bs_t = balance_sheet.T
                if result_df.empty:
                    result_df = bs_t
                else:
                    # Merge on index (dates)
                    result_df = result_df.join(bs_t, how='outer')

            # Filter by date range
            if not result_df.empty:
                result_df.index = pd.to_datetime(result_df.index)
                result_df = result_df.sort_index()
                result_df = result_df[(result_df.index >= start) & (result_df.index <= end)]

            return result_df

        except Exception as e:
            logger.error(f"Error fetching historical fundamentals for {symbol}: {e}")
            return pd.DataFrame()

    @staticmethod
    def _safe_get(d: dict, key: str) -> Optional[float]:
        """Safely get a numeric value from a dict."""
        val = d.get(key)
        if val is None or val == 'N/A':
            return None
        try:
            val_float = float(val)
            # Check for NaN or inf
            if np.isnan(val_float) or np.isinf(val_float):
                return None
            return val_float
        except (ValueError, TypeError):
            return None
