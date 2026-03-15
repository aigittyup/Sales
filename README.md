# Sales Data Analysis Agent

Automated sales data analysis agent that loads sales data, computes key metrics, generates visualizations, and produces summary reports.

## Features

- **Data Loading**: Auto-detects CSV and Excel formats, normalizes column names
- **Metrics Engine**: Total revenue, average order value, top products, monthly trends, growth rates
- **Segment Analysis**: Revenue breakdown by any categorical dimension (region, channel, etc.)
- **Visualizations**: Revenue trends, top products, segment pie charts, growth rate charts
- **CLI Interface**: Run analyses directly from the command line

## Quick Start

```bash
pip install -r requirements.txt

# Run analysis on your sales data
python -m analysis_agent data/sample_sales.csv --segments region channel

# Skip chart generation
python -m analysis_agent data/sample_sales.csv --no-charts
```

## Programmatic Usage

```python
from analysis_agent import SalesAnalysisAgent

agent = SalesAnalysisAgent(
    data_source="data/sales.csv",
    segment_cols=["region", "channel"],
)
report = agent.run()
print(report["summary"])
```

## Running Tests

```bash
pip install pytest
pytest tests/
```
