"""Tests for the Metadata, Lineage, and Ontology (MLO) tool."""

import json
import os
import tempfile

import pandas as pd
import pytest

from analysis_agent.lineage import DataLineageTracker
from analysis_agent.metadata import ColumnMetadata, DatasetMetadata, extract_metadata
from analysis_agent.mlo_tool import MetadataLineageOntologyTool
from analysis_agent.ontology import ColumnRole, SalesOntology


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01"]),
        "product": ["Widget A", "Widget B", "Widget A"],
        "region": ["North", "South", "East"],
        "channel": ["Online", "Retail", "Online"],
        "quantity": [10, 5, 8],
        "revenue": [500.0, 375.0, 400.0],
    })


@pytest.fixture()
def sample_csv(tmp_path: "pytest.TempPathFactory") -> str:
    path = str(tmp_path / "sales.csv")
    pd.DataFrame({
        "date": ["2025-01-01", "2025-02-01", "2025-03-01"],
        "product": ["Widget A", "Widget B", "Widget A"],
        "region": ["North", "South", "East"],
        "channel": ["Online", "Retail", "Online"],
        "quantity": [10, 5, 8],
        "revenue": [500.0, 375.0, 400.0],
    }).to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------

class TestExtractMetadata:
    def test_returns_dataset_metadata(self, sample_df):
        meta = extract_metadata(sample_df)
        assert isinstance(meta, DatasetMetadata)

    def test_row_and_column_counts(self, sample_df):
        meta = extract_metadata(sample_df)
        assert meta.row_count == 3
        assert meta.column_count == 6

    def test_column_names(self, sample_df):
        meta = extract_metadata(sample_df)
        names = [c.name for c in meta.columns]
        assert names == list(sample_df.columns)

    def test_numeric_stats_populated(self, sample_df):
        meta = extract_metadata(sample_df)
        revenue_meta = next(c for c in meta.columns if c.name == "revenue")
        assert revenue_meta.min_value == pytest.approx(375.0)
        assert revenue_meta.max_value == pytest.approx(500.0)
        assert revenue_meta.mean is not None

    def test_temporal_range_populated(self, sample_df):
        meta = extract_metadata(sample_df)
        date_meta = next(c for c in meta.columns if c.name == "date")
        assert date_meta.date_min == "2025-01-01"
        assert date_meta.date_max == "2025-03-01"

    def test_categorical_tags(self, sample_df):
        meta = extract_metadata(sample_df)
        region_meta = next(c for c in meta.columns if c.name == "region")
        assert "categorical" in region_meta.tags

    def test_currency_tags(self, sample_df):
        meta = extract_metadata(sample_df)
        revenue_meta = next(c for c in meta.columns if c.name == "revenue")
        assert "currency" in revenue_meta.tags

    def test_to_dict_is_json_serialisable(self, sample_df):
        meta = extract_metadata(sample_df)
        assert json.dumps(meta.to_dict())  # should not raise

    def test_description_inferred_for_known_columns(self, sample_df):
        meta = extract_metadata(sample_df)
        revenue_meta = next(c for c in meta.columns if c.name == "revenue")
        assert revenue_meta.description != ""


# ---------------------------------------------------------------------------
# Lineage tests
# ---------------------------------------------------------------------------

class TestDataLineageTracker:
    def test_build_pipeline_creates_nodes(self, sample_df):
        tracker = DataLineageTracker()
        tracker.build_pipeline_lineage(sample_df, "data/sales.csv")
        assert "source_file" in tracker.nodes
        assert "normalized" in tracker.nodes
        assert "core_metrics" in tracker.nodes
        assert "growth_rates" in tracker.nodes
        assert "sales_report" in tracker.nodes

    def test_build_pipeline_creates_edges(self, sample_df):
        tracker = DataLineageTracker()
        tracker.build_pipeline_lineage(sample_df, "data/sales.csv")
        assert len(tracker.edges) > 0

    def test_segment_nodes_created(self, sample_df):
        tracker = DataLineageTracker()
        tracker.build_pipeline_lineage(sample_df, "data/sales.csv", segment_cols=["region"])
        assert "segment_region" in tracker.nodes

    def test_get_upstream(self, sample_df):
        tracker = DataLineageTracker()
        tracker.build_pipeline_lineage(sample_df, "data/sales.csv")
        upstream = tracker.get_upstream("normalized")
        assert "source_file" in upstream

    def test_get_downstream(self, sample_df):
        tracker = DataLineageTracker()
        tracker.build_pipeline_lineage(sample_df, "data/sales.csv")
        downstream = tracker.get_downstream("normalized")
        assert "core_metrics" in downstream

    def test_to_dict_structure(self, sample_df):
        tracker = DataLineageTracker()
        tracker.build_pipeline_lineage(sample_df, "data/sales.csv")
        d = tracker.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert isinstance(d["nodes"], list)
        assert isinstance(d["edges"], list)

    def test_to_dict_is_json_serialisable(self, sample_df):
        tracker = DataLineageTracker()
        tracker.build_pipeline_lineage(sample_df, "data/sales.csv")
        assert json.dumps(tracker.to_dict())


