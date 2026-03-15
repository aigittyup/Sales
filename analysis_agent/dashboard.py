"""Simple web dashboard to view sales analysis results."""

import http.server
import json
import os
import socketserver
import webbrowser
from pathlib import Path

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sales Analysis Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; color: #333; }
        .header { background: linear-gradient(135deg, #1a73e8, #0d47a1); color: white; padding: 24px 40px; }
        .header h1 { font-size: 24px; font-weight: 600; }
        .header p { opacity: 0.85; margin-top: 4px; font-size: 14px; }
        .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card .label { font-size: 12px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; }
        .card .value { font-size: 28px; font-weight: 700; color: #1a73e8; margin-top: 4px; }
        .card .sub { font-size: 12px; color: #999; margin-top: 2px; }
        .section { background: white; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .section h2 { font-size: 18px; margin-bottom: 16px; color: #1a73e8; }
        .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 24px; margin-bottom: 24px; }
        .chart-container { background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }
        .chart-container img { max-width: 100%; height: auto; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-size: 12px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; }
        td { font-size: 14px; }
        tr:hover { background: #f8f9fa; }
        .positive { color: #0d9f6e; }
        .negative { color: #e74c3c; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Sales Analysis Dashboard</h1>
        <p id="period"></p>
    </div>
    <div class="container">
        <div class="cards" id="metric-cards"></div>
        <div class="charts" id="charts"></div>
        <div class="section" id="products-section">
            <h2>Top Products</h2>
            <table id="products-table"><thead><tr></tr></thead><tbody></tbody></table>
        </div>
        <div class="section" id="trend-section">
            <h2>Monthly Trend</h2>
            <table id="trend-table"><thead><tr></tr></thead><tbody></tbody></table>
        </div>
    </div>
    <script>
        fetch('/api/report')
            .then(r => r.json())
            .then(data => {
                const s = data.summary;
                document.getElementById('period').textContent = 'Period: ' + s.period;

                const cards = [
                    { label: 'Total Revenue', value: '$' + Number(s.total_revenue).toLocaleString(), sub: s.num_transactions + ' transactions' },
                    { label: 'Avg Order Value', value: '$' + Number(s.avg_order_value).toLocaleString(), sub: 'Median: $' + Number(s.median_order_value).toLocaleString() },
                    { label: 'Units Sold', value: Number(s.total_units).toLocaleString(), sub: '' },
                    { label: 'Revenue Std Dev', value: '$' + Number(s.revenue_std).toLocaleString(), sub: '' },
                ];
                const cardsEl = document.getElementById('metric-cards');
                cards.forEach(c => {
                    cardsEl.innerHTML += `<div class="card"><div class="label">${c.label}</div><div class="value">${c.value}</div><div class="sub">${c.sub}</div></div>`;
                });

                // Charts
                const chartsEl = document.getElementById('charts');
                (data.charts || []).forEach(path => {
                    const name = path.replace(/\\\\/g, '/').split('/').pop();
                    chartsEl.innerHTML += `<div class="chart-container"><img src="/charts/${name}" alt="${name}"></div>`;
                });

                // Top Products table
                if (data.top_products && data.top_products.length) {
                    const thead = document.querySelector('#products-table thead tr');
                    const tbody = document.querySelector('#products-table tbody');
                    const cols = Object.keys(data.top_products[0]);
                    cols.forEach(c => thead.innerHTML += `<th>${c.replace(/_/g, ' ')}</th>`);
                    data.top_products.forEach(row => {
                        let tr = '<tr>';
                        cols.forEach(c => {
                            let val = typeof row[c] === 'number' ? (c.includes('revenue') || c.includes('avg') ? '$' + row[c].toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : row[c].toLocaleString()) : row[c];
                            tr += `<td>${val}</td>`;
                        });
                        tbody.innerHTML += tr + '</tr>';
                    });
                }

                // Monthly Trend table
                if (data.monthly_trend && data.monthly_trend.length) {
                    const thead = document.querySelector('#trend-table thead tr');
                    const tbody = document.querySelector('#trend-table tbody');
                    const cols = Object.keys(data.monthly_trend[0]);
                    cols.forEach(c => thead.innerHTML += `<th>${c.replace(/_/g, ' ')}</th>`);
                    data.monthly_trend.forEach(row => {
                        let tr = '<tr>';
                        cols.forEach(c => {
                            let val = typeof row[c] === 'number' ? (c.includes('revenue') || c.includes('avg') ? '$' + row[c].toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : row[c].toLocaleString()) : row[c];
                            tr += `<td>${val}</td>`;
                        });
                        tbody.innerHTML += tr + '</tr>';
                    });
                }
            });
    </script>
</body>
</html>"""


def serve_dashboard(output_dir: str = "output", port: int = 8080):
    """Start a local web server to view the dashboard."""
    output_path = Path(output_dir).resolve()
    report_path = output_path / "sales_report.json"

    if not report_path.exists():
        print(f"Error: No report found at {report_path}")
        print("Run the analysis first: python -m analysis_agent data/sample_sales.csv")
        return

    class DashboardHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(DASHBOARD_HTML.encode())
            elif self.path == "/api/report":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                with open(report_path) as f:
                    self.wfile.write(f.read().encode())
            elif self.path.startswith("/charts/"):
                filename = self.path.split("/")[-1]
                filepath = output_path / filename
                if filepath.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.end_headers()
                    with open(filepath, "rb") as f:
                        self.wfile.write(f.read())
                else:
                    self.send_error(404)
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            pass  # Suppress request logs

    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        url = f"http://localhost:{port}"
        print(f"Dashboard running at {url}")
        print("Press Ctrl+C to stop")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard stopped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sales Analysis Dashboard")
    parser.add_argument("-o", "--output", default="output", help="Output directory with report data")
    parser.add_argument("-p", "--port", type=int, default=8080, help="Port number (default: 8080)")
    args = parser.parse_args()
    serve_dashboard(args.output, args.port)
