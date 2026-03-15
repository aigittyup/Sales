"""Plan vs Actual comparison engine - compares AOP targets to OTIF actuals."""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from analysis_agent.loader import load_data


@dataclass
class PlanVsActualResult:
    """Container for plan vs actual comparison results."""

    merged: pd.DataFrame
    by_month: pd.DataFrame
    by_corp: pd.DataFrame
    by_segment: pd.DataFrame
    summary: dict[str, Any]


def load_aop_data(filepath: str) -> pd.DataFrame:
    """Load and prepare AOP plan data, rolling up to monthly level."""
    df = load_data(filepath)

    # Identify key columns
    date_col = _find_col(df, ["aop_reporting_date", "reporting_date", "date"])
    units_col = _find_col(df, ["aop_sales_units", "aop_adj_units", "aop_units", "sales_units"])
    corp_col = _find_col(df, ["corp"])
    segment_col = _find_col(df, ["commercial_segment", "segment"])
    product_col = _find_col(df, ["product_num", "product"])
    distributor_col = _find_col(df, ["distributor_name", "distributor"])

    if not date_col:
        raise ValueError(f"Could not find date column. Available: {list(df.columns)}")
    if not units_col:
        raise ValueError(f"Could not find AOP units column. Available: {list(df.columns)}")

    # Ensure date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # Standardize column names for joining
    rename = {date_col: "plan_date"}
    if units_col:
        rename[units_col] = "plan_units"
    if corp_col:
        rename[corp_col] = "plan_corp"
    if segment_col:
        rename[segment_col] = "plan_segment"
    if product_col:
        rename[product_col] = "plan_product"
    if distributor_col:
        rename[distributor_col] = "plan_distributor"

    df = df.rename(columns=rename)

    # Add month key for joining
    df["month"] = df["plan_date"].dt.to_period("M")

    return df


def load_actuals_data(filepath: str) -> pd.DataFrame:
    """Load and prepare actuals/OTIF data for comparison."""
    df = load_data(filepath)

    date_col = _find_col(df, ["date"])
    order_col = _find_col(df, ["order_qty"])
    delivered_col = _find_col(df, ["total_delivered_qty", "delivered"])
    corp_col = _find_col(df, ["corp_name", "corp"])

    if not date_col:
        raise ValueError(f"Could not find date column. Available: {list(df.columns)}")

    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    rename = {date_col: "actual_date"}
    if order_col:
        rename[order_col] = "actual_orders"
    if delivered_col:
        rename[delivered_col] = "actual_delivered"
    if corp_col and corp_col != "plan_corp":
        rename[corp_col] = "actual_corp"

    df = df.rename(columns=rename)
    df["month"] = df["actual_date"].dt.to_period("M")

    return df


