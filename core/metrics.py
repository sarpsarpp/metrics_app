"""
Pure functions for computing fundamentals ratios and composite metrics.
All functions are vectorized where possible and handle missing/invalid data gracefully.
"""
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from .models import SymbolSnapshot, CompositeTimeSeriesPoint, DataQualityReport


class MetricsInputError(ValueError):
    """Raised when metric inputs are invalid."""
    pass


# ==============================================================================
# Per-Symbol Ratio Calculations
# ==============================================================================

def compute_ps_ratio(market_cap: float, revenue: float, strict: bool = True) -> Optional[float]:
    """Compute Price-to-Sales ratio."""
    if revenue is None or (strict and revenue <= 0):
        return None
    if market_cap is None:
        return None
    if revenue == 0:
        return None
    return market_cap / revenue


def compute_ev_sales(enterprise_value: float, revenue: float, strict: bool = True) -> Optional[float]:
    """Compute EV/Sales ratio."""
    if revenue is None or (strict and revenue <= 0):
        return None
    if enterprise_value is None:
        return None
    if revenue == 0:
        return None
    return enterprise_value / revenue


def compute_pe_ratio(market_cap: float, net_income: float, strict: bool = True) -> Optional[float]:
    """Compute Price-to-Earnings ratio."""
    if net_income is None or (strict and net_income <= 0):
        return None
    if market_cap is None:
        return None
    if net_income == 0:
        return None
    return market_cap / net_income


def compute_peg_ratio(pe_ratio: float, growth_rate: float, strict: bool = True) -> Optional[float]:
    """Compute PEG ratio = P/E / growth_rate (growth as decimal, e.g. 0.15 for 15%)."""
    if pe_ratio is None or growth_rate is None:
        return None
    if growth_rate <= 0:  # PEG not meaningful for negative/zero growth
        return None
    # Convert growth to percentage if needed
    growth_pct = growth_rate * 100 if growth_rate < 1 else growth_rate
    if growth_pct == 0:
        return None
    return pe_ratio / growth_pct


def compute_ev_ebitda(enterprise_value: float, ebitda: float, strict: bool = True) -> Optional[float]:
    """Compute EV/EBITDA ratio."""
    if ebitda is None or (strict and ebitda <= 0):
        return None
    if enterprise_value is None:
        return None
    if ebitda == 0:
        return None
    return enterprise_value / ebitda


def compute_ev_ebit(enterprise_value: float, ebit: float, strict: bool = True) -> Optional[float]:
    """Compute EV/EBIT ratio."""
    if ebit is None or (strict and ebit <= 0):
        return None
    if enterprise_value is None:
        return None
    if ebit == 0:
        return None
    return enterprise_value / ebit


def compute_pb_ratio(market_cap: float, book_value: float, strict: bool = True) -> Optional[float]:
    """Compute Price-to-Book ratio."""
    if book_value is None or (strict and book_value <= 0):
        return None
    if market_cap is None:
        return None
    if book_value == 0:
        return None
    return market_cap / book_value


def compute_ev_aum(enterprise_value: float, aum: float, strict: bool = True) -> Optional[float]:
    """Compute EV/AUM ratio (for asset managers)."""
    if aum is None or (strict and aum <= 0):
        return None
    if enterprise_value is None:
        return None
    if aum == 0:
        return None
    return enterprise_value / aum


def compute_roe(net_income: float, book_value: float, strict: bool = True) -> Optional[float]:
    """Compute Return on Equity."""
    if book_value is None or (strict and book_value <= 0):
        return None
    if net_income is None:
        return None
    if book_value == 0:
        return None
    return net_income / book_value


# ==============================================================================
# Composite Calculations (Sum-over-Sum for Accounting Metrics)
# ==============================================================================

