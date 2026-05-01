"""Metadata extraction for sales datasets."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


_COLUMN_DESCRIPTIONS: dict[str, str] = {
    "date": "Transaction date",
    "product": "Product name or SKU",
    "region": "Geographic sales region",
    "channel": "Sales channel (e.g. Online, Retail)",
    "quantity": "Number of units sold",
    "revenue": "Total revenue from the transaction",
    "price": "Unit price",
    "cost": "Unit or total cost",
    "profit": "Profit amount",
    "customer": "Customer identifier or name",
    "order_id": "Unique order identifier",
    "category": "Product category",
    "subcategory": "Product subcategory",
    "discount": "Discount applied",
    "country": "Country of sale",
    "city": "City of sale",
    "state": "State or province",
}


@dataclass
class ColumnMetadata:
    """Metadata for a single DataFrame column."""

    name: str
    dtype: str
    nullable: bool
    null_count: int
    null_pct: float
    unique_count: int
    sample_values: list[Any]
    description: str = ""
    tags: list[str] = field(default_factory=list)
    # Numeric stats
    min_value: float | None = None
    max_value: float | None = None
    mean: float | None = None
    std: float | None = None
    median: float | None = None
    # Temporal stats
    date_min: str | None = None
    date_max: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "dtype": self.dtype,
            "nullable": self.nullable,
            "null_count": self.null_count,
            "null_pct": round(self.null_pct, 4),
            "unique_count": self.unique_count,
            "sample_values": self.sample_values,
            "description": self.description,
            "tags": self.tags,
        }
        if self.min_value is not None:
            d["stats"] = {
                "min": self.min_value,
                "max": self.max_value,
                "mean": round(self.mean, 4) if self.mean is not None else None,
                "std": round(self.std, 4) if self.std is not None else None,
                "median": round(self.median, 4) if self.median is not None else None,
            }
        if self.date_min is not None:
            d["temporal_range"] = {"min": self.date_min, "max": self.date_max}
        return d


@dataclass
class DatasetMetadata:
    """Metadata for an entire dataset."""

    source_path: str
    file_format: str
    file_size_bytes: int
    row_count: int
    column_count: int
    extracted_at: str
    columns: list[ColumnMetadata]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "file_format": self.file_format,
            "file_size_bytes": self.file_size_bytes,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "extracted_at": self.extracted_at,
            "columns": [c.to_dict() for c in self.columns],
        }


def _infer_description(col_name: str) -> str:
    for key, desc in _COLUMN_DESCRIPTIONS.items():
        if key in col_name:
            return desc
    return ""


def _infer_tags(col_name: str, dtype: str) -> list[str]:
    tags: list[str] = []
    if "datetime" in dtype:
        tags.append("temporal")
    elif dtype in ("float64", "float32", "int64", "int32"):
        tags.append("numeric")
        if any(k in col_name for k in ("revenue", "price", "cost", "profit", "discount", "amount")):
            tags.append("currency")
        elif any(k in col_name for k in ("quantity", "count", "units", "qty", "num")):
            tags.append("quantity")
    elif dtype in ("object", "str", "string"):
        tags.append("categorical")
    if any(k in col_name for k in ("id", "key", "code", "sku", "order")):
        tags.append("identifier")
    return tags


def extract_metadata(df: pd.DataFrame, source_path: str = "") -> DatasetMetadata:
    """Extract column-level and dataset-level metadata from a DataFrame."""
    path = Path(source_path)
    file_size = path.stat().st_size if path.exists() else 0
    file_format = path.suffix.lstrip(".").lower() if source_path else "unknown"

    columns: list[ColumnMetadata] = []
    for col in df.columns:
        series = df[col]
        dtype = str(series.dtype)
        null_count = int(series.isna().sum())
        null_pct = null_count / len(df) if len(df) > 0 else 0.0
        unique_count = int(series.nunique())
        raw_samples = series.dropna().head(5).tolist()
        sample_values = [str(v) if not isinstance(v, (int, float, bool)) else v for v in raw_samples]

        col_meta = ColumnMetadata(
            name=col,
            dtype=dtype,
            nullable=null_count > 0,
            null_count=null_count,
            null_pct=null_pct,
            unique_count=unique_count,
            sample_values=sample_values,
            description=_infer_description(col),
            tags=_infer_tags(col, dtype),
        )

        if pd.api.types.is_numeric_dtype(series) and not series.dropna().empty:
            col_meta.min_value = float(series.min())
            col_meta.max_value = float(series.max())
            col_meta.mean = float(series.mean())
            col_meta.std = float(series.std())
            col_meta.median = float(series.median())
        elif pd.api.types.is_datetime64_any_dtype(series) and not series.dropna().empty:
            col_meta.date_min = str(series.min().date())
            col_meta.date_max = str(series.max().date())

        columns.append(col_meta)

    return DatasetMetadata(
        source_path=source_path,
        file_format=file_format,
        file_size_bytes=file_size,
        row_count=len(df),
        column_count=len(df.columns),
        extracted_at=datetime.utcnow().isoformat() + "Z",
        columns=columns,
    )
