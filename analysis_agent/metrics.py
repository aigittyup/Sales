"""Sales and supply chain metrics computation engine."""

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


# --- Data type detection ---

SUPPLY_CHAIN_INDICATORS = {"otif", "fill", "delivered", "on_time", "not_delivered", "order_qty"}
REVENUE_INDICATORS = {"revenue", "sales", "amount", "price", "total"}


def detect_data_type(df: pd.DataFrame) -> str:
    """Detect whether data is 'supply_chain' or 'revenue' based on column names."""
    cols = set(df.columns)
    sc_matches = len(cols & SUPPLY_CHAIN_INDICATORS)
    rev_matches = len(cols & REVENUE_INDICATORS)
    # Also check partial matches
    for col in cols:
        for indicator in SUPPLY_CHAIN_INDICATORS:
            if indicator in col:
                sc_matches += 1
        for indicator in REVENUE_INDICATORS:
            if indicator in col:
                rev_matches += 1
    return "supply_chain" if sc_matches > rev_matches else "revenue"


# --- Revenue metrics (original) ---

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


# --- Supply chain metrics ---

@dataclass
class SupplyChainMetrics:
    """Container for supply chain / delivery performance metrics."""

    total_order_qty: int
    total_delivered: int
    total_not_delivered: int
    avg_otif_pct: float
    avg_fill_pct: float
    num_records: int
    by_group: pd.DataFrame
    by_corp: pd.DataFrame
    monthly_trend: pd.DataFrame
    period_start: str
    period_end: str

    def summary(self) -> dict[str, Any]:
        fill_rate = self.total_delivered / self.total_order_qty * 100 if self.total_order_qty else 0
        return {
            "total_order_qty": self.total_order_qty,
            "total_delivered": self.total_delivered,
            "total_not_delivered": self.total_not_delivered,
            "overall_fill_rate_pct": round(fill_rate, 2),
            "avg_otif_pct": round(self.avg_otif_pct * 100, 2),
            "avg_fill_pct": round(self.avg_fill_pct * 100, 2),
            "num_records": self.num_records,
            "period": f"{self.period_start} to {self.period_end}",
        }


def _find_col(df: pd.DataFrame, keywords: list[str], default: str = "") -> str:
    """Find the first column containing any of the keywords."""
    for col in df.columns:
        for kw in keywords:
            if kw in col:
                return col
    return default