# ---------------------------------------------------------------------------
# Ontology tests
# ---------------------------------------------------------------------------

class TestSalesOntology:
    def test_classify_columns_returns_all_columns(self, sample_df):
        ontology = SalesOntology()
        classifications = ontology.classify_columns(sample_df)
        assert len(classifications) == len(sample_df.columns)

    def test_revenue_classified_as_measure(self, sample_df):
        ontology = SalesOntology()
        classifications = ontology.classify_columns(sample_df)
        revenue_cls = next(c for c in classifications if c.column == "revenue")
        assert revenue_cls.role == ColumnRole.MEASURE

    def test_date_classified_as_temporal(self, sample_df):
        ontology = SalesOntology()
        classifications = ontology.classify_columns(sample_df)
        date_cls = next(c for c in classifications if c.column == "date")
        assert date_cls.role == ColumnRole.TEMPORAL

    def test_region_classified_as_dimension(self, sample_df):
        ontology = SalesOntology()
        classifications = ontology.classify_columns(sample_df)
        region_cls = next(c for c in classifications if c.column == "region")
        assert region_cls.role == ColumnRole.DIMENSION

    def test_known_columns_matched_to_ontology(self, sample_df):
        ontology = SalesOntology()
        classifications = ontology.classify_columns(sample_df)
        matched = [c for c in classifications if c.ontology_term is not None]
        assert len(matched) >= 4  # date, product, region, channel, quantity, revenue all known

    def test_revenue_semantic_type_currency(self, sample_df):
        ontology = SalesOntology()
        classifications = ontology.classify_columns(sample_df)
        revenue_cls = next(c for c in classifications if c.column == "revenue")
        assert revenue_cls.semantic_type == "currency"

    def test_to_dict_contains_terms(self):
        ontology = SalesOntology()
        d = ontology.to_dict()
        assert "terms" in d
        assert "revenue" in d["terms"]
        assert "product" in d["terms"]

    def test_to_dict_is_json_serialisable(self):
        ontology = SalesOntology()
        assert json.dumps(ontology.to_dict())


# ---------------------------------------------------------------------------
# MLO tool integration tests
# ---------------------------------------------------------------------------

class TestMetadataLineageOntologyTool:
    def test_run_returns_all_sections(self, sample_csv, tmp_path):
        tool = MetadataLineageOntologyTool(
            data_source=sample_csv,
            output_dir=str(tmp_path / "output"),
            segment_cols=["region"],
        )
        report = tool.run()
        assert "metadata" in report
        assert "lineage" in report
        assert "ontology" in report

    def test_report_saved_to_disk(self, sample_csv, tmp_path):
        out_dir = str(tmp_path / "output")
        tool = MetadataLineageOntologyTool(data_source=sample_csv, output_dir=out_dir)
        tool.run()
        assert os.path.exists(os.path.join(out_dir, "mlo_report.json"))

    def test_saved_report_is_valid_json(self, sample_csv, tmp_path):
        out_dir = str(tmp_path / "output")
        tool = MetadataLineageOntologyTool(data_source=sample_csv, output_dir=out_dir)
        tool.run()
        with open(os.path.join(out_dir, "mlo_report.json")) as fh:
            data = json.load(fh)
        assert data["metadata"]["row_count"] == 3

    def test_individual_steps_callable_independently(self, sample_csv):
        tool = MetadataLineageOntologyTool(data_source=sample_csv)
        tool.load()
        meta = tool.build_metadata()
        lin = tool.build_lineage()
        ont = tool.build_ontology()
        assert meta.row_count == 3
        assert len(lin.nodes) > 0
        assert len(ont["column_classifications"]) > 0

    def test_file_not_found_raises(self, tmp_path):
        tool = MetadataLineageOntologyTool(
            data_source=str(tmp_path / "nonexistent.csv"),
            output_dir=str(tmp_path),
        )
        with pytest.raises(FileNotFoundError):
            tool.run()
