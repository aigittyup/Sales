"""Integration tests - validates the full pipeline end-to-end."""

import json
import math
import os
import threading
import time
import urllib.request
import urllib.parse

import pandas as pd
import pytest

from analysis_agent.agent import SalesAnalysisAgent
from analysis_agent.loader import load_data
from analysis_agent.metrics import (
    compute_metrics,
    compute_supply_chain_metrics,
    correlation_analysis,
    detect_data_type,
    segment_analysis,
)
from analysis_agent.plan_comparison import (
    compare_plan_vs_actual,
    load_actuals_data,
    load_aop_data,
)


# --- Loader tests ---

class TestLoaderFormats:
    def test_percentage_strings_parsed(self, tmp_path):
        csv = tmp_path / "pct.csv"
        csv.write_text("name,rate\nA,95%\nB,100%\nC,87.5%\n")
        df = load_data(str(csv))
        assert df["rate"].dtype == float
        assert df["rate"].iloc[0] == 0.95
        assert df["rate"].iloc[2] == 0.875

    def test_comma_numbers_parsed(self, tmp_path):
        csv = tmp_path / "nums.csv"
        csv.write_text('item,qty\nA,"17,492"\nB,"1,200"\n')
        df = load_data(str(csv))
        assert df["qty"].iloc[0] == 17492
        assert df["qty"].iloc[1] == 1200

    def test_month_year_combined(self, tmp_path):
        csv = tmp_path / "dates.csv"
        csv.write_text("val,Reporting Date - Month,Reporting Date - Year\n1,December,2025\n2,September,2025\n")
        df = load_data(str(csv))
        assert "date" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        assert df["date"].iloc[0].month == 12
        assert df["date"].iloc[0].year == 2025

    def test_delivery_columns_not_parsed_as_dates(self, tmp_path):
        csv = tmp_path / "sc.csv"
        csv.write_text('Corp,Order Qty,On Time Delivered Qty,Not Delivered by Due Date,Total Delivered Qty\nA,"1,000",950,50,960\n')
        df = load_data(str(csv))
        assert df["on_time_delivered_qty"].dtype in (int, "int64")
        assert df["not_delivered_by_due_date"].dtype in (int, "int64")
        assert df["total_delivered_qty"].dtype in (int, "int64")

    def test_unsupported_format_raises(self, tmp_path):
        txt = tmp_path / "bad.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported"):
            load_data(str(txt))

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_data("/nonexistent/path.csv")


# --- Data type detection ---

class TestDetectDataType:
    def test_detects_supply_chain(self):
        df = pd.DataFrame({"otif": [0.95], "fill": [0.98], "order_qty": [100], "total_delivered_qty": [95]})
        assert detect_data_type(df) == "supply_chain"

    def test_detects_revenue(self):
        df = pd.DataFrame({"revenue": [100], "quantity": [5], "product": ["A"]})
        assert detect_data_type(df) == "revenue"


# --- Metrics ---

class TestSupplyChainMetrics:
    @pytest.fixture
    def sc_df(self):
        return pd.DataFrame({
            "corp_name": ["A", "A", "B", "B"],
            "otif": [0.95, 0.98, 0.92, 0.96],
            "fill": [0.97, 0.99, 0.94, 0.97],
            "order_qty": [1000, 2000, 1500, 1800],
            "total_delivered_qty": [970, 1980, 1410, 1746],
            "not_delivered": [30, 20, 90, 54],
            "group_size": ["24F", "65", "24F", "65"],
            "date": pd.to_datetime(["2025-10-01", "2025-10-01", "2025-11-01", "2025-11-01"]),
        })

    def test_totals(self, sc_df):
        m = compute_supply_chain_metrics(sc_df)
        assert m.total_order_qty == 6300
        assert m.total_delivered == 6106
        assert m.num_records == 4

    def test_averages(self, sc_df):
        m = compute_supply_chain_metrics(sc_df)
        assert 0.9 < m.avg_otif_pct < 1.0
        assert 0.9 < m.avg_fill_pct < 1.0

    def test_by_corp(self, sc_df):
        m = compute_supply_chain_metrics(sc_df)
        assert len(m.by_corp) == 2

    def test_monthly_trend(self, sc_df):
        m = compute_supply_chain_metrics(sc_df)
        assert len(m.monthly_trend) == 2

    def test_summary_keys(self, sc_df):
        m = compute_supply_chain_metrics(sc_df)
        s = m.summary()
        required = ["total_order_qty", "total_delivered", "avg_otif_pct", "avg_fill_pct", "period"]
        for k in required:
            assert k in s, f"Missing key: {k}"


