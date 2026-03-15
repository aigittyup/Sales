"""CLI entry point for the Sales Analysis Agent."""

import argparse
import sys

from analysis_agent.agent import SalesAnalysisAgent


def main():
    parser = argparse.ArgumentParser(description="Sales Data Analysis Agent")
    parser.add_argument("data_file", help="Path to sales data file (CSV or Excel)")
    parser.add_argument("-o", "--output", default="output", help="Output directory (default: output)")
    parser.add_argument("--revenue-col", default="revenue", help="Revenue column name")
    parser.add_argument("--quantity-col", default="quantity", help="Quantity column name")
    parser.add_argument("--date-col", default="date", help="Date column name")
    parser.add_argument("--product-col", default="product", help="Product column name")
    parser.add_argument("--segments", nargs="*", default=[], help="Segment columns for breakdown analysis")
    parser.add_argument("--no-charts", action="store_true", help="Skip chart generation")
    parser.add_argument("--plan-file", default=None, help="AOP plan file for plan vs actual comparison")

    args = parser.parse_args()

    agent = SalesAnalysisAgent(
        data_source=args.data_file,
        output_dir=args.output,
        revenue_col=args.revenue_col,
        quantity_col=args.quantity_col,
        date_col=args.date_col,
        product_col=args.product_col,
        segment_cols=args.segments,
        plan_file=args.plan_file,
    )

    report = agent.run(generate_charts=not args.no_charts)

    print("\n--- Summary ---")
    for key, value in report["summary"].items():
        print(f"  {key}: {value}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
