# Sales Analysis Dashboard — User Guide

## Quick Start

```bash
# 1. Navigate to the project
cd ~/Sales

# 2. Launch the dashboard
python -m analysis_agent.dashboard
```

This opens **http://localhost:8080** in your browser automatically.

---

## Uploading Data

### Upload Actuals (OTIF / Sales Data)
1. Click **Upload Data** in the header
2. Select your CSV or Excel file
3. The agent auto-detects the data type (supply chain vs revenue) and runs the full analysis
4. Dashboard updates with metric cards, charts, tables, and correlation analysis

### Upload AOP Plan (for Plan vs Actual Comparison)
1. First upload your actuals data using **Upload Data**
2. Then click **Upload Plan** and select your AOP file
3. The dashboard re-runs the analysis and adds a **Plan vs Actual Comparison** section with:
   - Plan Units, Actual Orders, Order Attainment %, Delivery Attainment %
   - Monthly comparison table
   - Plan vs Actual trend chart, Attainment trend, Variance waterfall, Corp comparison

---

## Supported Data Formats

### Supply Chain / OTIF Data
Expected columns (flexible naming — auto-detected):
| Column | Example |
|--------|---------|
| Corp Name | COSTCO, WALMART |
| OTIF % | 95%, 98% |
| Fill % | 97%, 99% |
| Order Qty | "17,492" |
| Total Delivered Qty | "17,088" |
| Not Delivered | 404 |
| Group Size | 24F, 65 |
| Reporting Date - Month | December |
| Reporting Date - Year | 2025 |

### Revenue / Sales Data
Expected columns:
| Column | Example |
|--------|---------|
| date | 2025-01-15 |
| product | Widget A |
| quantity | 10 |
| revenue | 500.00 |
| region (optional) | North |

### AOP Plan Data
Expected columns:
| Column | Example |
|--------|---------|
| Aop Reporting Date | 2025-10-01 |
| Aop Sales Units | 500 |
| Corp | COSTCO |
| Commercial Segment (optional) | Retail |
| Distributor Name (optional) | COSTCO WHOLESALE |
| Product Num (optional) | P001 |

---

## CLI Usage (without the dashboard)

```bash
# Analyze supply chain data
python -m analysis_agent data/sample_supply_chain.csv -o output

# Analyze with segment breakdown
python -m analysis_agent data/sample_supply_chain.csv -o output --segments dealer_state

# Analyze revenue data
python -m analysis_agent data/sample_sales.csv -o output --segments region channel

# Plan vs Actual comparison
python -m analysis_agent data/sample_supply_chain.csv -o output --plan-file data/sample_aop.csv

# Skip chart generation (faster)
python -m analysis_agent data/sample_supply_chain.csv -o output --no-charts
```

### All CLI Arguments
| Argument | Default | Description |
|----------|---------|-------------|
| `data_file` | (required) | Path to CSV or Excel file |
| `-o, --output` | output | Output directory |
| `--revenue-col` | revenue | Revenue column name |
| `--quantity-col` | quantity | Quantity column name |
| `--date-col` | date | Date column name |
| `--product-col` | product | Product column name |
| `--segments` | (none) | Segment columns for breakdowns |
| `--no-charts` | false | Skip chart generation |
| `--plan-file` | (none) | AOP plan file path |

---

## Dashboard Features

- **Auto-detection**: Automatically identifies supply chain vs revenue data
- **Metric Cards**: Key KPIs displayed at the top (OTIF%, Fill Rate, Revenue, etc.)
- **Charts**: Revenue trends, top products, OTIF/Fill trends, corp performance, growth rates, correlation heatmap
- **Correlation Analysis**: Finds and displays strong correlations between numeric columns
- **Plan vs Actual**: Side-by-side comparison of AOP targets vs actual orders/deliveries
- **Refresh**: Click Refresh to reload the latest report without re-uploading
- **Last Refresh Timestamp**: Shows when data was last loaded

---

## Dashboard Port Options

```bash
# Default port 8080
python -m analysis_agent.dashboard

# Custom port
python -m analysis_agent.dashboard -p 3000

# Custom output directory
python -m analysis_agent.dashboard -o my_reports -p 9000
```

---

## Sample Data

The project includes sample files for testing:

```bash
# Supply chain sample (16 rows, 4 corps, OTIF/Fill metrics)
data/sample_supply_chain.csv

# Revenue sample (basic sales transactions)
data/sample_sales.csv

# AOP plan sample (32 rows, 4 corps, 4 months)
data/sample_aop.csv
```

Try it:
```bash
python -m analysis_agent data/sample_supply_chain.csv -o output --plan-file data/sample_aop.csv
python -m analysis_agent.dashboard -o output
```
