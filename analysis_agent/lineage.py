"""Data lineage tracking for the sales analysis pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass
class LineageNode:
    """A node in the data lineage graph (source, transform, or output)."""

    node_id: str
    node_type: str  # "source" | "transform" | "output"
    name: str
    description: str
    columns: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "description": self.description,
            "columns": self.columns,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class LineageEdge:
    """A directed edge between two lineage nodes describing a transformation."""

    source_id: str
    target_id: str
    transformation: str
    columns_in: list[str]
    columns_out: list[str]
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "transformation": self.transformation,
            "columns_in": self.columns_in,
            "columns_out": self.columns_out,
            "description": self.description,
        }


class DataLineageTracker:
    """Tracks data transformations and flow through the analysis pipeline.

    Builds a directed acyclic graph (DAG) of nodes (datasets/steps) and
    edges (transformations) representing how data moves and changes.

    Usage:
        tracker = DataLineageTracker()
        tracker.build_pipeline_lineage(df, source_path="data/sales.csv")
        report = tracker.to_dict()
    """

    def __init__(self) -> None:
        self.nodes: dict[str, LineageNode] = {}
        self.edges: list[LineageEdge] = []

    def add_node(
        self,
        node_id: str,
        node_type: str,
        name: str,
        description: str,
        columns: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> LineageNode:
        node = LineageNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            description=description,
            columns=columns,
            metadata=metadata or {},
        )
        self.nodes[node_id] = node
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        transformation: str,
        columns_in: list[str],
        columns_out: list[str],
        description: str = "",
    ) -> LineageEdge:
        edge = LineageEdge(
            source_id=source_id,
            target_id=target_id,
            transformation=transformation,
            columns_in=columns_in,
            columns_out=columns_out,
            description=description,
        )
        self.edges.append(edge)
        return edge

    def build_pipeline_lineage(
        self,
        df: pd.DataFrame,
        source_path: str,
        revenue_col: str = "revenue",
        quantity_col: str = "quantity",
        date_col: str = "date",
        product_col: str = "product",
        segment_cols: list[str] | None = None,
    ) -> "DataLineageTracker":
        """Auto-build the lineage graph for the standard sales analysis pipeline."""
        segment_cols = segment_cols or []
        raw_cols = list(df.columns)

        # Node: raw file source
        self.add_node(
            "source_file",
            "source",
            f"Raw File: {source_path}",
            f"Original data file loaded from {source_path}",
            raw_cols,
            {"path": source_path},
        )

        # Node: column normalization
        self.add_node(
            "normalized",
            "transform",
            "Column Normalization",
            "Column names converted to snake_case; date columns parsed to datetime",
            raw_cols,
        )
        self.add_edge(
            "source_file", "normalized",
            "normalize_columns",
            raw_cols, raw_cols,
            "Strip whitespace, lowercase, replace special chars with underscores; "
            "auto-detect and parse date columns",
        )

        # Node: core metrics aggregation
        metric_inputs = [c for c in [revenue_col, quantity_col, date_col, product_col] if c in df.columns]
        metric_outputs = [
            "total_revenue", "total_units", "avg_order_value",
            "median_order_value", "num_transactions", "revenue_std",
            "top_products", "monthly_trend",
        ]
        self.add_node(
            "core_metrics",
            "transform",
            "Core Sales Metrics",
            "Aggregate revenue, units, average order value, and monthly trend from raw transactions",
            metric_outputs,
        )
        self.add_edge(
            "normalized", "core_metrics",
            "compute_metrics",
            metric_inputs, metric_outputs,
            "sum/count/mean revenue; monthly resample (ME); top-N products by revenue",
        )

        # Node: month-over-month growth rates
        growth_outputs = ["date", "total_revenue", "mom_growth_pct", "cumulative_revenue"]
        self.add_node(
            "growth_rates",
            "transform",
            "Monthly Growth Rates",
            "Month-over-month revenue growth percentages derived from the monthly trend",
            growth_outputs,
        )
        self.add_edge(
            "core_metrics", "growth_rates",
            "compute_growth_rates",
            ["monthly_trend"], growth_outputs,
            "pct_change() on monthly revenue; cumulative sum for running total",
        )

        # Nodes: per-segment analyses
        for seg_col in segment_cols:
            if seg_col in df.columns:
                seg_id = f"segment_{seg_col}"
                seg_outputs = [
                    seg_col, "total_revenue", "num_orders",
                    "avg_order_value", "revenue_std", "revenue_share_pct",
                ]
                self.add_node(
                    seg_id,
                    "transform",
                    f"Segment Analysis: {seg_col}",
                    f"Revenue breakdown grouped by {seg_col}",
                    seg_outputs,
                )
                self.add_edge(
                    "normalized", seg_id,
                    "segment_analysis",
                    [seg_col, revenue_col], seg_outputs,
                    f"groupby('{seg_col}')['{revenue_col}'].agg([sum, count, mean, std]); "
                    "add revenue_share_pct",
                )

        # Node: final JSON report output
        upstream_ids = (
            ["core_metrics", "growth_rates"]
            + [f"segment_{s}" for s in segment_cols if s in df.columns]
        )
        report_columns = (
            ["summary", "top_products", "monthly_trend", "growth_rates"]
            + [f"segment_{s}" for s in segment_cols if s in df.columns]
        )
        self.add_node(
            "sales_report",
            "output",
            "Sales Report (JSON)",
            "Final JSON report combining all metrics, trends, and segment analyses",
            report_columns,
            {"format": "json", "filename": "sales_report.json"},
        )
        for src_id in upstream_ids:
            self.add_edge(
                src_id, "sales_report",
                "aggregate_report",
                list(self.nodes[src_id].columns), report_columns,
                "Merge all computed metrics into a single JSON document",
            )

        return self

    def get_upstream(self, node_id: str) -> list[str]:
        """Return all node IDs that feed into the given node (direct parents)."""
        return [e.source_id for e in self.edges if e.target_id == node_id]

    def get_downstream(self, node_id: str) -> list[str]:
        """Return all node IDs that the given node feeds into (direct children)."""
        return [e.target_id for e in self.edges if e.source_id == node_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }
