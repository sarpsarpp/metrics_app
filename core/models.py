"""
Data models for fundamentals and time series.
"""
from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import pandas as pd


class SymbolSnapshot(BaseModel):
    """Single point-in-time fundamentals snapshot for a symbol."""
    symbol: str
    timestamp: datetime

    # Price and market data
    price: Optional[float] = None
    shares_outstanding: Optional[float] = None
    market_cap: Optional[float] = None

    # Balance sheet items
    total_debt: Optional[float] = None
    cash: Optional[float] = None
    equity_book: Optional[float] = None
    aum: Optional[float] = None  # For asset managers

    # Income statement (TTM)
    revenue_ttm: Optional[float] = None
    ebitda_ttm: Optional[float] = None
    ebit_ttm: Optional[float] = None
    net_income_ttm: Optional[float] = None
    eps_ttm: Optional[float] = None

    # Growth estimates
    growth_forward_1y: Optional[float] = None  # As decimal (0.15 = 15%)

    # Currency
    currency: str = "USD"

    # Data quality
    warnings: List[str] = Field(default_factory=list)

    @field_validator('shares_outstanding', 'total_debt', 'cash', 'equity_book',
                     'revenue_ttm', 'ebitda_ttm', 'ebit_ttm', 'net_income_ttm')
    @classmethod
    def check_negative_denominators(cls, v, info):
        """Warn about negative values that could affect ratios."""
        if v is not None and v < 0:
            return v  # Allow but caller should check warnings
        return v

    def compute_enterprise_value(self) -> Optional[float]:
        """Compute EV = Market Cap + Total Debt - Cash."""
        import pandas as pd
        import numpy as np

        # Handle NaN values
        if self.market_cap is None or (isinstance(self.market_cap, float) and np.isnan(self.market_cap)):
            return None

        # Treat None/NaN as 0 for debt and cash
        debt = 0.0
        if self.total_debt is not None and not (isinstance(self.total_debt, float) and np.isnan(self.total_debt)):
            debt = self.total_debt

        cash = 0.0
        if self.cash is not None and not (isinstance(self.cash, float) and np.isnan(self.cash)):
            cash = self.cash

        return self.market_cap + debt - cash


class TimeSeriesPoint(BaseModel):
    """A single point in a time series with computed ratios."""
    timestamp: datetime
    symbol: str

    # Raw values
    price: Optional[float] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None

    # Computed ratios
    ps_ratio: Optional[float] = None
    ev_sales: Optional[float] = None
    pe_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ev_ebit: Optional[float] = None
    pb_ratio: Optional[float] = None
    ev_aum: Optional[float] = None
    roe: Optional[float] = None

    warnings: List[str] = Field(default_factory=list)


class CompositeTimeSeriesPoint(BaseModel):
    """Composite metrics for a group at a point in time."""
    timestamp: datetime

    # Composite ratios
    ps_ratio: Optional[float] = None
    ev_sales: Optional[float] = None
    pe_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ev_ebit: Optional[float] = None
    pb_ratio: Optional[float] = None
    ev_aum: Optional[float] = None
    roe: Optional[float] = None

    # Aggregated denominators for reference
    total_market_cap: Optional[float] = None
    total_revenue: Optional[float] = None
    total_equity: Optional[float] = None

    # Metadata
    symbols_included: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class GroupConfig(BaseModel):
    """Configuration for a saved symbol group."""
    name: str
    symbols: List[str]
    created_at: datetime = Field(default_factory=datetime.now)
    description: Optional[str] = None

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v):
        """Ensure symbols are uppercase and unique."""
        return list(set(s.upper().strip() for s in v if s.strip()))


class DataQualityReport(BaseModel):
    """Report on data quality and missing fields."""
    symbols_analyzed: List[str]
    timestamp: datetime

    missing_fields: Dict[str, List[str]] = Field(default_factory=dict)  # symbol -> list of missing fields
    negative_denominators: Dict[str, List[str]] = Field(default_factory=dict)  # symbol -> list of negative fields
    forward_filled_dates: Dict[str, List[datetime]] = Field(default_factory=dict)  # symbol -> dates forward-filled
    currency_warnings: List[str] = Field(default_factory=list)
    excluded_from_metrics: Dict[str, List[str]] = Field(default_factory=dict)  # metric -> symbols excluded

    def add_missing_field(self, symbol: str, field: str):
        """Record a missing field for a symbol."""
        if symbol not in self.missing_fields:
            self.missing_fields[symbol] = []
        if field not in self.missing_fields[symbol]:
            self.missing_fields[symbol].append(field)

    def add_negative_denominator(self, symbol: str, field: str):
        """Record a negative denominator."""
        if symbol not in self.negative_denominators:
            self.negative_denominators[symbol] = []
        if field not in self.negative_denominators[symbol]:
            self.negative_denominators[symbol].append(field)

    def add_excluded_symbol(self, metric: str, symbol: str):
        """Record a symbol excluded from a metric calculation."""
        if metric not in self.excluded_from_metrics:
            self.excluded_from_metrics[metric] = []
        if symbol not in self.excluded_from_metrics[metric]:
            self.excluded_from_metrics[metric].append(symbol)
