"""Metadata, Lineage, and Ontology (MLO) tool for sales data."""

import json
import os
from typing import Any

import pandas as pd

from analysis_agent.lineage import DataLineageTracker
from analysis_agent.loader import load_data
from analysis_agent.metadata import DatasetMetadata, extract_metadata
from analysis_agent.ontology import SalesOntology


class MetadataLineageOntologyTool:
    """Builds metadata, data lineage, and ontology for a sales dataset.

    Three lenses on the same data:

    * **Metadata** – per-column stats (dtype, nulls, min/max/mean, samples) and
      dataset-level facts (row count, file size, extraction timestamp).

    * **Lineage** – a directed graph of how raw data flows through the analysis
      pipeline: source file → normalization → metrics → segments → final report.

    * **Ontology** – maps every column to a known sales business concept
      (product, region, revenue, …) and classifies its role (dimension, measure,
      temporal, identifier).

    The combined report is saved as ``<output_dir>/mlo_report.json``.

    Usage::

        tool = MetadataLineageOntologyTool("data/sales.csv", segment_cols=["region", "channel"])
        report = tool.run()
    """

    def __init__(
        self,
        data_source: str,
        output_dir: str = "output",
        revenue_col: str = "revenue",
        quantity_col: str = "quantity",
        date_col: str = "date",
        product_col: str = "product",
        segment_cols: list[str] | None = None,
    ) -> None:
        self.data_source = data_source
        self.output_dir = output_dir
        self.revenue_col = revenue_col
        self.quantity_col = quantity_col
        self.date_col = date_col
        self.product_col = product_col
        self.segment_cols = segment_cols or []

        self._df: pd.DataFrame | None = None

    @property
    def data(self) -> pd.DataFrame:
        if self._df is None:
            raise RuntimeError("Data not loaded. Call run() or load() first.")
        return self._df

    # ------------------------------------------------------------------
    # Pipeline steps (public so callers can use them independently)
    # ------------------------------------------------------------------

    def load(self) -> pd.DataFrame:
        """Load the data source into a DataFrame."""
        self._df = load_data(self.data_source)
        return self._df

    def build_metadata(self) -> DatasetMetadata:
        """Extract column-level and dataset-level metadata."""
        return extract_metadata(self.data, self.data_source)

    def build_lineage(self) -> DataLineageTracker:
        """Build the data lineage DAG for the standard sales pipeline."""
        tracker = DataLineageTracker()
        tracker.build_pipeline_lineage(
            self.data,
            source_path=self.data_source,
            revenue_col=self.revenue_col,
            quantity_col=self.quantity_col,
            date_col=self.date_col,
            product_col=self.product_col,
            segment_cols=self.segment_cols,
        )
        return tracker

    def build_ontology(self) -> dict[str, Any]:
        """Classify columns against the sales business ontology."""
        ontology = SalesOntology()
        classifications = ontology.classify_columns(self.data)
        matched = sum(1 for c in classifications if c.ontology_term)
        return {
            "schema": ontology.to_dict(),
            "column_classifications": [c.to_dict() for c in classifications],
            "summary": {
                "total_columns": len(classifications),
                "matched_to_ontology": matched,
                "unmatched": len(classifications) - matched,
            },
        }

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def run(self) -> dict[str, Any]:
        """Execute the full MLO pipeline and save the report.

        Returns the complete report dict with ``metadata``, ``lineage``,
        and ``ontology`` sections.
        """
        print("=== Metadata, Lineage & Ontology Tool ===")

        print("\n[1/4] Loading data...")
        self.load()
        print(f"  {len(self.data)} rows, {len(self.data.columns)} columns from {self.data_source}")

        print("[2/4] Extracting metadata...")
        metadata = self.build_metadata()
        nullable = sum(1 for c in metadata.columns if c.nullable)
        print(f"  {metadata.column_count} columns | {nullable} nullable | {metadata.file_size_bytes:,} bytes")

        print("[3/4] Building data lineage...")
        lineage = self.build_lineage()
        print(f"  {len(lineage.nodes)} nodes, {len(lineage.edges)} edges in the lineage graph")

        print("[4/4] Applying business ontology...")
        ontology_result = self.build_ontology()
        s = ontology_result["summary"]
        print(f"  {s['matched_to_ontology']}/{s['total_columns']} columns matched to ontology terms")

        report: dict[str, Any] = {
            "metadata": metadata.to_dict(),
            "lineage": lineage.to_dict(),
            "ontology": ontology_result,
        }

        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "mlo_report.json")
        with open(output_path, "w") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"\n  Report saved → {output_path}")
        print("=== MLO Analysis Complete ===")

        return report
