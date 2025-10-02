"""
Alpha Vantage adapter (premium, optional).
Placeholder implementation - requires API key.
"""
from typing import Dict, Optional
import pandas as pd
import requests
import os
from datetime import datetime
import logging

from .base import DataSourceError

logger = logging.getLogger(__name__)


class AlphaVantageAdapter:
    """Adapter for Alpha Vantage API."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            logger.warning("ALPHA_VANTAGE_API_KEY not set. Alpha Vantage adapter will not work.")

    def price_history(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch price history from Alpha Vantage."""
        if not self.api_key:
            raise DataSourceError("Alpha Vantage API key not configured")

        # Placeholder implementation
        logger.info(f"Alpha Vantage price_history not fully implemented for {symbol}")
        return pd.DataFrame()

    def snapshot(self, symbol: str) -> Dict[str, Optional[float]]:
        """Fetch current fundamentals snapshot from Alpha Vantage."""
        if not self.api_key:
            raise DataSourceError("Alpha Vantage API key not configured")

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
            # Get company overview
            params = {
                "function": "OVERVIEW",
                "symbol": symbol,
                "apikey": self.api_key
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data:
                result['shares_outstanding'] = self._safe_float(data.get('SharesOutstanding'))
                result['eps_ttm'] = self._safe_float(data.get('TrailingPE'))  # Note: might need to derive EPS
                result['equity_book'] = self._safe_float(data.get('BookValue'))

            # Get quote for current price
            quote_params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key
            }
            quote_resp = requests.get(self.BASE_URL, params=quote_params, timeout=10)
            quote_resp.raise_for_status()
            quote_data = quote_resp.json()

            if "Global Quote" in quote_data:
                result['price'] = self._safe_float(quote_data["Global Quote"].get("05. price"))

        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage snapshot for {symbol}: {e}")

        return result

    def historical_fundamentals(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        frequency: str = "Q"
    ) -> pd.DataFrame:
        """Fetch historical fundamentals from Alpha Vantage."""
        if not self.api_key:
            raise DataSourceError("Alpha Vantage API key not configured")

        # Placeholder implementation
        logger.info(f"Alpha Vantage historical_fundamentals not fully implemented for {symbol}")
        return pd.DataFrame()

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        """Safely convert to float."""
        if val is None or val == 'None':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
