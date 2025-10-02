"""
Unit tests for metrics calculations.
"""
import pytest
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from core import metrics
from core.models import SymbolSnapshot, DataQualityReport


@pytest.fixture
def sample_snapshot_aapl():
    """Sample snapshot for AAPL."""
    return SymbolSnapshot(
        symbol="AAPL",
        timestamp=datetime(2024, 1, 1),
        price=180.0,
        shares_outstanding=15_500_000_000,
        market_cap=180.0 * 15_500_000_000,  # $2.79T
        total_debt=100_000_000_000,  # $100B
        cash=50_000_000_000,  # $50B
        revenue_ttm=400_000_000_000,  # $400B
        ebitda_ttm=120_000_000_000,  # $120B
        ebit_ttm=110_000_000_000,  # $110B
        net_income_ttm=100_000_000_000,  # $100B
        equity_book=60_000_000_000,  # $60B
        eps_ttm=6.45,
        growth_forward_1y=0.10  # 10%
    )


@pytest.fixture
def sample_snapshot_msft():
    """Sample snapshot for MSFT."""
    return SymbolSnapshot(
        symbol="MSFT",
        timestamp=datetime(2024, 1, 1),
        price=370.0,
        shares_outstanding=7_500_000_000,
        market_cap=370.0 * 7_500_000_000,  # $2.775T
        total_debt=80_000_000_000,  # $80B
        cash=100_000_000_000,  # $100B
        revenue_ttm=220_000_000_000,  # $220B
        ebitda_ttm=90_000_000_000,  # $90B
        ebit_ttm=85_000_000_000,  # $85B
        net_income_ttm=75_000_000_000,  # $75B
        equity_book=200_000_000_000,  # $200B
        eps_ttm=10.0,
        growth_forward_1y=0.12  # 12%
    )


class TestIndividualMetrics:
    """Test individual metric calculations."""

    def test_ps_ratio(self, sample_snapshot_aapl):
        """Test P/S ratio calculation."""
        ps = metrics.compute_ps_ratio(
            sample_snapshot_aapl.market_cap,
            sample_snapshot_aapl.revenue_ttm
        )
        expected = 2_790_000_000_000 / 400_000_000_000  # ~6.975
        assert ps == pytest.approx(expected, rel=0.01)

    def test_ps_ratio_zero_revenue(self, sample_snapshot_aapl):
        """Test P/S with zero revenue."""
        ps = metrics.compute_ps_ratio(
            sample_snapshot_aapl.market_cap,
            0.0
        )
        assert ps is None

    def test_pe_ratio(self, sample_snapshot_aapl):
        """Test P/E ratio calculation."""
        pe = metrics.compute_pe_ratio(
            sample_snapshot_aapl.market_cap,
            sample_snapshot_aapl.net_income_ttm
        )
        expected = 2_790_000_000_000 / 100_000_000_000  # 27.9
        assert pe == pytest.approx(expected, rel=0.01)

    def test_ev_sales(self, sample_snapshot_aapl):
        """Test EV/Sales calculation."""
        ev = sample_snapshot_aapl.compute_enterprise_value()
        ev_sales = metrics.compute_ev_sales(ev, sample_snapshot_aapl.revenue_ttm)

        expected_ev = 2_790_000_000_000 + 100_000_000_000 - 50_000_000_000  # $2.84T
        expected = expected_ev / 400_000_000_000  # ~7.1
        assert ev_sales == pytest.approx(expected, rel=0.01)

    def test_ev_ebitda(self, sample_snapshot_aapl):
        """Test EV/EBITDA calculation."""
        ev = sample_snapshot_aapl.compute_enterprise_value()
        ev_ebitda = metrics.compute_ev_ebitda(ev, sample_snapshot_aapl.ebitda_ttm)

        expected_ev = 2_790_000_000_000 + 100_000_000_000 - 50_000_000_000
        expected = expected_ev / 120_000_000_000  # ~23.67
        assert ev_ebitda == pytest.approx(expected, rel=0.01)

    def test_pb_ratio(self, sample_snapshot_aapl):
        """Test P/B ratio calculation."""
        pb = metrics.compute_pb_ratio(
            sample_snapshot_aapl.market_cap,
            sample_snapshot_aapl.equity_book
        )
        expected = 2_790_000_000_000 / 60_000_000_000  # 46.5
        assert pb == pytest.approx(expected, rel=0.01)

    def test_roe(self, sample_snapshot_aapl):
        """Test ROE calculation."""
        roe = metrics.compute_roe(
            sample_snapshot_aapl.net_income_ttm,
            sample_snapshot_aapl.equity_book
        )
        expected = 100_000_000_000 / 60_000_000_000  # 1.667
        assert roe == pytest.approx(expected, rel=0.01)

    def test_peg_ratio(self, sample_snapshot_aapl):
        """Test PEG ratio calculation."""
        pe = metrics.compute_pe_ratio(
            sample_snapshot_aapl.market_cap,
            sample_snapshot_aapl.net_income_ttm
        )
        peg = metrics.compute_peg_ratio(pe, sample_snapshot_aapl.growth_forward_1y)

        # PE = 27.9, Growth = 10%, PEG = 27.9 / 10 = 2.79
        expected = pe / 10.0
        assert peg == pytest.approx(expected, rel=0.01)

    def test_negative_denominator_strict(self, sample_snapshot_aapl):
        """Test strict mode with negative denominator."""
        result = metrics.compute_ps_ratio(
            sample_snapshot_aapl.market_cap,
            -1000.0,
            strict=True
        )
        assert result is None

    def test_negative_denominator_non_strict(self, sample_snapshot_aapl):
        """Test non-strict mode with negative denominator."""
        result = metrics.compute_ps_ratio(
            sample_snapshot_aapl.market_cap,
            -1000.0,
            strict=False
        )
        # Should still return None for zero
        assert result is None


