"""Data loading utilities for various sales data formats."""

from pathlib import Path

import numpy as np
import pandas as pd


def _is_string_col(series: pd.Series) -> bool:
    """Check if a column contains string data (works with pandas 2.x and 3.x)."""
    return series.dtype == object or str(series.dtype) == "string" or str(series.dtype) == "str"


def load_csv(filepath: str) -> pd.DataFrame:
    """Load sales data from a CSV file."""
    return pd.read_csv(filepath)


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
    df = _parse_date_columns(df)
    return df


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to snake_case."""
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def _parse_percentages(df: pd.DataFrame) -> pd.DataFrame:
    """Convert percentage strings like '98%' to float values (0.98)."""
    for col in df.columns:
        if _is_string_col(df[col]):
            sample = df[col].dropna().head(20).astype(str)
            if len(sample) > 0 and sample.str.match(r"^\d+\.?\d*%$").all():
                df[col] = df[col].astype(str).str.rstrip("%").astype(float) / 100.0
    return df


def _parse_comma_numbers(df: pd.DataFrame) -> pd.DataFrame:
    """Convert comma-formatted number strings like '17,492' to numeric."""
    for col in df.columns:
        if _is_string_col(df[col]):
            sample = df[col].dropna().head(20).astype(str)
            if len(sample) > 0 and sample.str.match(r"^[\d,]+\.?\d*$").all():
                try:
                    converted = df[col].astype(str).str.replace(",", "").astype(float)
                    if (converted == converted.astype(int)).all():
                        df[col] = converted.astype(int)
                    else:
                        df[col] = converted
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

    if month_col and year_col and _is_string_col(df[month_col]):
        try:
            df["date"] = pd.to_datetime(
                df[month_col].astype(str) + " " + df[year_col].astype(str),
                format="%B %Y",
                errors="coerce",
            )
        except Exception:
            pass

    return df


def _parse_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Auto-detect and parse standalone date columns (not qty/delivery columns)."""
    skip_keywords = {"qty", "delivered", "order", "amount", "total", "not_delivered"}
    for col in df.columns:
        if not _is_string_col(df[col]):
            continue
        # Only parse columns that look like actual date fields
        if not any(kw in col for kw in ("date", "time", "created", "updated")):
            continue
        # Skip columns that contain qty/delivery keywords
        if any(kw in col for kw in skip_keywords):
            continue
        try:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        except Exception:
            pass
    return df