def compute_composite_ps(
    snapshots: List[SymbolSnapshot],
    strict: bool = True,
    quality_report: Optional[DataQualityReport] = None
) -> Tuple[Optional[float], List[str], List[str]]:
    """
    Compute composite P/S = (Σ Market Cap) / (Σ Revenue).
    Returns: (ratio, symbols_included, warnings)
    """
    total_mcap = 0.0
    total_revenue = 0.0
    included = []
    warnings = []

    for snap in snapshots:
        if snap.market_cap is None or snap.revenue_ttm is None:
            warnings.append(f"{snap.symbol}: Missing market cap or revenue")
            if quality_report:
                quality_report.add_excluded_symbol("P/S", snap.symbol)
            continue
        if strict and snap.revenue_ttm <= 0:
            warnings.append(f"{snap.symbol}: Non-positive revenue ({snap.revenue_ttm})")
            if quality_report:
                quality_report.add_excluded_symbol("P/S", snap.symbol)
                quality_report.add_negative_denominator(snap.symbol, "revenue_ttm")
            continue

        total_mcap += snap.market_cap
        total_revenue += snap.revenue_ttm
        included.append(snap.symbol)

    if total_revenue == 0 or not included:
        return None, included, warnings

    return total_mcap / total_revenue, included, warnings


def compute_composite_ev_sales(
    snapshots: List[SymbolSnapshot],
    strict: bool = True,
    quality_report: Optional[DataQualityReport] = None
) -> Tuple[Optional[float], List[str], List[str]]:
    """Compute composite EV/Sales = (Σ EV) / (Σ Revenue)."""
    total_ev = 0.0
    total_revenue = 0.0
    included = []
    warnings = []

    for snap in snapshots:
        ev = snap.compute_enterprise_value()
        if ev is None or snap.revenue_ttm is None:
            warnings.append(f"{snap.symbol}: Missing EV or revenue")
            if quality_report:
                quality_report.add_excluded_symbol("EV/Sales", snap.symbol)
            continue
        if strict and snap.revenue_ttm <= 0:
            warnings.append(f"{snap.symbol}: Non-positive revenue")
            if quality_report:
                quality_report.add_excluded_symbol("EV/Sales", snap.symbol)
                quality_report.add_negative_denominator(snap.symbol, "revenue_ttm")
            continue

        total_ev += ev
        total_revenue += snap.revenue_ttm
        included.append(snap.symbol)

    if total_revenue == 0 or not included:
        return None, included, warnings

    return total_ev / total_revenue, included, warnings


def compute_composite_pe(
    snapshots: List[SymbolSnapshot],
    strict: bool = True,
    quality_report: Optional[DataQualityReport] = None
) -> Tuple[Optional[float], List[str], List[str]]:
    """Compute composite P/E = (Σ Market Cap) / (Σ Net Income)."""
    total_mcap = 0.0
    total_ni = 0.0
    included = []
    warnings = []

    for snap in snapshots:
        if snap.market_cap is None or snap.net_income_ttm is None:
            warnings.append(f"{snap.symbol}: Missing market cap or net income")
            if quality_report:
                quality_report.add_excluded_symbol("P/E", snap.symbol)
            continue
        if strict and snap.net_income_ttm <= 0:
            warnings.append(f"{snap.symbol}: Non-positive net income")
            if quality_report:
                quality_report.add_excluded_symbol("P/E", snap.symbol)
                quality_report.add_negative_denominator(snap.symbol, "net_income_ttm")
            continue

        total_mcap += snap.market_cap
        total_ni += snap.net_income_ttm
        included.append(snap.symbol)

    if total_ni == 0 or not included:
        return None, included, warnings

    return total_mcap / total_ni, included, warnings


def compute_composite_peg(
    snapshots: List[SymbolSnapshot],
    strict: bool = True,
    quality_report: Optional[DataQualityReport] = None
) -> Tuple[Optional[float], List[str], List[str]]:
    """
    Compute composite PEG = Composite P/E / (market-cap weighted growth).
    Returns None if too many symbols missing growth.
    """
    # First get composite P/E
    composite_pe, included_pe, warnings = compute_composite_pe(snapshots, strict, quality_report)
    if composite_pe is None:
        return None, [], warnings

    # Compute weighted average growth
    total_weight = 0.0
    weighted_growth = 0.0
    included = []

    for snap in snapshots:
        if snap.symbol not in included_pe:
            continue
        if snap.growth_forward_1y is None or snap.growth_forward_1y <= 0:
            warnings.append(f"{snap.symbol}: Missing or non-positive growth estimate")
            if quality_report:
                quality_report.add_excluded_symbol("PEG", snap.symbol)
            continue
        if snap.market_cap is None:
            continue

        total_weight += snap.market_cap
        weighted_growth += snap.market_cap * snap.growth_forward_1y
        included.append(snap.symbol)

    if total_weight == 0 or not included:
        warnings.append("Insufficient growth data for PEG calculation")
        return None, included, warnings

    avg_growth = weighted_growth / total_weight
    # Convert to percentage
    avg_growth_pct = avg_growth * 100 if avg_growth < 1 else avg_growth

    if avg_growth_pct == 0:
        return None, included, warnings

    return composite_pe / avg_growth_pct, included, warnings


