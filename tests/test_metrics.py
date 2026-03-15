"""Tests for the sales metrics computation engine."""

import pandas as pd
import pytest

from analysis_agent.metrics import compute_metrics, segment_analysis, compute_growth_rates


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "date": pd.to_datetime(["2025-01-01", "2025-01-15", "2025-02-01", "2025-02-15"]),
        "product": ["A", "B", "A", "B"],
        "region": ["North", "South", "North", "South"],
        "quantity": [10, 5, 8, 12],
        "revenue": [100.0, 50.0, 80.0, 120.0],
    })


def test_compute_metrics_totals(sample_df):
    metrics = compute_metrics(sample_df)
    assert metrics.total_revenue == 350.0
    assert metrics.total_units == 35
    assert metrics.num_transactions == 4


def test_compute_metrics_averages(sample_df):
    metrics = compute_metrics(sample_df)
    assert metrics.avg_order_value == 87.5
    assert metrics.median_order_value == 90.0


def test_top_products(sample_df):
    metrics = compute_metrics(sample_df)
    assert len(metrics.top_products) == 2
    top = metrics.top_products.iloc[0]
    assert top["product"] == "A"
    assert top["total_revenue"] == 180.0


def test_monthly_trend(sample_df):
    metrics = compute_metrics(sample_df)
    assert len(metrics.monthly_trend) == 2


def test_segment_analysis(sample_df):
    result = segment_analysis(sample_df, "region")
    assert len(result) == 2
    assert "revenue_share_pct" in result.columns
    assert abs(result["revenue_share_pct"].sum() - 100.0) < 0.01


def test_segment_analysis_missing_col(sample_df):
    with pytest.raises(ValueError, match="Segment column"):
        segment_analysis(sample_df, "nonexistent")


def test_compute_growth_rates(sample_df):
    metrics = compute_metrics(sample_df)
    growth = compute_growth_rates(metrics.monthly_trend)
    assert "mom_growth_pct" in growth.columns
    assert "cumulative_revenue" in growth.columns


def test_missing_revenue_col():
    df = pd.DataFrame({"price": [10, 20]})
    with pytest.raises(ValueError, match="Missing required columns"):
        compute_metrics(df)
