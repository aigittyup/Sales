"""Data loading utilities for various sales data formats."""

import os
from pathlib import Path

import pandas as pd


def load_csv(filepath: str) -> pd.DataFrame:
    """Load sales data from a CSV file."""
    return pd.read_csv(filepath, parse_dates=True, infer_datetime_format=True)


def load_excel(filepath: str, sheet_name: str | None = None) -> pd.DataFrame:
    """Load sales data from an Excel file."""
    return pd.read_excel(filepath, sheet_name=sheet_name or 0)


def load_data(filepath: str, **kwargs) -> pd.DataFrame:
    """Auto-detect file type and load sales data.

    Supports CSV and Excel formats.
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
