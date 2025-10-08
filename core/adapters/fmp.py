"""
Financial Modeling Prep adapter (premium, optional).
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


class FinancialModelingPrepAdapter:
    """Adapter for Financial Modeling Prep API."""

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        if not self.api_key:
            logger.warning("FMP_API_KEY not set. FMP adapter will not work.")

    def price_history(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch price history from FMP."""
        if not self.api_key:
            raise DataSourceError("FMP API key not configured")

        # FMP uses different endpoint for historical prices
        # Placeholder implementation
        logger.info(f"FMP price_history not fully implemented for {symbol}")
        return pd.DataFrame()

    def snapshot(self, symbol: str) -> Dict[str, Optional[float]]:
        """Fetch current fundamentals snapshot from FMP."""
        if not self.api_key:
            raise DataSourceError("FMP API key not configured")

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
            # Get quote
            quote_url = f"{self.BASE_URL}/quote/{symbol}"
            quote_resp = requests.get(quote_url, params={"apikey": self.api_key}, timeout=10)
            quote_resp.raise_for_status()
            quote_data = quote_resp.json()

            if quote_data and len(quote_data) > 0:
                quote = quote_data[0]
                result['price'] = quote.get('price')
                result['shares_outstanding'] = quote.get('sharesOutstanding')
                result['eps_ttm'] = quote.get('eps')

            # Get key metrics TTM
            metrics_url = f"{self.BASE_URL}/key-metrics-ttm/{symbol}"
            metrics_resp = requests.get(metrics_url, params={"apikey": self.api_key}, timeout=10)
            metrics_resp.raise_for_status()
            metrics_data = metrics_resp.json()

            if metrics_data and len(metrics_data) > 0:
                metrics = metrics_data[0]
                result['revenue_ttm'] = metrics.get('reventueTTM')
                result['net_income_ttm'] = metrics.get('netIncomeTTM')
                result['equity_book'] = metrics.get('stockholdersEquityTTM')

            # Additional fields would require more API calls
            # This is a basic implementation

        except Exception as e:
            logger.error(f"Error fetching FMP snapshot for {symbol}: {e}")

        return result

    def historical_fundamentals(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        frequency: str = "Q"
    ) -> pd.DataFrame:
        """Fetch historical fundamentals from FMP."""
        if not self.api_key:
            raise DataSourceError("FMP API key not configured")

        # Placeholder implementation
        logger.info(f"FMP historical_fundamentals not fully implemented for {symbol}")
        return pd.DataFrame()
