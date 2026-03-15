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

        /* Interstate Batteries green branding */
        .header { background: linear-gradient(135deg, #00843D, #005a28); color: white; padding: 24px 40px; display: flex; justify-content: space-between; align-items: center; }
        .header-left h1 { font-size: 24px; font-weight: 600; }
        .header-left p { opacity: 0.85; margin-top: 4px; font-size: 14px; }
        .header-right { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
        .powered-by { font-size: 11px; opacity: 0.7; letter-spacing: 0.5px; }
        .powered-by strong { font-size: 14px; opacity: 1; letter-spacing: 1px; }
        .refresh-bar { display: flex; align-items: center; gap: 12px; }
        .refresh-btn { background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.4); padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; transition: background 0.2s; }
        .refresh-btn:hover { background: rgba(255,255,255,0.35); }
        .last-refresh { font-size: 11px; opacity: 0.75; }

        .container { max-width: 1200px; margin: 0 auto; padding: 24px; }

        /* Upload bar - compact collapsible */
        .upload-bar { background: white; border-radius: 8px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }
        .upload-toggle { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; cursor: pointer; user-select: none; }
        .upload-toggle:hover { background: #f8f9fa; }
        .upload-toggle h3 { font-size: 13px; color: #00843D; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .upload-toggle .arrow { transition: transform 0.2s; font-size: 10px; color: #999; }
        .upload-toggle .arrow.open { transform: rotate(90deg); }
        .upload-body { display: none; padding: 0 20px 16px; }
        .upload-body.open { display: block; }
        .upload-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
        .upload-row input[type="file"] { display: none; }
        .upload-btn { background: #00843D; color: white; border: none; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 12px; white-space: nowrap; }
        .upload-btn:hover { background: #005a28; }
        .upload-btn:disabled { background: #ccc; cursor: not-allowed; }
        .upload-btn.sm { padding: 5px 12px; font-size: 11px; }
        .file-label { font-size: 12px; color: #666; }
        .upload-options { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; align-items: end; }
        .upload-options label { font-size: 11px; color: #555; display: flex; flex-direction: column; gap: 2px; }
        .upload-options input[type="text"] { padding: 4px 8px; border: 1px solid #ddd; border-radius: 3px; font-size: 11px; width: 110px; }
        .upload-options input[type="text"]:focus { outline: none; border-color: #00843D; box-shadow: 0 0 0 2px rgba(0,132,61,0.15); }
        .status-msg { margin-top: 8px; padding: 6px 10px; border-radius: 4px; font-size: 12px; display: none; }
        .status-msg.success { display: block; background: #d4edda; color: #155724; }
        .status-msg.error { display: block; background: #f8d7da; color: #721c24; }
        .status-msg.loading { display: block; background: #fff3cd; color: #856404; }
        .drop-active { border: 2px dashed #00843D; background: #e8f5e9; border-radius: 6px; }

        /* Cards */
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-top: 3px solid #00843D; }
        .card .label { font-size: 12px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; }
        .card .value { font-size: 28px; font-weight: 700; color: #00843D; margin-top: 4px; }
        .card .sub { font-size: 12px; color: #999; margin-top: 2px; }

        /* Sections */
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

        /* Correlation */
        .corr-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
        .corr-pair { font-weight: 500; }
        .corr-value { font-weight: 700; }
        .corr-strong { color: #00843D; }
        .corr-moderate { color: #f39c12; }
        .corr-negative { color: #e74c3c; }

        .hidden { display: none; }

        /* Footer */
        .footer { text-align: center; padding: 16px; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            <h1>Sales Analysis Dashboard</h1>
            <p id="period"></p>
        </div>
        <div class="header-right">
            <div class="powered-by">POWERED BY <strong>AMPLIFY</strong></div>
            <div class="refresh-bar">
                <span class="last-refresh" id="last-refresh"></span>
                <button class="refresh-btn" id="refresh-btn" onclick="hardRefresh()">Refresh</button>
            </div>
        </div>
    </div>
    <div class="container">
        <!-- Results first -->
        <div id="results" class="hidden">
            <div class="cards" id="metric-cards"></div>
            <div class="charts" id="charts"></div>

            <!-- Correlation Section -->
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

        <!-- Compact upload bar at bottom -->
        <div class="upload-bar" id="upload-bar">
            <div class="upload-toggle" onclick="toggleUpload()">
                <h3><span class="arrow" id="upload-arrow">&#9654;</span> Upload New Data</h3>
                <span class="file-label" id="file-label"></span>
            </div>
            <div class="upload-body" id="upload-body">
                <div class="upload-row" id="drop-zone">
                    <input type="file" id="file-input" accept=".csv,.xlsx,.xls">
                    <button class="upload-btn sm" id="browse-btn">Choose File</button>
                    <span class="file-label" id="file-name"></span>
                    <span style="color:#ccc">|</span>
                    <span class="file-label">or drag & drop a file here</span>
                </div>
                <div class="upload-options">
                    <label>Revenue <input type="text" id="opt-revenue" value="revenue"></label>
                    <label>Date <input type="text" id="opt-date" value="date"></label>
                    <label>Product <input type="text" id="opt-product" value="product"></label>
                    <label>Quantity <input type="text" id="opt-quantity" value="quantity"></label>
                    <label>Segments <input type="text" id="opt-segments" value="" placeholder="region,channel"></label>
                    <button class="upload-btn" id="analyze-btn" disabled>Analyze</button>
                </div>
                <div class="status-msg" id="status-msg"></div>
            </div>
        </div>
    </div>
    <div class="footer">Powered by Amplify | Interstate Batteries</div>
    <script>
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const browseBtn = document.getElementById('browse-btn');
        const analyzeBtn = document.getElementById('analyze-btn');
        const fileNameEl = document.getElementById('file-name');
        const fileLabelEl = document.getElementById('file-label');
        const statusMsg = document.getElementById('status-msg');
        let selectedFile = null;

        function toggleUpload() {
            const body = document.getElementById('upload-body');
            const arrow = document.getElementById('upload-arrow');
            body.classList.toggle('open');
            arrow.classList.toggle('open');
        }

        function updateRefreshTime() {
            const now = new Date();
            document.getElementById('last-refresh').textContent = 'Last refresh: ' + now.toLocaleString();
        }

        function hardRefresh() {
            fetch('/api/report')
                .then(r => { if (r.ok) return r.json(); throw new Error('no report'); })
                .then(data => { renderReport(data); updateRefreshTime(); })
                .catch(() => { window.location.reload(); });
        }

        browseBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => { if (e.target.files[0]) selectFile(e.target.files[0]); });

        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drop-active'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drop-active'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drop-active');
            if (e.dataTransfer.files[0]) selectFile(e.dataTransfer.files[0]);
        });

        function selectFile(file) {
            selectedFile = file;
            const label = file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
            fileNameEl.textContent = label;
            fileLabelEl.textContent = label;
            analyzeBtn.disabled = false;
        }

        analyzeBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            analyzeBtn.disabled = true;
            statusMsg.className = 'status-msg loading';
            statusMsg.textContent = 'Uploading and analyzing... this may take a moment.';

            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('revenue_col', document.getElementById('opt-revenue').value);
            formData.append('date_col', document.getElementById('opt-date').value);
            formData.append('product_col', document.getElementById('opt-product').value);
            formData.append('quantity_col', document.getElementById('opt-quantity').value);
            formData.append('segments', document.getElementById('opt-segments').value);

            try {
                const resp = await fetch('/api/upload', { method: 'POST', body: formData });
                const result = await resp.json();
                if (result.error) {
                    statusMsg.className = 'status-msg error';
                    statusMsg.textContent = 'Error: ' + result.error;
                    analyzeBtn.disabled = false;
                } else {
                    statusMsg.className = 'status-msg success';
                    statusMsg.textContent = 'Analysis complete!';
                    renderReport(result);
                    updateRefreshTime();
                    analyzeBtn.disabled = false;
                }
            } catch (err) {
                statusMsg.className = 'status-msg error';
                statusMsg.textContent = 'Upload failed: ' + err.message;
                analyzeBtn.disabled = false;
            }
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

            // Metric cards - adapt to data type
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

            // Charts
            const chartsEl = document.getElementById('charts');
            chartsEl.innerHTML = '';
            (data.charts || []).forEach(path => {
                const name = path.replace(/\\\\/g, '/').split('/').pop();
                chartsEl.innerHTML += '<div class="chart-container"><img src="/charts/' + name + '?t=' + Date.now() + '" alt="' + name + '"></div>';
            });

            // Correlation section
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

            // Data tables - adapt to data type
            const prodSection = document.getElementById('products-section');
            const trendSection = document.getElementById('trend-section');

            if (isSC) {
                prodSection.querySelector('h2').textContent = 'Performance by Corp';
                renderTable('products-table', data.by_corp || []);
                trendSection.querySelector('h2').textContent = 'Monthly Trend';
                renderTable('trend-table', data.monthly_trend || []);
            } else {
                prodSection.querySelector('h2').textContent = 'Top Products';
                renderTable('products-table', data.top_products || []);
                trendSection.querySelector('h2').textContent = 'Monthly Trend';
                renderTable('trend-table', data.monthly_trend || []);
            }
        }

        // Auto-load existing report on page load
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

                    # Parse multipart form data
                    boundary = content_type.split("boundary=")[1].encode()
                    content_length = int(self.headers["Content-Length"])
                    body = self.rfile.read(content_length)

                    parts = body.split(b"--" + boundary)
                    file_data = None
                    file_ext = ".csv"
                    form_fields = {}

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
                        elif "name=" in header:
                            field_name = header.split('name="')[1].split('"')[0]
                            form_fields[field_name] = data.decode(errors="replace").strip()

                    if file_data is None:
                        self._json_response(400, {"error": "No file uploaded"})
                        return

                    # Save uploaded file
                    upload_path = output_path / ("uploaded_data" + file_ext)
                    with open(upload_path, "wb") as f:
                        f.write(file_data)

                    # Build analysis command
                    cmd = [
                        sys.executable, "-m", "analysis_agent",
                        str(upload_path),
                        "-o", str(output_path),
                    ]
                    for flag, field in [
                        ("--revenue-col", "revenue_col"),
                        ("--date-col", "date_col"),
                        ("--product-col", "product_col"),
                        ("--quantity-col", "quantity_col"),
                    ]:
                        if form_fields.get(field):
                            cmd.extend([flag, form_fields[field]])

                    segments = form_fields.get("segments", "").strip()
                    if segments:
                        cmd.append("--segments")
                        cmd.extend(s.strip() for s in segments.split(",") if s.strip())

                    # Run analysis
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )

                    if result.returncode != 0:
                        self._json_response(500, {"error": result.stderr or result.stdout or "Analysis failed"})
                        return

                    # Return the report
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
            self.wfile.write(json.dumps(data, default=str).encode())

        def log_message(self, format, *args):
            pass

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
