"""
Unit tests for repository.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from core.repository import FundamentalsRepository
from core.models import SymbolSnapshot


class TestFundamentalsRepository:
    """Test FundamentalsRepository."""

    @pytest.fixture
    def repo(self):
        """Create repository instance."""
        with patch('core.repository.YahooFinanceAdapter'):
            repo = FundamentalsRepository(primary_adapter="yahoo")
            return repo

    def test_repository_initialization(self, repo):
        """Test repository initializes correctly."""
        assert repo is not None
        assert repo.primary_adapter_name == "yahoo"

    def test_get_adapter_default(self, repo):
        """Test getting default adapter."""
        adapter = repo.get_adapter()
        assert adapter is not None

    def test_get_adapter_by_name(self, repo):
        """Test getting adapter by name."""
        adapter = repo.get_adapter("yahoo")
        assert adapter is not None

    def test_build_symbol_snapshot(self, repo):
        """Test building a symbol snapshot."""
        # Mock the fetch_snapshot method
        mock_data = {
            'price': 180.0,
            'shares_outstanding': 15_500_000_000,
            'total_debt': 100_000_000_000,
            'cash': 50_000_000_000,
            'revenue_ttm': 400_000_000_000,
            'ebitda_ttm': 120_000_000_000,
            'ebit_ttm': 110_000_000_000,
            'net_income_ttm': 100_000_000_000,
            'equity_book': 60_000_000_000,
            'eps_ttm': 6.45,
            'currency': 'USD'
        }

        with patch.object(repo, 'fetch_snapshot', return_value=mock_data):
            snapshot = repo.build_symbol_snapshot(
                "AAPL",
                datetime(2024, 1, 1)
            )

            assert isinstance(snapshot, SymbolSnapshot)
            assert snapshot.symbol == "AAPL"
            assert snapshot.price == 180.0
            assert snapshot.market_cap == 180.0 * 15_500_000_000

    def test_build_symbol_snapshot_missing_data(self, repo):
        """Test building snapshot with missing data."""
        mock_data = {
            'price': None,
            'shares_outstanding': None,
            'revenue_ttm': None,
            'currency': 'USD'
        }

        with patch.object(repo, 'fetch_snapshot', return_value=mock_data):
            snapshot = repo.build_symbol_snapshot(
                "INVALID",
                datetime(2024, 1, 1)
            )

            assert snapshot.price is None
            assert snapshot.shares_outstanding is None
            # Should have warnings
            assert len(snapshot.warnings) > 0


class TestCaching:
    """Test caching functionality."""

    def test_cache_manager_initialization(self):
        """Test cache manager initializes."""
        from core.cache import CacheManager

        cache = CacheManager()
        assert cache is not None
        assert cache.cache_dir.exists()

    def test_cache_key_generation(self):
        """Test cache key generation."""
        from core.cache import CacheManager

        cache = CacheManager()
        key1 = cache.get_cache_key("test", symbol="AAPL", date="2024-01-01")
        key2 = cache.get_cache_key("test", symbol="AAPL", date="2024-01-01")
        key3 = cache.get_cache_key("test", symbol="MSFT", date="2024-01-01")

        # Same inputs should produce same key
        assert key1 == key2

        # Different inputs should produce different keys
        assert key1 != key3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
