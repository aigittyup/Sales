"""CLI entry point for the Sales Analysis Agent."""

import argparse
import sys


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("data_file", help="Path to sales data file (CSV or Excel)")
    parser.add_argument("-o", "--output", default="output", help="Output directory (default: output)")
    parser.add_argument("--revenue-col", default="revenue", help="Revenue column name")
    parser.add_argument("--quantity-col", default="quantity", help="Quantity column name")
    parser.add_argument("--date-col", default="date", help="Date column name")
    parser.add_argument("--product-col", default="product", help="Product column name")
    parser.add_argument("--segments", nargs="*", default=[], help="Segment columns for breakdown analysis")


def _run_analyze(args: argparse.Namespace) -> int:
    from analysis_agent.agent import SalesAnalysisAgent

    agent = SalesAnalysisAgent(
        data_source=args.data_file,
        output_dir=args.output,
        revenue_col=args.revenue_col,
        quantity_col=args.quantity_col,
        date_col=args.date_col,
        product_col=args.product_col,
        segment_cols=args.segments,
    )
    report = agent.run(generate_charts=not args.no_charts)

    print("\n--- Summary ---")
    for key, value in report["summary"].items():
        print(f"  {key}: {value}")
    return 0


def _run_mlo(args: argparse.Namespace) -> int:
    from analysis_agent.mlo_tool import MetadataLineageOntologyTool

    tool = MetadataLineageOntologyTool(
        data_source=args.data_file,
        output_dir=args.output,
        revenue_col=args.revenue_col,
        quantity_col=args.quantity_col,
        date_col=args.date_col,
        product_col=args.product_col,
        segment_cols=args.segments,
    )
    report = tool.run()

    print("\n--- Metadata Summary ---")
    meta = report["metadata"]
    print(f"  Rows: {meta['row_count']}  |  Columns: {meta['column_count']}")
    print(f"  Format: {meta['file_format']}  |  Size: {meta['file_size_bytes']:,} bytes")

    print("\n--- Lineage Graph ---")
    lin = report["lineage"]
    print(f"  Nodes: {len(lin['nodes'])}  |  Edges: {len(lin['edges'])}")
    for node in lin["nodes"]:
        print(f"  [{node['node_type']:10s}] {node['name']}")

    print("\n--- Ontology Classifications ---")
    for cls in report["ontology"]["column_classifications"]:
        term = cls["ontology_term"] or "(unmatched)"
        print(f"  {cls['column']:20s}  role={cls['role']:12s}  type={cls['semantic_type']:12s}  term={term}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sales Data Analysis Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Commands:\n"
            "  analyze  Run full sales metrics analysis and generate charts\n"
            "  mlo      Extract metadata, lineage, and ontology for the dataset\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    # ------------------------------------------------------------------ analyze
    analyze_parser = subparsers.add_parser("analyze", help="Run sales metrics analysis")
    _add_common_args(analyze_parser)
    analyze_parser.add_argument("--no-charts", action="store_true", help="Skip chart generation")

    # ------------------------------------------------------------------ mlo
    mlo_parser = subparsers.add_parser(
        "mlo",
        help="Extract metadata, data lineage, and ontology for the dataset",
    )
    _add_common_args(mlo_parser)

    args = parser.parse_args()

    if args.command == "analyze":
        return _run_analyze(args)
    if args.command == "mlo":
        return _run_mlo(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