def compute_composite_ev_ebitda(
    snapshots: List[SymbolSnapshot],
    strict: bool = True,
    quality_report: Optional[DataQualityReport] = None
) -> Tuple[Optional[float], List[str], List[str]]:
    """Compute composite EV/EBITDA = (Σ EV) / (Σ EBITDA)."""
    total_ev = 0.0
    total_ebitda = 0.0
    included = []
    warnings = []

    for snap in snapshots:
        ev = snap.compute_enterprise_value()
        if ev is None or snap.ebitda_ttm is None:
            warnings.append(f"{snap.symbol}: Missing EV or EBITDA")
            if quality_report:
                quality_report.add_excluded_symbol("EV/EBITDA", snap.symbol)
            continue
        if strict and snap.ebitda_ttm <= 0:
            warnings.append(f"{snap.symbol}: Non-positive EBITDA")
            if quality_report:
                quality_report.add_excluded_symbol("EV/EBITDA", snap.symbol)
                quality_report.add_negative_denominator(snap.symbol, "ebitda_ttm")
            continue

        total_ev += ev
        total_ebitda += snap.ebitda_ttm
        included.append(snap.symbol)

    if total_ebitda == 0 or not included:
        return None, included, warnings

    return total_ev / total_ebitda, included, warnings


def compute_composite_ev_ebit(
    snapshots: List[SymbolSnapshot],
    strict: bool = True,
    quality_report: Optional[DataQualityReport] = None
) -> Tuple[Optional[float], List[str], List[str]]:
    """Compute composite EV/EBIT = (Σ EV) / (Σ EBIT)."""
    total_ev = 0.0
    total_ebit = 0.0
    included = []
    warnings = []

    for snap in snapshots:
        ev = snap.compute_enterprise_value()
        if ev is None or snap.ebit_ttm is None:
            warnings.append(f"{snap.symbol}: Missing EV or EBIT")
            if quality_report:
                quality_report.add_excluded_symbol("EV/EBIT", snap.symbol)
            continue
        if strict and snap.ebit_ttm <= 0:
            warnings.append(f"{snap.symbol}: Non-positive EBIT")
            if quality_report:
                quality_report.add_excluded_symbol("EV/EBIT", snap.symbol)
                quality_report.add_negative_denominator(snap.symbol, "ebit_ttm")
            continue

        total_ev += ev
        total_ebit += snap.ebit_ttm
        included.append(snap.symbol)

    if total_ebit == 0 or not included:
        return None, included, warnings

    return total_ev / total_ebit, included, warnings


def compute_composite_pb(
    snapshots: List[SymbolSnapshot],
    strict: bool = True,
    quality_report: Optional[DataQualityReport] = None
) -> Tuple[Optional[float], List[str], List[str]]:
    """Compute composite P/B = (Σ Market Cap) / (Σ Book Value)."""
    total_mcap = 0.0
    total_equity = 0.0
    included = []
    warnings = []

    for snap in snapshots:
        if snap.market_cap is None or snap.equity_book is None:
            warnings.append(f"{snap.symbol}: Missing market cap or book value")
            if quality_report:
                quality_report.add_excluded_symbol("P/B", snap.symbol)
            continue
        if strict and snap.equity_book <= 0:
            warnings.append(f"{snap.symbol}: Non-positive book value")
            if quality_report:
                quality_report.add_excluded_symbol("P/B", snap.symbol)
                quality_report.add_negative_denominator(snap.symbol, "equity_book")
            continue

        total_mcap += snap.market_cap
        total_equity += snap.equity_book
        included.append(snap.symbol)

    if total_equity == 0 or not included:
        return None, included, warnings

    return total_mcap / total_equity, included, warnings