def compute_supply_chain_metrics(
    df: pd.DataFrame,
    date_col: str = "date",
    top_n: int = 10,
) -> SupplyChainMetrics:
    """Compute supply chain performance metrics."""
    otif_col = _find_col(df, ["otif"])
    fill_col = _find_col(df, ["fill"])
    order_qty_col = _find_col(df, ["order_qty"])
    delivered_col = _find_col(df, ["total_delivered"])
    not_delivered_col = _find_col(df, ["not_delivered"], "")
    group_col = _find_col(df, ["group_size", "group"])
    corp_col = _find_col(df, ["corp_name", "corp"])

    total_order_qty = int(df[order_qty_col].sum()) if order_qty_col in df.columns else 0
    total_delivered = int(df[delivered_col].sum()) if delivered_col in df.columns else 0

    # Find not_delivered column that doesn't have "by_due_date" or "date" suffix specifically
    not_del_cols = [c for c in df.columns if "not_delivered" in c]
    # Prefer the shorter/simpler one (just "not_delivered")
    if not_delivered_col and not_delivered_col in df.columns:
        total_not_delivered = int(df[not_delivered_col].sum())
    elif not_del_cols:
        total_not_delivered = int(df[not_del_cols[-1]].sum())
    else:
        total_not_delivered = total_order_qty - total_delivered

    avg_otif = float(df[otif_col].mean()) if otif_col in df.columns else 0.0
    avg_fill = float(df[fill_col].mean()) if fill_col in df.columns else 0.0

    # By group size
    by_group = pd.DataFrame()
    if group_col in df.columns:
        agg_cols = {}
        if order_qty_col in df.columns:
            agg_cols[order_qty_col] = "sum"
        if delivered_col in df.columns:
            agg_cols[delivered_col] = "sum"
        if otif_col in df.columns:
            agg_cols[otif_col] = "mean"
        if fill_col in df.columns:
            agg_cols[fill_col] = "mean"

        if agg_cols:
            by_group = (
                df.groupby(group_col)
                .agg(agg_cols)
                .sort_values(order_qty_col if order_qty_col in agg_cols else list(agg_cols.keys())[0], ascending=False)
                .head(top_n)
                .reset_index()
            )
            # Format percentage columns for display
            for col in [otif_col, fill_col]:
                if col in by_group.columns:
                    by_group[col] = by_group[col].round(4)

    # By corp
    by_corp = pd.DataFrame()
    if corp_col in df.columns:
        agg_cols = {}
        if order_qty_col in df.columns:
            agg_cols[order_qty_col] = "sum"
        if delivered_col in df.columns:
            agg_cols[delivered_col] = "sum"
        if otif_col in df.columns:
            agg_cols[otif_col] = "mean"
        if fill_col in df.columns:
            agg_cols[fill_col] = "mean"

        if agg_cols:
            by_corp = (
                df.groupby(corp_col)
                .agg(agg_cols)
                .sort_values(order_qty_col if order_qty_col in agg_cols else list(agg_cols.keys())[0], ascending=False)
                .head(top_n)
                .reset_index()
            )
            for col in [otif_col, fill_col]:
                if col in by_corp.columns:
                    by_corp[col] = by_corp[col].round(4)

    # Monthly trend
    monthly_trend = pd.DataFrame()
    period_start = "N/A"
    period_end = "N/A"
    if date_col in df.columns and pd.api.types.is_datetime64_any_dtype(df[date_col]):
        agg_cols = {}
        if order_qty_col in df.columns:
            agg_cols[order_qty_col] = "sum"
        if delivered_col in df.columns:
            agg_cols[delivered_col] = "sum"
        if otif_col in df.columns:
            agg_cols[otif_col] = "mean"
        if fill_col in df.columns:
            agg_cols[fill_col] = "mean"

        if agg_cols:
            monthly_trend = (
                df.set_index(date_col)
                .resample("ME")
                .agg(agg_cols)
                .reset_index()
            )
            for col in [otif_col, fill_col]:
                if col in monthly_trend.columns:
                    monthly_trend[col] = monthly_trend[col].round(4)

        period_start = str(df[date_col].min().date())
        period_end = str(df[date_col].max().date())

    return SupplyChainMetrics(
        total_order_qty=total_order_qty,
        total_delivered=total_delivered,
        total_not_delivered=total_not_delivered,
        avg_otif_pct=avg_otif,
        avg_fill_pct=avg_fill,
        num_records=len(df),
        by_group=by_group,
        by_corp=by_corp,
        monthly_trend=monthly_trend,
        period_start=period_start,
        period_end=period_end,
    )


# --- Original revenue functions ---

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

    total_units = int(df[quantity_col].sum()) if quantity_col in df.columns else 0

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
    value_col: str = "revenue",
) -> pd.DataFrame:
    """Analyze a value column by a categorical segment."""
    if segment_col not in df.columns:
        raise ValueError(f"Segment column '{segment_col}' not found in data.")

    if value_col not in df.columns:
        # Fall back to order_qty for supply chain data
        value_col = _find_col(df, ["order_qty", "total_delivered"]) or value_col

    result = (
        df.groupby(segment_col)[value_col]
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


def correlation_analysis(df: pd.DataFrame) -> dict:
    """Compute correlation matrix and identify strong correlations among numeric columns."""
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        return {"matrix": pd.DataFrame(), "strong_correlations": []}

    corr_matrix = numeric_df.corr()

    strong = []
    cols = corr_matrix.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr_matrix.iloc[i, j]
            if abs(r) >= 0.5:
                strong.append({
                    "col_1": cols[i],
                    "col_2": cols[j],
                    "correlation": round(float(r), 4),
                    "strength": "strong" if abs(r) >= 0.7 else "moderate",
                })

    strong.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return {"matrix": corr_matrix, "strong_correlations": strong}


def _validate_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. Available columns: {list(df.columns)}"
        )