def compare_plan_vs_actual(
    plan_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
) -> PlanVsActualResult:
    """Compare AOP plan data against actuals at multiple levels."""

    # --- Monthly rollup ---
    plan_monthly = (
        plan_df.groupby("month")
        .agg(plan_units=("plan_units", "sum"))
        .reset_index()
    )

    actual_agg = {}
    if "actual_orders" in actuals_df.columns:
        actual_agg["actual_orders"] = ("actual_orders", "sum")
    if "actual_delivered" in actuals_df.columns:
        actual_agg["actual_delivered"] = ("actual_delivered", "sum")

    actuals_monthly = (
        actuals_df.groupby("month")
        .agg(**actual_agg)
        .reset_index()
    )

    by_month = plan_monthly.merge(actuals_monthly, on="month", how="outer")
    by_month = _add_variance_cols(by_month)
    by_month["month_str"] = by_month["month"].astype(str)

    # --- By Corp ---
    by_corp = pd.DataFrame()
    if "plan_corp" in plan_df.columns and "actual_corp" in actuals_df.columns:
        plan_corp = (
            plan_df.groupby("plan_corp")
            .agg(plan_units=("plan_units", "sum"))
            .reset_index()
            .rename(columns={"plan_corp": "corp"})
        )
        actual_corp_agg = {}
        if "actual_orders" in actuals_df.columns:
            actual_corp_agg["actual_orders"] = ("actual_orders", "sum")
        if "actual_delivered" in actuals_df.columns:
            actual_corp_agg["actual_delivered"] = ("actual_delivered", "sum")

        actuals_corp = (
            actuals_df.groupby("actual_corp")
            .agg(**actual_corp_agg)
            .reset_index()
            .rename(columns={"actual_corp": "corp"})
        )
        by_corp = plan_corp.merge(actuals_corp, on="corp", how="outer")
        by_corp = _add_variance_cols(by_corp)

    # --- By Segment ---
    by_segment = pd.DataFrame()
    if "plan_segment" in plan_df.columns:
        plan_seg = (
            plan_df.groupby("plan_segment")
            .agg(plan_units=("plan_units", "sum"))
            .reset_index()
            .rename(columns={"plan_segment": "segment"})
        )
        by_segment = plan_seg.copy()
        by_segment = _add_variance_cols(by_segment)

    # --- Merged detail (month + corp if available) ---
    merge_keys = ["month"]
    plan_group_cols = ["month"]
    actual_group_cols = ["month"]

    if "plan_corp" in plan_df.columns and "actual_corp" in actuals_df.columns:
        plan_group_cols.append("plan_corp")
        actual_group_cols.append("actual_corp")

    plan_rolled = plan_df.groupby(plan_group_cols).agg(plan_units=("plan_units", "sum")).reset_index()
    actuals_rolled = actuals_df.groupby(actual_group_cols).agg(**actual_agg).reset_index()

    if "plan_corp" in plan_rolled.columns:
        plan_rolled = plan_rolled.rename(columns={"plan_corp": "corp"})
    if "actual_corp" in actuals_rolled.columns:
        actuals_rolled = actuals_rolled.rename(columns={"actual_corp": "corp"})
        if "corp" in plan_rolled.columns:
            merge_keys.append("corp")

    merged = plan_rolled.merge(actuals_rolled, on=merge_keys, how="outer")
    merged = _add_variance_cols(merged)

    # --- Summary ---
    total_plan = float(by_month["plan_units"].sum()) if "plan_units" in by_month else 0
    total_orders = float(by_month["actual_orders"].sum()) if "actual_orders" in by_month else 0
    total_delivered = float(by_month["actual_delivered"].sum()) if "actual_delivered" in by_month else 0

    summary = {
        "total_plan_units": int(total_plan),
        "total_actual_orders": int(total_orders),
        "total_actual_delivered": int(total_delivered),
        "order_attainment_pct": round(total_orders / total_plan * 100, 2) if total_plan else 0,
        "delivery_attainment_pct": round(total_delivered / total_plan * 100, 2) if total_plan else 0,
        "order_gap": int(total_orders - total_plan),
        "delivery_gap": int(total_delivered - total_plan),
        "months_compared": len(by_month.dropna(subset=["plan_units"])),
    }

    return PlanVsActualResult(
        merged=merged,
        by_month=by_month,
        by_corp=by_corp,
        by_segment=by_segment,
        summary=summary,
    )


def _add_variance_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Add variance and attainment columns."""
    if "plan_units" in df.columns and "actual_orders" in df.columns:
        df["order_variance"] = df["actual_orders"] - df["plan_units"]
        df["order_attainment_pct"] = np.where(
            df["plan_units"] > 0,
            (df["actual_orders"] / df["plan_units"] * 100).round(1),
            np.nan,
        )
    if "plan_units" in df.columns and "actual_delivered" in df.columns:
        df["delivery_variance"] = df["actual_delivered"] - df["plan_units"]
        df["delivery_attainment_pct"] = np.where(
            df["plan_units"] > 0,
            (df["actual_delivered"] / df["plan_units"] * 100).round(1),
            np.nan,
        )
    return df


def _find_col(df: pd.DataFrame, keywords: list[str]) -> str:
    """Find the first column matching any keyword (exact match first, then substring)."""
    # Exact matches first
    for kw in keywords:
        if kw in df.columns:
            return kw
    # Then substring matches
    for kw in keywords:
        for col in df.columns:
            if kw in col:
                return col
    return ""
