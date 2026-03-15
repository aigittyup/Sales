"""Data loading utilities for various sales data formats."""

import re
from pathlib import Path

import numpy as np
import pandas as pd


def load_csv(filepath: str) -> pd.DataFrame:
    """Load sales data from a CSV file."""
    return pd.read_csv(filepath, parse_dates=True)


def load_excel(filepath: str, sheet_name: str | None = None) -> pd.DataFrame:
    """Load sales data from an Excel file."""
    return pd.read_excel(filepath, sheet_name=sheet_name or 0)


def load_data(filepath: str, **kwargs) -> pd.DataFrame:
    """Auto-detect file type and load sales data.

    Supports CSV and Excel formats. Automatically handles:
    - Percentage strings (e.g. "98%") -> float (0.98)
    - Comma-formatted numbers (e.g. "17,492") -> int/float
    - Split date columns (Month + Year) -> combined datetime
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    ext = path.suffix.lower()
    loaders = {
        ".csv": load_csv,
        ".xlsx": load_excel,
        ".xls": load_excel,
    }

    loader = loaders.get(ext)
    if loader is None:
        raise ValueError(f"Unsupported file format: {ext}. Supported: {list(loaders.keys())}")

    df = loader(filepath, **kwargs)
    df = _normalize_columns(df)
    df = _parse_percentages(df)
    df = _parse_comma_numbers(df)
    df = _combine_month_year(df)
    return df


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to snake_case."""
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
    )

    # Auto-detect and parse date columns
    for col in df.columns:
        if any(keyword in col for keyword in ("date", "time", "created", "updated")):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                pass

    return df


def _parse_percentages(df: pd.DataFrame) -> pd.DataFrame:
    """Convert percentage strings like '98%' to float values (0.98)."""
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna().head(20)
            if len(sample) > 0 and sample.str.match(r"^\d+\.?\d*%$").all():
                df[col] = df[col].str.rstrip("%").astype(float) / 100.0
    return df


def _parse_comma_numbers(df: pd.DataFrame) -> pd.DataFrame:
    """Convert comma-formatted number strings like '17,492' to numeric."""
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna().head(20)
            if len(sample) > 0 and sample.str.match(r"^[\d,]+\.?\d*$").all():
                try:
                    df[col] = df[col].str.replace(",", "").astype(float)
                    if (df[col] == df[col].astype(int)).all():
                        df[col] = df[col].astype(int)
                except (ValueError, TypeError):
                    pass
    return df


def _combine_month_year(df: pd.DataFrame) -> pd.DataFrame:
    """Combine separate month and year columns into a single date column."""
    month_col = None
    year_col = None

    for col in df.columns:
        if "month" in col and "year" not in col:
            month_col = col
        elif "year" in col and "month" not in col:
            year_col = col

    if month_col and year_col and df[month_col].dtype == object:
        try:
            df["date"] = pd.to_datetime(
                df[month_col].astype(str) + " " + df[year_col].astype(str),
                format="%B %Y",
                errors="coerce",
            )
        except Exception:
            pass

    return df
