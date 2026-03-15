"""Tests for the data loader module."""

import os
import tempfile

import pandas as pd
import pytest

from analysis_agent.loader import load_data, _normalize_columns


@pytest.fixture
def sample_csv(tmp_path):
    filepath = tmp_path / "test.csv"
    df = pd.DataFrame({
        "Date": ["2025-01-01", "2025-01-02"],
        "Product Name": ["Widget A", "Widget B"],
        "Revenue": [100.0, 200.0],
    })
    df.to_csv(filepath, index=False)
    return str(filepath)


def test_load_csv(sample_csv):
    df = load_data(sample_csv)
    assert len(df) == 2
    assert "revenue" in df.columns
    assert "product_name" in df.columns


def test_normalize_columns():
    df = pd.DataFrame({"  Order Date ": [1], "Product Name": [2], "Total Revenue ($)": [3]})
    result = _normalize_columns(df)
    assert list(result.columns) == ["order_date", "product_name", "total_revenue"]


def test_load_missing_file():
    with pytest.raises(FileNotFoundError):
        load_data("/nonexistent/path.csv")


def test_unsupported_format(tmp_path):
    filepath = tmp_path / "data.txt"
    filepath.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported file format"):
        load_data(str(filepath))
