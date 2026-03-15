"""Sales metrics computation engine."""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class SalesMetrics:
    """Container for computed sales metrics."""

    total_revenue: float
    total_units: int
    avg_order_value: float
    median_order_value: float
    num_transactions: int
    revenue_std: float
    top_products: pd.DataFrame
    monthly_trend: pd.DataFrame
    period_start: str
    period_end: str

    def summary(self) -> dict[str, Any]:
        return {
            "total_revenue": round(self.total_revenue, 2),
            "total_units": self.total_units,
            "avg_order_value": round(self.avg_order_value, 2),
            "median_order_value": round(self.median_order_value, 2),
            "num_transactions": self.num_transactions,
            "revenue_std": round(self.revenue_std, 2),
            "period": f"{self.period_start} to {self.period_end}",
        }


def compute_metrics(
    df: pd.DataFrame,
    revenue_col: str = "revenue",
    quantity_col: str = "quantity",
    date_col: str = "date",
    product_col: str = "product",
    top_n: int = 10,
) -> SalesMetrics:
    """Compute core sales metrics from a DataFrame."""
    _validate_columns(df, [revenue_col])

    revenue = df[revenue_col].dropna()

    # Units sold (if column exists)
    total_units = int(df[quantity_col].sum()) if quantity_col in df.columns else 0

    # Top products by revenue
    if product_col in df.columns:
        top_products = (
            df.groupby(product_col)[revenue_col]
            .agg(["sum", "count", "mean"])
            .rename(columns={"sum": "total_revenue", "count": "num_orders", "mean": "avg_revenue"})
            .sort_values("total_revenue", ascending=False)
            .head(top_n)
            .reset_index()
        )
    else:
        top_products = pd.DataFrame()

    # Monthly trend
    if date_col in df.columns and pd.api.types.is_datetime64_any_dtype(df[date_col]):
        monthly_trend = (
            df.set_index(date_col)
            .resample("ME")[revenue_col]
            .agg(["sum", "count", "mean"])
            .rename(columns={"sum": "total_revenue", "count": "num_orders", "mean": "avg_revenue"})
            .reset_index()
        )
        period_start = str(df[date_col].min().date())
        period_end = str(df[date_col].max().date())
    else:
        monthly_trend = pd.DataFrame()
        period_start = "N/A"
        period_end = "N/A"

    return SalesMetrics(
        total_revenue=float(revenue.sum()),
        total_units=total_units,
        avg_order_value=float(revenue.mean()),
        median_order_value=float(revenue.median()),
        num_transactions=len(revenue),
        revenue_std=float(revenue.std()),
        top_products=top_products,
        monthly_trend=monthly_trend,
        period_start=period_start,
        period_end=period_end,
    )


def compute_growth_rates(monthly_trend: pd.DataFrame, revenue_col: str = "total_revenue") -> pd.DataFrame:
    """Compute month-over-month growth rates."""
    if monthly_trend.empty or revenue_col not in monthly_trend.columns:
        return pd.DataFrame()

    result = monthly_trend.copy()
    result["mom_growth_pct"] = result[revenue_col].pct_change() * 100
    result["cumulative_revenue"] = result[revenue_col].cumsum()
    return result


def segment_analysis(
    df: pd.DataFrame,
    segment_col: str,
    revenue_col: str = "revenue",
) -> pd.DataFrame:
    """Analyze revenue by a categorical segment (region, channel, etc.)."""
    if segment_col not in df.columns:
        raise ValueError(f"Segment column '{segment_col}' not found in data.")

    result = (
        df.groupby(segment_col)[revenue_col]
        .agg(["sum", "count", "mean", "std"])
        .rename(columns={
            "sum": "total_revenue",
            "count": "num_orders",
            "mean": "avg_order_value",
            "std": "revenue_std",
        })
        .sort_values("total_revenue", ascending=False)
        .reset_index()
    )
    result["revenue_share_pct"] = (result["total_revenue"] / result["total_revenue"].sum()) * 100
    return result


def _validate_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. Available columns: {list(df.columns)}"
        )
