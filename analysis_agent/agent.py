"""Core Sales Analysis Agent - orchestrates data loading, analysis, and reporting."""

import json
import os
from pathlib import Path
from typing import Union

import pandas as pd

from analysis_agent.loader import load_data
from analysis_agent.metrics import (
    SalesMetrics,
    SupplyChainMetrics,
    compute_growth_rates,
    compute_metrics,
    compute_supply_chain_metrics,
    correlation_analysis,
    detect_data_type,
    segment_analysis,
)
from analysis_agent.visualizations import (
    plot_correlation_heatmap,
    plot_corp_performance,
    plot_group_performance,
    plot_growth_rates,
    plot_order_volume_trend,
    plot_otif_fill_trend,
    plot_revenue_trend,
    plot_segment_breakdown,
    plot_top_products,
)


class SalesAnalysisAgent:
    """Automated sales data analysis agent.

    Auto-detects data type (revenue vs supply chain) and runs the
    appropriate analysis pipeline.

    Usage:
        agent = SalesAnalysisAgent("data/sales.csv")
        report = agent.run()
        print(report["summary"])
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
    ):
        self.data_source = data_source
        self.output_dir = output_dir
        self.revenue_col = revenue_col
        self.quantity_col = quantity_col
        self.date_col = date_col
        self.product_col = product_col
        self.segment_cols = segment_cols or []

        self._df: pd.DataFrame | None = None
        self._metrics: Union[SalesMetrics, SupplyChainMetrics, None] = None
        self._data_type: str | None = None

    @property
    def data(self) -> pd.DataFrame:
        if self._df is None:
            raise RuntimeError("Data not loaded. Call agent.run() or agent.load_data() first.")
        return self._df

    def load_data(self) -> pd.DataFrame:
        """Load and prepare the sales data."""
        self._df = load_data(self.data_source)
        self._data_type = detect_data_type(self._df)
        print(f"Loaded {len(self._df)} rows, {len(self._df.columns)} columns from {self.data_source}")
        print(f"  Detected data type: {self._data_type}")
        return self._df

    def analyze(self) -> Union[SalesMetrics, SupplyChainMetrics]:
        """Run analysis based on detected data type."""
        if self._data_type == "supply_chain":
            self._metrics = compute_supply_chain_metrics(
                self.data,
                date_col=self.date_col,
            )
        else:
            self._metrics = compute_metrics(
                self.data,
                revenue_col=self.revenue_col,
                quantity_col=self.quantity_col,
                date_col=self.date_col,
                product_col=self.product_col,
            )
        return self._metrics

    def generate_visualizations(self) -> list[str]:
        """Generate all applicable charts and return file paths."""
        os.makedirs(self.output_dir, exist_ok=True)
        charts = []

        if self._metrics is None:
            self.analyze()

        if self._data_type == "supply_chain":
            charts.extend(self._generate_supply_chain_charts())
        else:
            charts.extend(self._generate_revenue_charts())

        # Correlation heatmap (works for both types)
        corr = correlation_analysis(self.data)
        if not corr["matrix"].empty:
            charts.append(plot_correlation_heatmap(corr["matrix"], self.output_dir))

        return charts

    def _generate_revenue_charts(self) -> list[str]:
        charts = []
        metrics = self._metrics

        if not metrics.monthly_trend.empty:
            charts.append(
                plot_revenue_trend(metrics.monthly_trend, self.output_dir, self.date_col)
            )
            growth = compute_growth_rates(metrics.monthly_trend)
            if not growth.empty:
                charts.append(plot_growth_rates(growth, self.output_dir, self.date_col))

        if not metrics.top_products.empty:
            charts.append(
                plot_top_products(metrics.top_products, self.output_dir, self.product_col)
            )

        for seg_col in self.segment_cols:
            if seg_col in self.data.columns:
                seg_df = segment_analysis(self.data, seg_col, self.revenue_col)
                charts.append(plot_segment_breakdown(seg_df, seg_col, self.output_dir))

        return charts

    def _generate_supply_chain_charts(self) -> list[str]:
        charts = []
        metrics = self._metrics

        if not metrics.monthly_trend.empty:
            charts.append(
                plot_otif_fill_trend(metrics.monthly_trend, self.output_dir, self.date_col)
            )
            charts.append(
                plot_order_volume_trend(metrics.monthly_trend, self.output_dir, self.date_col)
            )

        if not metrics.by_corp.empty:
            charts.append(plot_corp_performance(metrics.by_corp, self.output_dir))

        if not metrics.by_group.empty:
            charts.append(plot_group_performance(metrics.by_group, self.output_dir))

        # Segment breakdowns
        for seg_col in self.segment_cols:
            if seg_col in self.data.columns:
                seg_df = segment_analysis(self.data, seg_col)
                charts.append(plot_segment_breakdown(seg_df, seg_col, self.output_dir))

        return charts

    def generate_report(self) -> dict:
        """Build the full analysis report as a dict."""
        if self._metrics is None:
            self.analyze()

        report = {
            "data_type": self._data_type,
            "summary": self._metrics.summary(),
        }

        if self._data_type == "supply_chain":
            report["by_corp"] = (
                self._metrics.by_corp.to_dict(orient="records")
                if not self._metrics.by_corp.empty else []
            )
            report["by_group"] = (
                self._metrics.by_group.to_dict(orient="records")
                if not self._metrics.by_group.empty else []
            )
            if not self._metrics.monthly_trend.empty and self.date_col in self._metrics.monthly_trend.columns:
                report["monthly_trend"] = (
                    self._metrics.monthly_trend.assign(
                        **{self.date_col: self._metrics.monthly_trend[self.date_col].astype(str)}
                    ).to_dict(orient="records")
                )
            else:
                report["monthly_trend"] = []
        else:
            report["top_products"] = (
                self._metrics.top_products.to_dict(orient="records")
                if not self._metrics.top_products.empty else []
            )
            if not self._metrics.monthly_trend.empty and self.date_col in self._metrics.monthly_trend.columns:
                report["monthly_trend"] = (
                    self._metrics.monthly_trend.assign(
                        **{self.date_col: self._metrics.monthly_trend[self.date_col].astype(str)}
                    ).to_dict(orient="records")
                )
            else:
                report["monthly_trend"] = []

        # Segment analyses
        for seg_col in self.segment_cols:
            if seg_col in self.data.columns:
                seg_df = segment_analysis(self.data, seg_col)
                report[f"segment_{seg_col}"] = seg_df.to_dict(orient="records")

        # Correlation
        corr = correlation_analysis(self.data)
        if not corr["matrix"].empty:
            report["correlation"] = {
                "matrix": corr["matrix"].round(4).to_dict(),
                "strong_correlations": corr["strong_correlations"],
            }

        return report

    def save_report(self, report: dict) -> str:
        """Save the report to a JSON file."""
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, "sales_report.json")
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)
        return filepath

    def run(self, generate_charts: bool = True) -> dict:
        """Execute the full analysis pipeline."""
        print("=== Sales Analysis Agent ===")

        print("\n[1/4] Loading data...")
        self.load_data()

        print("[2/4] Computing metrics...")
        self.analyze()
        summary = self._metrics.summary()

        if self._data_type == "supply_chain":
            print(f"  Total Orders:    {summary['total_order_qty']:,}")
            print(f"  Total Delivered: {summary['total_delivered']:,}")
            print(f"  Avg OTIF:        {summary['avg_otif_pct']}%")
            print(f"  Avg Fill Rate:   {summary['avg_fill_pct']}%")
        else:
            print(f"  Total Revenue: ${summary['total_revenue']:,.2f}")
            print(f"  Transactions:  {summary['num_transactions']}")
            print(f"  Avg Order:     ${summary['avg_order_value']:,.2f}")

        charts = []
        if generate_charts:
            print("[3/4] Generating visualizations...")
            charts = self.generate_visualizations()
            print(f"  Generated {len(charts)} chart(s)")
        else:
            print("[3/4] Skipping visualizations")

        print("[4/4] Building report...")
        report = self.generate_report()
        report["charts"] = charts
        report_path = self.save_report(report)
        print(f"  Report saved to {report_path}")

        print("\n=== Analysis Complete ===")
        return report