class TestCorrelation:
    def test_finds_strong_correlation(self):
        df = pd.DataFrame({"a": range(10), "b": range(10), "c": [9 - x for x in range(10)]})
        result = correlation_analysis(df)
        assert len(result["strong_correlations"]) >= 2
        # a and b should be perfectly correlated
        ab = next(c for c in result["strong_correlations"] if set([c["col_1"], c["col_2"]]) == {"a", "b"})
        assert ab["correlation"] > 0.99

    def test_no_strong_with_random(self):
        import numpy as np
        np.random.seed(42)
        df = pd.DataFrame({"a": np.random.randn(100), "b": np.random.randn(100)})
        result = correlation_analysis(df)
        assert len(result["strong_correlations"]) == 0

    def test_single_column_returns_empty(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = correlation_analysis(df)
        assert result["matrix"].empty


# --- Full pipeline ---

class TestFullPipeline:
    def test_supply_chain_pipeline(self, tmp_path):
        csv = tmp_path / "sc.csv"
        csv.write_text(
            'Corp Name,OTIF %,Fill %,Order Qty,Total Delivered Qty,Not Delivered,Group Size,Reporting Date - Month,Reporting Date - Year\n'
            'ACME,95%,97%,"10,000","9,700",300,24F,October,2025\n'
            'ACME,98%,99%,"8,000","7,920",80,65,November,2025\n'
            'BETA,92%,94%,"12,000","11,280",720,24F,October,2025\n'
            'BETA,96%,97%,"9,500","9,215",285,65,November,2025\n'
        )
        agent = SalesAnalysisAgent(str(csv), output_dir=str(tmp_path / "out"))
        report = agent.run(generate_charts=True)

        # Verify report structure
        assert report["data_type"] == "supply_chain"
        assert report["summary"]["total_order_qty"] == 39500
        assert len(report["by_corp"]) == 2
        assert len(report["monthly_trend"]) == 2
        assert "correlation" in report

        # Verify charts were created
        assert len(report["charts"]) > 0
        for chart_path in report["charts"]:
            assert os.path.exists(chart_path), f"Chart not found: {chart_path}"

        # Verify report JSON is valid (no NaN)
        report_json = (tmp_path / "out" / "sales_report.json").read_text()
        parsed = json.loads(report_json)  # Should not raise
        assert "NaN" not in report_json, "JSON contains NaN — will break browser"

    def test_revenue_pipeline(self, tmp_path):
        csv = tmp_path / "rev.csv"
        csv.write_text(
            "date,product,quantity,revenue,region\n"
            "2025-01-01,A,10,500,North\n"
            "2025-01-15,B,5,300,South\n"
            "2025-02-01,A,8,400,North\n"
            "2025-02-15,B,12,600,South\n"
        )
        agent = SalesAnalysisAgent(str(csv), output_dir=str(tmp_path / "out"), segment_cols=["region"])
        report = agent.run(generate_charts=True)

        assert report["data_type"] == "revenue"
        assert report["summary"]["total_revenue"] == 1800.0
        assert len(report["top_products"]) == 2
        assert len(report["charts"]) > 0

        report_json = (tmp_path / "out" / "sales_report.json").read_text()
        assert "NaN" not in report_json


# --- JSON validity ---

class TestJSONValidity:
    def test_report_json_has_no_nan(self):
        """Run the sample supply chain data and verify JSON is browser-safe."""
        sample = os.path.join(os.path.dirname(__file__), "..", "data", "sample_supply_chain.csv")
        if not os.path.exists(sample):
            pytest.skip("Sample data not found")

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SalesAnalysisAgent(sample, output_dir=tmpdir, segment_cols=["dealer_state"])
            report = agent.run(generate_charts=False)
            report_path = os.path.join(tmpdir, "sales_report.json")
            with open(report_path) as f:
                text = f.read()

            assert "NaN" not in text, "JSON contains NaN"
            assert "Infinity" not in text, "JSON contains Infinity"
            parsed = json.loads(text)  # Must not raise
            assert parsed["data_type"] in ("supply_chain", "revenue")


# --- Dashboard HTML validity ---

class TestDashboardHTML:
    def test_html_has_no_broken_regex(self):
        """Verify JS regex patterns survive Python string escaping."""
        from analysis_agent.dashboard import DASHBOARD_HTML
        # Check that the chart path splitter is valid JS
        assert "path.split(/[" in DASHBOARD_HTML
        # No unescaped single backslash in regex that would break JS
        import re
        # Find all regex literals and ensure they're balanced
        for i, line in enumerate(DASHBOARD_HTML.split("\n"), 1):
            if ".split(/" in line or ".replace(/" in line or ".match(/" in line:
                # Count unescaped slashes — regex must be balanced
                assert line.count("(") == line.count(")"), f"Unbalanced parens on line {i}: {line.strip()}"


# --- Dashboard server ---

class TestDashboardServer:
    def test_serves_html_and_api(self):
        """Start the dashboard server, hit endpoints, verify responses."""
        from analysis_agent.dashboard import serve_dashboard
        import tempfile, threading, time, urllib.request

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal report
            report = {"data_type": "revenue", "summary": {"total_revenue": 100, "period": "test"}, "charts": []}
            with open(os.path.join(tmpdir, "sales_report.json"), "w") as f:
                json.dump(report, f)

            # Patch webbrowser.open to do nothing
            import webbrowser
            orig_open = webbrowser.open
            webbrowser.open = lambda url: None

            server_started = threading.Event()
            port = 18923

            def run_server():
                import socketserver
                socketserver.TCPServer.allow_reuse_address = True
                try:
                    serve_dashboard(tmpdir, port)
                except Exception:
                    pass

            t = threading.Thread(target=run_server, daemon=True)
            t.start()
            time.sleep(1)

            try:
                # Test HTML page
                resp = urllib.request.urlopen(f"http://localhost:{port}/")
                html = resp.read().decode()
                assert "Sales Analysis Dashboard" in html
                assert "AMPLIFY" in html
                assert "Upload Data" in html

                # Test API
                resp = urllib.request.urlopen(f"http://localhost:{port}/api/report")
                data = json.loads(resp.read().decode())
                assert data["data_type"] == "revenue"
            finally:
                webbrowser.open = orig_open


# --- Plan vs Actual Comparison ---

class TestPlanComparison:
    @pytest.fixture
    def aop_csv(self, tmp_path):
        csv = tmp_path / "aop.csv"
        csv.write_text(
            "Aop Reporting Date,Commercial Segment,Aop Sales Units,Corp,Distributor Name,Product Num\n"
            "2025-10-01,Retail,500,ACME,ACME INC,P001\n"
            "2025-10-01,Commercial,300,BETA,BETA CO,P002\n"
            "2025-11-01,Retail,600,ACME,ACME INC,P001\n"
            "2025-11-01,Commercial,400,BETA,BETA CO,P002\n"
        )
        return str(csv)

    @pytest.fixture
    def actuals_csv(self, tmp_path):
        csv = tmp_path / "actuals.csv"
        csv.write_text(
            "date,corp_name,order_qty,total_delivered_qty,otif,fill\n"
            "2025-10-15,ACME,480,460,0.96,0.97\n"
            "2025-10-20,BETA,310,290,0.94,0.95\n"
            "2025-11-10,ACME,620,590,0.98,0.99\n"
            "2025-11-18,BETA,380,360,0.95,0.96\n"
        )
        return str(csv)

    def test_load_aop_data(self, aop_csv):
        df = load_aop_data(aop_csv)
        assert "plan_units" in df.columns
        assert "plan_date" in df.columns
        assert "month" in df.columns
        assert len(df) == 4
        assert df["plan_units"].sum() == 1800

    def test_load_actuals_data(self, actuals_csv):
        df = load_actuals_data(actuals_csv)
        assert "actual_orders" in df.columns
        assert "actual_delivered" in df.columns
        assert "month" in df.columns
        assert len(df) == 4

    def test_compare_monthly(self, aop_csv, actuals_csv):
        plan_df = load_aop_data(aop_csv)
        actuals_df = load_actuals_data(actuals_csv)
        result = compare_plan_vs_actual(plan_df, actuals_df)

        assert len(result.by_month) == 2
        assert "plan_units" in result.by_month.columns
        assert "actual_orders" in result.by_month.columns
        assert "order_variance" in result.by_month.columns
        assert "order_attainment_pct" in result.by_month.columns

    def test_compare_by_corp(self, aop_csv, actuals_csv):
        plan_df = load_aop_data(aop_csv)
        actuals_df = load_actuals_data(actuals_csv)
        result = compare_plan_vs_actual(plan_df, actuals_df)

        assert not result.by_corp.empty
        assert "corp" in result.by_corp.columns
        assert "plan_units" in result.by_corp.columns

    def test_summary_values(self, aop_csv, actuals_csv):
        plan_df = load_aop_data(aop_csv)
        actuals_df = load_actuals_data(actuals_csv)
        result = compare_plan_vs_actual(plan_df, actuals_df)

        s = result.summary
        assert s["total_plan_units"] == 1800
        assert s["total_actual_orders"] == 1790
        assert s["total_actual_delivered"] == 1700
        assert s["order_attainment_pct"] > 0
        assert s["delivery_attainment_pct"] > 0
        assert s["months_compared"] == 2

    def test_variance_correct_sign(self, aop_csv, actuals_csv):
        plan_df = load_aop_data(aop_csv)
        actuals_df = load_actuals_data(actuals_csv)
        result = compare_plan_vs_actual(plan_df, actuals_df)

        # Oct: plan=800, actual=790 -> negative variance
        # Nov: plan=1000, actual=1000 -> zero variance
        for _, row in result.by_month.iterrows():
            expected_var = row["actual_orders"] - row["plan_units"]
            assert row["order_variance"] == expected_var

    def test_attainment_calculation(self, aop_csv, actuals_csv):
        plan_df = load_aop_data(aop_csv)
        actuals_df = load_actuals_data(actuals_csv)
        result = compare_plan_vs_actual(plan_df, actuals_df)

        for _, row in result.by_month.iterrows():
            if row["plan_units"] > 0:
                expected_pct = round(row["actual_orders"] / row["plan_units"] * 100, 1)
                assert row["order_attainment_pct"] == expected_pct


class TestPlanComparisonPipeline:
    def test_agent_with_plan_file(self, tmp_path):
        """Full pipeline with plan comparison."""
        actuals = tmp_path / "actuals.csv"
        actuals.write_text(
            'Corp Name,OTIF %,Fill %,Order Qty,Total Delivered Qty,Not Delivered,Group Size,Reporting Date - Month,Reporting Date - Year\n'
            'ACME,95%,97%,"10,000","9,700",300,24F,October,2025\n'
            'ACME,98%,99%,"8,000","7,920",80,65,November,2025\n'
            'BETA,92%,94%,"12,000","11,280",720,24F,October,2025\n'
            'BETA,96%,97%,"9,500","9,215",285,65,November,2025\n'
        )
        plan = tmp_path / "plan.csv"
        plan.write_text(
            "Aop Reporting Date,Aop Sales Units,Corp\n"
            "2025-10-01,11000,ACME\n"
            "2025-10-01,13000,BETA\n"
            "2025-11-01,9000,ACME\n"
            "2025-11-01,10000,BETA\n"
        )
        agent = SalesAnalysisAgent(
            str(actuals),
            output_dir=str(tmp_path / "out"),
            plan_file=str(plan),
        )
        report = agent.run(generate_charts=True)

        # Verify plan comparison is in report
        assert "plan_comparison" in report
        pc = report["plan_comparison"]
        assert pc["summary"]["total_plan_units"] == 43000
        assert pc["summary"]["total_actual_orders"] > 0
        assert len(pc["by_month"]) >= 2

        # Verify charts include plan charts
        plan_charts = [c for c in report["charts"] if "plan" in c or "attainment" in c or "variance" in c]
        assert len(plan_charts) >= 2

        # Verify JSON is valid
        report_json = (tmp_path / "out" / "sales_report.json").read_text()
        parsed = json.loads(report_json)
        assert "NaN" not in report_json
        assert "plan_comparison" in parsed


class TestDashboardPlanUpload:
    def test_html_has_plan_upload_button(self):
        from analysis_agent.dashboard import DASHBOARD_HTML
        assert "Upload Plan" in DASHBOARD_HTML
        assert "plan-input" in DASHBOARD_HTML
        assert "/api/upload-plan" in DASHBOARD_HTML
