import os
import json
import datetime
import re
from pipeline.reporting.llm_narrator import SarvamNarrator
from pipeline.utils.db_connection import get_cursor
from dotenv import load_dotenv

# Ensure .env is loaded from root
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv()

# BharatData Premium Minimalist Serif Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BharatData Executive Ingestion Report - {dataset_name}</title>
    <!-- Premium Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=PT+Serif:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --bg-primary: #FFFFFF;
            --bg-secondary: #F9FAFB;
            --text-main: #111827;
            --text-muted: #6B7280;
            --brand-blue: #0047AB;
            --border-light: #E5E7EB;
            --success-bg: #ECFDF5;
            --success-text: #065F46;
        }}
        
        body {{
            font-family: 'PT Serif', serif;
            background-color: var(--bg-secondary);
            color: var(--text-main);
            margin: 0;
            padding: 4rem 2rem;
            line-height: 1.8;
            -webkit-font-smoothing: antialiased;
        }}
        
        .report-page {{
            max-width: 900px;
            background: var(--bg-primary);
            margin: 0 auto;
            padding: 5rem;
            box-shadow: 0 4px 50px rgba(0,0,0,0.03);
            border: 1px solid var(--border-light);
            position: relative;
        }}

        /* Header Styles */
        header {{
            border-bottom: 2px solid var(--text-main);
            margin-bottom: 4rem;
            padding-bottom: 2rem;
        }}

        .brand {{
            font-family: 'Playfair Display', serif;
            font-weight: 700;
            font-size: 0.9rem;
            letter-spacing: 0.2rem;
            text-transform: uppercase;
            color: var(--brand-blue);
            margin-bottom: 1rem;
            display: block;
        }}

        h1 {{
            font-family: 'Playfair Display', serif;
            font-size: 2.8rem;
            margin: 0.5rem 0;
            line-height: 1.2;
            font-weight: 400;
        }}

        .metadata-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
            margin-top: 2rem;
            font-size: 0.9rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border-light);
            padding-top: 1.5rem;
        }}

        /* Sections */
        .section-title {{
            font-family: 'Playfair Display', serif;
            font-size: 1.5rem;
            margin: 3rem 0 1.5rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border-light);
            color: var(--text-main);
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 2rem;
            margin: 2rem 0;
        }}

        .stat-card {{
            padding: 1.5rem;
            border: 1px solid var(--border-light);
            border-radius: 4px;
            background: var(--bg-secondary);
        }}

        .stat-label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }}

        .stat-value {{
            font-size: 1.8rem;
            font-family: 'Playfair Display', serif;
            font-weight: 700;
        }}

        /* Content Formatting */
        .analysis-content {{
            font-size: 1.1rem;
        }}

        .analysis-content h3 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.3rem;
            margin-top: 2rem;
            color: var(--brand-blue);
        }}

        .analysis-content br {{
            display: block;
            margin: 1rem 0;
            content: "";
        }}

        /* Registry Context Section */
        .registry-context {{
            background: #F3F4F6;
            padding: 2.5rem;
            border-radius: 8px;
            margin-top: 5rem;
        }}

        .context-title {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.2rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: var(--text-muted);
        }}

        /* Footer */
        footer {{
            margin-top: 6rem;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border-light);
            padding-top: 3rem;
        }}

        .footer-links {{
            margin-bottom: 1rem;
        }}
        
        .footer-links a {{
            color: var(--brand-blue);
            text-decoration: none;
            margin: 0 1rem;
        }}

        .print-only {{
            display: none;
        }}

        /* Table Styles */
        .analysis-content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 2rem 0;
            font-size: 0.95rem;
            border: 1px solid var(--border-light);
        }}

        .analysis-content th {{
            background: var(--bg-secondary);
            text-align: left;
            padding: 1rem;
            border-bottom: 2px solid var(--border-light);
            font-family: 'Playfair Display', serif;
            font-weight: 700;
        }}

        .analysis-content td {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-light);
        }}

        .analysis-content tr:last-child td {{
            border-bottom: none;
        }}

        .analysis-content tr:nth-child(even) {{
            background: #FAFAFA;
        }}

        @media print {{
            body {{ padding: 0; background: none; }}
            .report-page {{ box-shadow: none; border: none; width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="report-page">
        <header>
            <span class="brand">BharatData Premium Registry</span>
            <h1>{dataset_name}</h1>
            <div class="metadata-grid">
                <div>
                    <strong>Description:</strong><br>
                    {description}
                </div>
                <div>
                    <strong>Prepared Date:</strong> {date}<br>
                    <strong>ID:</strong> {source_id}<br>
                    <strong>Status:</strong> <span style="color: {health_color}">{status}</span>
                </div>
            </div>
        </header>

        <section>
            <h2 class="section-title">Ingestion Performance</h2>
            <div class="metrics-grid">
                <div class="stat-card">
                    <div class="stat-label">Health Score</div>
                    <div class="stat-value" style="color: {health_color}">{health}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Records</div>
                    <div class="stat-value">{total_records}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Data Confidence</div>
                    <div class="stat-value">{avg_confidence}%</div>
                </div>
            </div>
        </section>

        <section>
            <h2 class="section-title">Executive Analysis</h2>
            <div class="analysis-content">
                {narrative}
            </div>
        </section>

        <section class="registry-context">
            <div class="context-title">BharatData Global Registry Update</div>
            <div style="font-size: 1.2rem">
                With this addition, the BharatData ecosystem now manages <strong>{global_dataset_count} proprietary datasets</strong>. 
                Our registry continues to expand as India's unified data infrastructure.
            </div>
        </section>

        <footer>
            <div class="footer-links">
                <a href="#">Official Documentation</a> | 
                <a href="#">Privacy Framework</a> | 
                <a href="#">API Portal</a>
            </div>
            <div>Generated by the BharatData Team</div>
            <div style="margin-top: 0.5rem; letter-spacing: 0.3rem; font-weight: 700;">BHARATDATA</div>
        </footer>
    </div>
</body>
</html>
"""

def markdown_to_html(text):
    """Converts deep-audit Markdown (tables, headings, bold, lists) to premium HTML."""
    # 1. Tables (Handle before linebreaks)
    if '|' in text:
        lines = text.split('\n')
        html_lines = []
        in_table = False
        for line in lines:
            if '|' in line:
                cells = [c.strip() for c in line.split('|') if c.strip() or line.split('|')[0] == '' ]
                if not cells: continue
                if '--' in line: continue # Skip separator rows
                if not in_table:
                    html_lines.append('<table><thead><tr>')
                    for c in cells: html_lines.append(f'<th>{c}</th>')
                    html_lines.append('</tr></thead><tbody>')
                    in_table = True
                else:
                    html_lines.append('<tr>')
                    for c in cells: html_lines.append(f'<td>{c}</td>')
                    html_lines.append('</tr>')
            else:
                if in_table:
                    html_lines.append('</tbody></table>')
                    in_table = False
                html_lines.append(line)
        if in_table: html_lines.append('</tbody></table>')
        text = '\n'.join(html_lines)

    # 2. Headings (###)
    text = re.sub(r'### (.*?)\n', r'<h3>\1</h3>', text)
    text = re.sub(r'### (.*?)$', r'<h3>\1</h3>', text)
    
    # 3. Bold (**)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # 4. Lists (-)
    if '-' in text:
        lines = text.split('\n')
        in_list, html_lines = False, []
        for line in lines:
            if line.strip().startswith('- '):
                if not in_list: (html_lines.append('<ul>'), setattr(None, 'in_list', True)) # Mock setattr for logic
                in_list = True
                html_lines.append(f"<li>{line.strip()[2:]}</li>")
            else:
                if in_list: html_lines.append('</ul>')
                in_list = False
                html_lines.append(line)
        if in_list: html_lines.append('</ul>')
        text = '\n'.join(html_lines)

    # 4. Paragraphs / Newlines (Carefully excluding table areas)
    text = text.replace('\n', '<br>')
    text = text.replace('<br><h3>', '<h3>').replace('</h3><br>', '</h3>')
    
    # Clean redundant breaks in Table structures injected by global replace
    tags_to_clean = ['table', 'thead', 'tbody', 'tr', 'th', 'td']
    for tag in tags_to_clean:
        text = text.replace(f'<{tag}><br>', f'<{tag}>')
        text = text.replace(f'<br></{tag}>', f'</{tag}>')
        text = text.replace(f'</{tag}><br>', f'</{tag}>')

    return text

def get_total_datasets_count():
    """Calculates the total datasets registered across the system."""
    try:
        # In this architecture, datasets are defined by YAMLs in sources/
        # We count files excluding schemas and hidden ones
        source_dir = "sources"
        count = 0
        if os.path.exists(source_dir):
            for root, dirs, files in os.walk(source_dir):
                if "_schema" in root: continue
                count += len([f for f in files if f.endswith('.yaml')])
        return count
    except Exception:
        return "N/A"

def get_unique_report_path(dataset_id):
    """Calculates a unique report filename to prevent overwriting."""
    base_dir = "reports"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        
    filename = f"report_{dataset_id}.html"
    full_path = os.path.join(base_dir, filename)
    
    if os.path.exists(full_path):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"report_{dataset_id}_{ts}.html"
        full_path = os.path.join(base_dir, filename)
        
    return full_path

def generate_report(report_json_path, source_metadata=None):
    """Generates the premium HTML report."""
    if not os.path.exists(report_json_path):
        return None
        
    with open(report_json_path, "r") as f:
        data = json.load(f)
        
    source_metadata = source_metadata or {}
    dataset_name = source_metadata.get("name", "Unknown Dataset")
    dataset_id = source_metadata.get("id", "unidentified")
    description = source_metadata.get("description", "No description provided.")
    
    status = data.get("status", "SUCCESS")
    health = data.get("overall_health", "100%")
    health_val = int(health.replace('%', ''))
    health_color = "#065F46" if health_val > 90 else "#92400E" if health_val > 70 else "#991B1B"
    
    total_records = 0
    avg_conf = 0.0
    for check in data.get('checks', []):
        if check['check'] == 'ingestion_summary':
            total_records = check['metrics'].get('total_records', 0)
            avg_conf = round(check['metrics'].get('average', 0.0) * 100, 2)
            
    global_count = get_total_datasets_count()
    
    print("--- Requesting Sarvam-M Premium Narration ---")
    try:
        narrator = SarvamNarrator()
        narrative_raw = narrator.generate_narrative(data)
        narrative = markdown_to_html(narrative_raw)
    except Exception as e:
        narrative = f"<p style='color:red'>AI Analysis Failed: {str(e)}</p>"
        
    output_path = get_unique_report_path(dataset_id)
    
    final_html = HTML_TEMPLATE.format(
        dataset_name=dataset_name,
        source_id=dataset_id,
        description=description,
        status=status,
        health=health,
        health_color=health_color,
        total_records=total_records,
        avg_confidence=avg_conf,
        date=datetime.datetime.now().strftime("%B %d, %Y"),
        narrative=narrative,
        global_dataset_count=global_count
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    print(f"PREMIUM REPORT GENERATED: {output_path}")
    return output_path

if __name__ == "__main__":
    generate_report("quality_report_latest.json", {"id": "test", "name": "Test"})
