"""
Base protocol for fundamentals data sources.
"""
from typing import Protocol, Dict, Optional
import pandas as pd
from datetime import datetime


class AbstractFundamentalsSource(Protocol):
    """Protocol for fundamentals data sources."""

    def price_history(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch price history for a symbol.

        Args:
            symbol: Stock ticker symbol
            start: Start date
            end: End date
            interval: Data interval (1d, 1wk, 1mo)

        Returns:
            DataFrame with columns: Date (index), Open, High, Low, Close, Adj Close, Volume
        """
        ...

    def snapshot(self, symbol: str) -> Dict[str, Optional[float]]:
        """
        Fetch current fundamentals snapshot for a symbol.

        Returns dict with keys:
        - price: Current price
        - shares_outstanding: Shares outstanding
        - total_debt: Total debt
        - cash: Cash and equivalents
        - revenue_ttm: Trailing twelve months revenue
        - ebitda_ttm: TTM EBITDA
        - ebit_ttm: TTM EBIT
        - net_income_ttm: TTM net income
        - equity_book: Book value / total equity
        - aum: Assets under management (for asset managers)
        - eps_ttm: Earnings per share TTM
        - growth_forward_1y: Forward 1-year growth estimate (as decimal, e.g., 0.15 = 15%)
        - currency: Currency code (e.g., 'USD')

        All values may be None if not available.
        """
        ...

    def historical_fundamentals(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        frequency: str = "Q"  # Q=quarterly, A=annual
    ) -> pd.DataFrame:
        """
        Fetch historical fundamentals for a symbol.

        Returns:
            DataFrame with Date index and columns for fundamentals metrics.
            Should include same fields as snapshot() where available.
        """
        ...


class DataSourceError(Exception):
    """Raised when data source encounters an error."""
    pass
