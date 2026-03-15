"""Web dashboard with file upload and correlation analysis display."""

import http.server
import json
import os
import socketserver
import subprocess
import sys
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

        .header { background: linear-gradient(135deg, #00843D, #005a28); color: white; padding: 24px 40px; display: flex; justify-content: space-between; align-items: center; }
        .header-left h1 { font-size: 24px; font-weight: 600; }
        .header-left p { opacity: 0.85; margin-top: 4px; font-size: 14px; }
        .header-right { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
        .powered-by { font-size: 11px; opacity: 0.7; letter-spacing: 0.5px; }
        .powered-by strong { font-size: 14px; opacity: 1; letter-spacing: 1px; }
        .header-actions { display: flex; align-items: center; gap: 8px; }
        .header-btn { background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.4); padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; transition: background 0.2s; }
        .header-btn:hover { background: rgba(255,255,255,0.35); }
        .last-refresh { font-size: 11px; opacity: 0.75; }
        .status-toast { position: fixed; top: 20px; right: 20px; padding: 10px 20px; border-radius: 6px; font-size: 13px; z-index: 999; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .status-toast.success { display: block; background: #d4edda; color: #155724; }
        .status-toast.error { display: block; background: #f8d7da; color: #721c24; }
        .status-toast.loading { display: block; background: #fff3cd; color: #856404; }

        .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-top: 3px solid #00843D; }
        .card .label { font-size: 12px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; }
        .card .value { font-size: 28px; font-weight: 700; color: #00843D; margin-top: 4px; }
        .card .sub { font-size: 12px; color: #999; margin-top: 2px; }
        .section { background: white; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .section h2 { font-size: 18px; margin-bottom: 16px; color: #00843D; }
        .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 24px; margin-bottom: 24px; }
        .chart-container { background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }
        .chart-container img { max-width: 100%; height: auto; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #e8f5e9; font-size: 12px; text-transform: uppercase; color: #333; letter-spacing: 0.5px; }
        td { font-size: 14px; }
        tr:hover { background: #f1f8f3; }
        .corr-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
        .corr-pair { font-weight: 500; }
        .corr-value { font-weight: 700; }
        .corr-strong { color: #00843D; }
        .corr-moderate { color: #f39c12; }
        .corr-negative { color: #e74c3c; }
        .hidden { display: none; }
        .footer { text-align: center; padding: 16px; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <input type="file" id="file-input" accept=".csv,.xlsx,.xls" style="display:none">
    <div class="status-toast" id="status-toast"></div>
    <div class="header">
        <div class="header-left">
            <h1>Sales Analysis Dashboard</h1>
            <p id="period"></p>
        </div>
        <div class="header-right">
            <div class="powered-by">POWERED BY <strong>AMPLIFY</strong></div>
            <div class="header-actions">
                <span class="last-refresh" id="last-refresh"></span>
                <button class="header-btn" onclick="hardRefresh()">Refresh</button>
                <button class="header-btn" onclick="document.getElementById('file-input').click()">Upload Data</button>
            </div>
        </div>
    </div>
    <div class="container">
        <div id="results" class="hidden">
            <div class="cards" id="metric-cards"></div>
            <div class="charts" id="charts"></div>
            <div class="section" id="correlation-section" style="display:none;">
                <h2>Correlation Analysis</h2>
                <div id="corr-findings"></div>
            </div>
            <div class="section" id="products-section">
                <h2>Top Products</h2>
                <table id="products-table"><thead><tr></tr></thead><tbody></tbody></table>
            </div>
            <div class="section" id="trend-section">
                <h2>Monthly Trend</h2>
                <table id="trend-table"><thead><tr></tr></thead><tbody></tbody></table>
            </div>
        </div>
    </div>
    <div class="footer">Powered by Amplify | Interstate Batteries</div>
    <script>
        const fileInput = document.getElementById('file-input');
        const toast = document.getElementById('status-toast');

        function showToast(msg, type) {
            toast.textContent = msg;
            toast.className = 'status-toast ' + type;
            if (type !== 'loading') setTimeout(() => { toast.style.display = 'none'; }, 4000);
        }

        function updateRefreshTime() {
            document.getElementById('last-refresh').textContent = 'Last refresh: ' + new Date().toLocaleString();
        }

        function hardRefresh() {
            fetch('/api/report')
                .then(r => { if (r.ok) return r.json(); throw new Error('no report'); })
                .then(data => { renderReport(data); updateRefreshTime(); })
                .catch(() => { window.location.reload(); });
        }

        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            showToast('Analyzing ' + file.name + '...', 'loading');
            console.log('Uploading:', file.name, file.size, 'bytes');

            const formData = new FormData();
            formData.append('file', file);

            try {
                const resp = await fetch('/api/upload', { method: 'POST', body: formData });
                console.log('Response status:', resp.status);
                const text = await resp.text();
                console.log('Response body:', text.substring(0, 500));
                let result;
                try { result = JSON.parse(text); } catch(e) { showToast('Server returned invalid response', 'error'); fileInput.value = ''; return; }
                if (result.error) {
                    showToast('Error: ' + result.error, 'error');
                } else {
                    showToast('Analysis complete!', 'success');
                    renderReport(result);
                    updateRefreshTime();
                }
            } catch (err) {
                console.error('Upload error:', err);
                showToast('Upload failed: ' + err.message, 'error');
            }
            fileInput.value = '';
        });

        function fmtVal(val, colName) {
            if (typeof val !== 'number') return val;
            if (colName.includes('otif') || colName.includes('fill')) return (val * 100).toFixed(1) + '%';
            if (colName.includes('revenue') || colName.includes('avg') || colName.includes('price')) return '$' + val.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
            if (colName.includes('pct') || colName.includes('share')) return val.toFixed(1) + '%';
            return val.toLocaleString();
        }

        function renderTable(tableId, rows) {
            const thead = document.querySelector('#' + tableId + ' thead tr');
            const tbody = document.querySelector('#' + tableId + ' tbody');
            thead.innerHTML = '';
            tbody.innerHTML = '';
            if (rows && rows.length) {
                const cols = Object.keys(rows[0]);
                cols.forEach(c => thead.innerHTML += '<th>' + c.replace(/_/g, ' ') + '</th>');
                rows.forEach(row => {
                    let tr = '<tr>';
                    cols.forEach(c => { tr += '<td>' + fmtVal(row[c], c) + '</td>'; });
                    tbody.innerHTML += tr + '</tr>';
                });
            }
        }

        function renderReport(data) {
            document.getElementById('results').classList.remove('hidden');
            const s = data.summary;
            document.getElementById('period').textContent = 'Period: ' + s.period;

            let cards;
            const isSC = data.data_type === 'supply_chain';
            if (isSC) {
                cards = [
                    { label: 'Total Orders', value: Number(s.total_order_qty).toLocaleString(), sub: s.num_records + ' records' },
                    { label: 'Total Delivered', value: Number(s.total_delivered).toLocaleString(), sub: Number(s.total_not_delivered).toLocaleString() + ' not delivered' },
                    { label: 'Avg OTIF %', value: s.avg_otif_pct + '%', sub: 'Target: 95%' },
                    { label: 'Avg Fill Rate', value: s.avg_fill_pct + '%', sub: 'Overall: ' + s.overall_fill_rate_pct + '%' },
                ];
            } else {
                cards = [
                    { label: 'Total Revenue', value: '$' + Number(s.total_revenue).toLocaleString(), sub: s.num_transactions + ' transactions' },
                    { label: 'Avg Order Value', value: '$' + Number(s.avg_order_value).toLocaleString(), sub: 'Median: $' + Number(s.median_order_value).toLocaleString() },
                    { label: 'Units Sold', value: Number(s.total_units).toLocaleString(), sub: '' },
                    { label: 'Revenue Std Dev', value: '$' + Number(s.revenue_std).toLocaleString(), sub: '' },
                ];
            }
            const cardsEl = document.getElementById('metric-cards');
            cardsEl.innerHTML = '';
            cards.forEach(c => {
                cardsEl.innerHTML += '<div class="card"><div class="label">' + c.label + '</div><div class="value">' + c.value + '</div><div class="sub">' + c.sub + '</div></div>';
            });

            const chartsEl = document.getElementById('charts');
            chartsEl.innerHTML = '';
            (data.charts || []).forEach(path => {
                const name = path.replace(/\\/g, '/').split('/').pop();
                chartsEl.innerHTML += '<div class="chart-container"><img src="/charts/' + name + '?t=' + Date.now() + '" alt="' + name + '"></div>';
            });

            const corrSection = document.getElementById('correlation-section');
            const corrFindings = document.getElementById('corr-findings');
            corrFindings.innerHTML = '';
            if (data.correlation && data.correlation.strong_correlations && data.correlation.strong_correlations.length > 0) {
                corrSection.style.display = 'block';
                data.correlation.strong_correlations.forEach(c => {
                    const cls = c.correlation < 0 ? 'corr-negative' : (c.strength === 'strong' ? 'corr-strong' : 'corr-moderate');
                    const sign = c.correlation > 0 ? '+' : '';
                    corrFindings.innerHTML += '<div class="corr-item"><span class="corr-pair">' + c.col_1 + ' &harr; ' + c.col_2 +
                        '</span><span class="corr-value ' + cls + '">' + sign + c.correlation.toFixed(4) +
                        ' (' + c.strength + ')</span></div>';
                });
            } else if (data.correlation) {
                corrSection.style.display = 'block';
                corrFindings.innerHTML = '<p style="color:#666">No strong correlations found (|r| &lt; 0.5) among numeric columns.</p>';
            } else {
                corrSection.style.display = 'none';
            }

            const prodSection = document.getElementById('products-section');
            const trendSection = document.getElementById('trend-section');
            if (isSC) {
                prodSection.querySelector('h2').textContent = 'Performance by Corp';
                renderTable('products-table', data.by_corp || []);
            } else {
                prodSection.querySelector('h2').textContent = 'Top Products';
                renderTable('products-table', data.top_products || []);
            }
            trendSection.querySelector('h2').textContent = 'Monthly Trend';
            renderTable('trend-table', data.monthly_trend || []);
        }

        fetch('/api/report')
            .then(r => { if (r.ok) return r.json(); throw new Error('no report'); })
            .then(data => { renderReport(data); updateRefreshTime(); })
            .catch(() => {});
    </script>
</body>
</html>"""


def serve_dashboard(output_dir: str = "output", port: int = 8080):
    """Start a local web server to view the dashboard."""
    output_path = Path(output_dir).resolve()
    project_root = Path(__file__).resolve().parent.parent
    os.makedirs(output_path, exist_ok=True)

    class DashboardHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(DASHBOARD_HTML.encode())
            elif self.path == "/api/report":
                report_path = output_path / "sales_report.json"
                if report_path.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    with open(report_path) as f:
                        self.wfile.write(f.read().encode())
                else:
                    self.send_error(404)
            elif self.path.startswith("/charts/"):
                filename = self.path.split("/")[-1].split("?")[0]
                filepath = output_path / filename
                if filepath.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    with open(filepath, "rb") as f:
                        self.wfile.write(f.read())
                else:
                    self.send_error(404)
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path == "/api/upload":
                try:
                    content_type = self.headers.get("Content-Type", "")
                    if "multipart/form-data" not in content_type:
                        self._json_response(400, {"error": "Expected multipart form data"})
                        return

                    boundary = content_type.split("boundary=")[1].encode()
                    content_length = int(self.headers["Content-Length"])
                    body = self.rfile.read(content_length)

                    parts = body.split(b"--" + boundary)
                    file_data = None
                    file_ext = ".csv"

                    for part in parts:
                        if b"Content-Disposition" not in part:
                            continue
                        header_end = part.index(b"\r\n\r\n")
                        header = part[:header_end].decode(errors="replace")
                        data = part[header_end + 4:]
                        if data.endswith(b"\r\n"):
                            data = data[:-2]

                        if 'name="file"' in header:
                            file_data = data
                            if 'filename="' in header:
                                fname = header.split('filename="')[1].split('"')[0]
                                file_ext = Path(fname).suffix or ".csv"

                    if file_data is None:
                        self._json_response(400, {"error": "No file uploaded"})
                        return

                    upload_path = output_path / ("uploaded_data" + file_ext)
                    with open(upload_path, "wb") as f:
                        f.write(file_data)

                    cmd = [
                        sys.executable, "-m", "analysis_agent",
                        str(upload_path),
                        "-o", str(output_path),
                    ]

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=120,
                        cwd=str(project_root),
                    )

                    if result.returncode != 0:
                        self._json_response(500, {"error": result.stderr or result.stdout or "Analysis failed"})
                        return

                    report_path = output_path / "sales_report.json"
                    with open(report_path) as f:
                        report = json.load(f)

                    self._json_response(200, report)

                except Exception as e:
                    self._json_response(500, {"error": str(e)})
            else:
                self.send_error(404)

        def _json_response(self, code, data):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            # Replace NaN with null for valid JSON
            text = json.dumps(data, default=str)
            text = text.replace(": NaN", ": null").replace(":NaN", ":null")
            self.wfile.write(text.encode())

        def log_message(self, format, *args):
            if self.path == "/api/upload":
                print(format % args)

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
