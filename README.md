# Sales Data Analysis Agent

Automated sales data analysis agent that loads sales data, computes key metrics, generates visualizations, and produces summary reports — plus a built-in **Metadata / Lineage / Ontology** (MLO) tool to document your data assets.

## Features

- **Data Loading**: Auto-detects CSV and Excel formats, normalizes column names
- **Metrics Engine**: Total revenue, average order value, top products, monthly trends, growth rates
- **Segment Analysis**: Revenue breakdown by any categorical dimension (region, channel, etc.)
- **Visualizations**: Revenue trends, top products, segment pie charts, growth rate charts
- **CLI Interface**: Run analyses directly from the command line
- **MLO Tool**: Extract column metadata, data lineage DAG, and business ontology classifications

## Installation

```bash
# From source
pip install -e .

# Dev dependencies (includes pytest)
pip install -e ".[dev]"
```

## Quick Start

```bash
# Run full sales analysis
analysis-agent analyze data/sample_sales.csv --segments region channel

# Extract metadata, lineage, and ontology
analysis-agent mlo data/sample_sales.csv --segments region channel

# Skip chart generation
analysis-agent analyze data/sample_sales.csv --no-charts
```

## Programmatic Usage

```python
from analysis_agent import SalesAnalysisAgent, MetadataLineageOntologyTool

# Sales analysis
agent = SalesAnalysisAgent(
    data_source="data/sales.csv",
    segment_cols=["region", "channel"],
)
report = agent.run()
print(report["summary"])

# Metadata, lineage & ontology
tool = MetadataLineageOntologyTool(
    data_source="data/sales.csv",
    segment_cols=["region", "channel"],
)
mlo_report = tool.run()
# Saves output/mlo_report.json with:
#   mlo_report["metadata"]  — per-column stats & dataset facts
#   mlo_report["lineage"]   — DAG of source → transforms → output
#   mlo_report["ontology"]  — column roles, semantic types & term mappings
```

## MLO Report Structure

```
output/mlo_report.json
├── metadata
│   ├── source_path, file_format, file_size_bytes, row_count, column_count
│   └── columns[]  — name, dtype, nullable, null_count, unique_count,
│                    sample_values, description, tags, stats, temporal_range
├── lineage
│   ├── nodes[]  — source / transform / output nodes in the pipeline DAG
│   └── edges[]  — directed transformations between nodes
└── ontology
    ├── schema   — 17-term sales domain ontology (product, region, channel, …)
    ├── column_classifications[]  — role, semantic_type, ontology_term, relationships
    └── summary  — matched vs. unmatched column counts
```

## Running Tests

```bash
pytest
```