def compute_composite_ev_aum(
    snapshots: List[SymbolSnapshot],
    strict: bool = True,
    quality_report: Optional[DataQualityReport] = None
) -> Tuple[Optional[float], List[str], List[str]]:
    """Compute composite EV/AUM = (Σ EV) / (Σ AUM) for asset managers."""
    total_ev = 0.0
    total_aum = 0.0
    included = []
    warnings = []

    for snap in snapshots:
        ev = snap.compute_enterprise_value()
        if ev is None or snap.aum is None:
            warnings.append(f"{snap.symbol}: Missing EV or AUM (not an asset manager?)")
            if quality_report:
                quality_report.add_excluded_symbol("EV/AUM", snap.symbol)
            continue
        if strict and snap.aum <= 0:
            warnings.append(f"{snap.symbol}: Non-positive AUM")
            if quality_report:
                quality_report.add_excluded_symbol("EV/AUM", snap.symbol)
                quality_report.add_negative_denominator(snap.symbol, "aum")
            continue

        total_ev += ev
        total_aum += snap.aum
        included.append(snap.symbol)

    if total_aum == 0 or not included:
        return None, included, warnings

    return total_ev / total_aum, included, warnings


def compute_composite_roe(
    snapshots: List[SymbolSnapshot],
    weighting: str = "market_cap",  # "market_cap" or "equity"
    strict: bool = True,
    quality_report: Optional[DataQualityReport] = None
) -> Tuple[Optional[float], List[str], List[str]]:
    """
    Compute composite ROE as weighted average.
    weighting: 'market_cap' (default) or 'equity'
    """
    total_weight = 0.0
    weighted_roe = 0.0
    included = []
    warnings = []

    for snap in snapshots:
        if snap.net_income_ttm is None or snap.equity_book is None:
            warnings.append(f"{snap.symbol}: Missing net income or book value for ROE")
            if quality_report:
                quality_report.add_excluded_symbol("ROE", snap.symbol)
            continue
        if strict and snap.equity_book <= 0:
            warnings.append(f"{snap.symbol}: Non-positive book value")
            if quality_report:
                quality_report.add_excluded_symbol("ROE", snap.symbol)
                quality_report.add_negative_denominator(snap.symbol, "equity_book")
            continue

        roe = snap.net_income_ttm / snap.equity_book

        if weighting == "market_cap":
            if snap.market_cap is None:
                warnings.append(f"{snap.symbol}: Missing market cap for weighting")
                if quality_report:
                    quality_report.add_excluded_symbol("ROE", snap.symbol)
                continue
            weight = snap.market_cap
        elif weighting == "equity":
            weight = snap.equity_book
        else:
            raise ValueError(f"Unknown weighting mode: {weighting}")

        total_weight += weight
        weighted_roe += weight * roe
        included.append(snap.symbol)

    if total_weight == 0 or not included:
        return None, included, warnings

    return weighted_roe / total_weight, included, warnings


# ==============================================================================
# Time Series Processing
# ==============================================================================

def forward_fill_fundamentals(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    Forward-fill fundamental columns (TTM data between quarterly reports).
    """
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = df[col].ffill()
    return df


def apply_rolling_window(df: pd.DataFrame, window_days: int, columns: List[str]) -> pd.DataFrame:
    """
    Apply rolling average to specified columns.
    """
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[f"{col}_rolling"] = df[col].rolling(window=window_days, min_periods=1).mean()
    return df


def winsorize_series(series: pd.Series, lower_percentile: float = 0.01, upper_percentile: float = 0.99) -> pd.Series:
    """
    Winsorize series at specified percentiles to handle outliers.
    """
    lower = series.quantile(lower_percentile)
    upper = series.quantile(upper_percentile)
    return series.clip(lower=lower, upper=upper)