class TestCompositeMetrics:
    """Test composite metric calculations."""

    def test_composite_ps(self, sample_snapshot_aapl, sample_snapshot_msft):
        """Test composite P/S calculation."""
        snapshots = [sample_snapshot_aapl, sample_snapshot_msft]
        ratio, included, warnings = metrics.compute_composite_ps(snapshots)

        total_mcap = sample_snapshot_aapl.market_cap + sample_snapshot_msft.market_cap
        total_revenue = sample_snapshot_aapl.revenue_ttm + sample_snapshot_msft.revenue_ttm

        expected = total_mcap / total_revenue
        assert ratio == pytest.approx(expected, rel=0.01)
        assert len(included) == 2
        assert "AAPL" in included
        assert "MSFT" in included

    def test_composite_pe(self, sample_snapshot_aapl, sample_snapshot_msft):
        """Test composite P/E calculation."""
        snapshots = [sample_snapshot_aapl, sample_snapshot_msft]
        ratio, included, warnings = metrics.compute_composite_pe(snapshots)

        total_mcap = sample_snapshot_aapl.market_cap + sample_snapshot_msft.market_cap
        total_ni = sample_snapshot_aapl.net_income_ttm + sample_snapshot_msft.net_income_ttm

        expected = total_mcap / total_ni
        assert ratio == pytest.approx(expected, rel=0.01)
        assert len(included) == 2

    def test_composite_ev_sales(self, sample_snapshot_aapl, sample_snapshot_msft):
        """Test composite EV/Sales calculation."""
        snapshots = [sample_snapshot_aapl, sample_snapshot_msft]
        ratio, included, warnings = metrics.compute_composite_ev_sales(snapshots)

        ev_aapl = sample_snapshot_aapl.compute_enterprise_value()
        ev_msft = sample_snapshot_msft.compute_enterprise_value()
        total_ev = ev_aapl + ev_msft
        total_revenue = sample_snapshot_aapl.revenue_ttm + sample_snapshot_msft.revenue_ttm

        expected = total_ev / total_revenue
        assert ratio == pytest.approx(expected, rel=0.01)

    def test_composite_roe_market_cap_weighted(self, sample_snapshot_aapl, sample_snapshot_msft):
        """Test composite ROE with market cap weighting."""
        snapshots = [sample_snapshot_aapl, sample_snapshot_msft]
        ratio, included, warnings = metrics.compute_composite_roe(
            snapshots,
            weighting="market_cap"
        )

        roe_aapl = sample_snapshot_aapl.net_income_ttm / sample_snapshot_aapl.equity_book
        roe_msft = sample_snapshot_msft.net_income_ttm / sample_snapshot_msft.equity_book

        total_mcap = sample_snapshot_aapl.market_cap + sample_snapshot_msft.market_cap
        weight_aapl = sample_snapshot_aapl.market_cap / total_mcap
        weight_msft = sample_snapshot_msft.market_cap / total_mcap

        expected = weight_aapl * roe_aapl + weight_msft * roe_msft
        assert ratio == pytest.approx(expected, rel=0.01)

    def test_composite_roe_equity_weighted(self, sample_snapshot_aapl, sample_snapshot_msft):
        """Test composite ROE with equity weighting."""
        snapshots = [sample_snapshot_aapl, sample_snapshot_msft]
        ratio, included, warnings = metrics.compute_composite_roe(
            snapshots,
            weighting="equity"
        )

        roe_aapl = sample_snapshot_aapl.net_income_ttm / sample_snapshot_aapl.equity_book
        roe_msft = sample_snapshot_msft.net_income_ttm / sample_snapshot_msft.equity_book

        total_equity = sample_snapshot_aapl.equity_book + sample_snapshot_msft.equity_book
        weight_aapl = sample_snapshot_aapl.equity_book / total_equity
        weight_msft = sample_snapshot_msft.equity_book / total_equity

        expected = weight_aapl * roe_aapl + weight_msft * roe_msft
        assert ratio == pytest.approx(expected, rel=0.01)

    def test_composite_peg(self, sample_snapshot_aapl, sample_snapshot_msft):
        """Test composite PEG calculation."""
        snapshots = [sample_snapshot_aapl, sample_snapshot_msft]
        ratio, included, warnings = metrics.compute_composite_peg(snapshots)

        # Composite P/E
        total_mcap = sample_snapshot_aapl.market_cap + sample_snapshot_msft.market_cap
        total_ni = sample_snapshot_aapl.net_income_ttm + sample_snapshot_msft.net_income_ttm
        composite_pe = total_mcap / total_ni

        # Weighted growth
        total_weight = total_mcap
        weighted_growth = (
            sample_snapshot_aapl.market_cap * sample_snapshot_aapl.growth_forward_1y +
            sample_snapshot_msft.market_cap * sample_snapshot_msft.growth_forward_1y
        ) / total_weight

        expected = composite_pe / (weighted_growth * 100)
        assert ratio == pytest.approx(expected, rel=0.01)

    def test_composite_with_missing_data(self, sample_snapshot_aapl, sample_snapshot_msft):
        """Test composite calculation when one symbol has missing data."""
        # Remove revenue from MSFT
        sample_snapshot_msft.revenue_ttm = None

        snapshots = [sample_snapshot_aapl, sample_snapshot_msft]
        ratio, included, warnings = metrics.compute_composite_ps(snapshots)

        # Should only include AAPL
        expected = sample_snapshot_aapl.market_cap / sample_snapshot_aapl.revenue_ttm
        assert ratio == pytest.approx(expected, rel=0.01)
        assert len(included) == 1
        assert "AAPL" in included
        assert "MSFT" not in included
        assert len(warnings) > 0

    def test_composite_with_negative_denominator_strict(
        self, sample_snapshot_aapl, sample_snapshot_msft
    ):
        """Test composite with negative denominator in strict mode."""
        # Make MSFT revenue negative
        sample_snapshot_msft.revenue_ttm = -1000.0

        snapshots = [sample_snapshot_aapl, sample_snapshot_msft]
        quality_report = DataQualityReport(
            symbols_analyzed=["AAPL", "MSFT"],
            timestamp=datetime.now()
        )

        ratio, included, warnings = metrics.compute_composite_ps(
            snapshots,
            strict=True,
            quality_report=quality_report
        )

        # Should only include AAPL
        assert len(included) == 1
        assert "AAPL" in included
        assert "MSFT" in quality_report.excluded_from_metrics.get("P/S", [])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
