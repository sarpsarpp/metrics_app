"""
Unit tests for data adapters.
"""
import pytest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from core.adapters.yahoo import YahooFinanceAdapter
from core.adapters.base import DataSourceError


class TestYahooAdapter:
    """Test Yahoo Finance adapter."""

    @pytest.fixture
    def adapter(self):
        """Create Yahoo adapter instance."""
        return YahooFinanceAdapter()

    def test_adapter_initialization(self, adapter):
        """Test adapter initializes correctly."""
        assert adapter is not None

    def test_safe_get_valid_number(self, adapter):
        """Test _safe_get with valid number."""
        data = {"price": 100.5}
        result = adapter._safe_get(data, "price")
        assert result == 100.5

    def test_safe_get_none(self, adapter):
        """Test _safe_get with None."""
        data = {"price": None}
        result = adapter._safe_get(data, "price")
        assert result is None

    def test_safe_get_na_string(self, adapter):
        """Test _safe_get with 'N/A' string."""
        data = {"price": "N/A"}
        result = adapter._safe_get(data, "price")
        assert result is None

    def test_safe_get_missing_key(self, adapter):
        """Test _safe_get with missing key."""
        data = {}
        result = adapter._safe_get(data, "price")
        assert result is None

    def test_safe_get_string_number(self, adapter):
        """Test _safe_get with string that converts to number."""
        data = {"price": "150.75"}
        result = adapter._safe_get(data, "price")
        assert result == 150.75

    @patch('core.adapters.yahoo.yf.Ticker')
    def test_snapshot_structure(self, mock_ticker, adapter):
        """Test snapshot returns correct structure."""
        # Mock the ticker info
        mock_instance = Mock()
        mock_instance.info = {
            'currentPrice': 180.0,
            'sharesOutstanding': 15_500_000_000,
            'currency': 'USD',
            'trailingEps': 6.45
        }
        mock_instance.balance_sheet = pd.DataFrame()
        mock_instance.financials = pd.DataFrame()
        mock_instance.quarterly_financials = pd.DataFrame()

        mock_ticker.return_value = mock_instance

        result = adapter.snapshot("AAPL")

        # Check all required keys are present
        required_keys = [
            'price', 'shares_outstanding', 'total_debt', 'cash',
            'revenue_ttm', 'ebitda_ttm', 'ebit_ttm', 'net_income_ttm',
            'equity_book', 'aum', 'eps_ttm', 'growth_forward_1y', 'currency'
        ]

        for key in required_keys:
            assert key in result

        # Check values that were mocked
        assert result['price'] == 180.0
        assert result['shares_outstanding'] == 15_500_000_000
        assert result['currency'] == 'USD'
        assert result['eps_ttm'] == 6.45


class TestAdapterErrorHandling:
    """Test error handling in adapters."""

    def test_yahoo_adapter_network_error(self):
        """Test handling of network errors."""
        adapter = YahooFinanceAdapter()

        # This will likely fail or return empty data for invalid symbol
        result = adapter.snapshot("INVALID_SYMBOL_XYZ123")

        # Should return dict with None values, not raise exception
        assert isinstance(result, dict)
        assert 'price' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
