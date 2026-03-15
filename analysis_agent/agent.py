"""Core Sales Analysis Agent - orchestrates data loading, analysis, and reporting."""

import json
import os
from pathlib import Path

import pandas as pd

from analysis_agent.loader import load_data
from analysis_agent.metrics import (
    SalesMetrics,
    compute_growth_rates,
    compute_metrics,
    correlation_analysis,
    segment_analysis,
)
from analysis_agent.visualizations import (
    plot_correlation_heatmap,
    plot_growth_rates,
    plot_revenue_trend,
    plot_segment_breakdown,
    plot_top_products,
)


class SalesAnalysisAgent:
    """Automated sales data analysis agent.

    Loads sales data, computes key metrics, generates visualizations,
    and produces a summary report.

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
        self._metrics: SalesMetrics | None = None

    @property
    def data(self) -> pd.DataFrame:
        if self._df is None:
            raise RuntimeError("Data not loaded. Call agent.run() or agent.load_data() first.")
        return self._df

    def load_data(self) -> pd.DataFrame:
        """Load and prepare the sales data."""
        self._df = load_data(self.data_source)
        print(f"Loaded {len(self._df)} rows, {len(self._df.columns)} columns from {self.data_source}")
        return self._df

    def analyze(self) -> SalesMetrics:
        """Run core sales metrics analysis."""
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

        # Revenue trend
        if not self._metrics.monthly_trend.empty:
            charts.append(
                plot_revenue_trend(self._metrics.monthly_trend, self.output_dir, self.date_col)
            )

            # Growth rates
            growth = compute_growth_rates(self._metrics.monthly_trend)
            if not growth.empty:
                charts.append(plot_growth_rates(growth, self.output_dir, self.date_col))

        # Top products
        if not self._metrics.top_products.empty:
            charts.append(
                plot_top_products(self._metrics.top_products, self.output_dir, self.product_col)
            )

        # Segment breakdowns
        for seg_col in self.segment_cols:
            if seg_col in self.data.columns:
                seg_df = segment_analysis(self.data, seg_col, self.revenue_col)
                charts.append(plot_segment_breakdown(seg_df, seg_col, self.output_dir))

        # Correlation heatmap
        corr = correlation_analysis(self.data)
        if not corr["matrix"].empty:
            charts.append(plot_correlation_heatmap(corr["matrix"], self.output_dir))

        return charts

    def generate_report(self) -> dict:
        """Build the full analysis report as a dict."""
        if self._metrics is None:
            self.analyze()

        report = {
            "summary": self._metrics.summary(),
            "top_products": (
                self._metrics.top_products.to_dict(orient="records")
                if not self._metrics.top_products.empty
                else []
            ),
            "monthly_trend": (
                self._metrics.monthly_trend.assign(
                    **{self.date_col: self._metrics.monthly_trend[self.date_col].astype(str)}
                ).to_dict(orient="records")
                if not self._metrics.monthly_trend.empty
                and self.date_col in self._metrics.monthly_trend.columns
                else []
            ),
        }

        # Add segment analyses
        for seg_col in self.segment_cols:
            if seg_col in self.data.columns:
                seg_df = segment_analysis(self.data, seg_col, self.revenue_col)
                report[f"segment_{seg_col}"] = seg_df.to_dict(orient="records")

        # Add correlation analysis
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
        """Execute the full analysis pipeline.

        Returns the report dict with summary metrics, top products,
        trends, and paths to generated charts.
        """
        print("=== Sales Analysis Agent ===")

        # Step 1: Load data
        print("\n[1/4] Loading data...")
        self.load_data()

        # Step 2: Compute metrics
        print("[2/4] Computing metrics...")
        self.analyze()
        summary = self._metrics.summary()
        print(f"  Total Revenue: ${summary['total_revenue']:,.2f}")
        print(f"  Transactions:  {summary['num_transactions']}")
        print(f"  Avg Order:     ${summary['avg_order_value']:,.2f}")

        # Step 3: Generate charts
        charts = []
        if generate_charts:
            print("[3/4] Generating visualizations...")
            charts = self.generate_visualizations()
            print(f"  Generated {len(charts)} chart(s)")
        else:
            print("[3/4] Skipping visualizations")

        # Step 4: Build and save report
        print("[4/4] Building report...")
        report = self.generate_report()
        report["charts"] = charts
        report_path = self.save_report(report)
        print(f"  Report saved to {report_path}")

        print("\n=== Analysis Complete ===")
        return report
