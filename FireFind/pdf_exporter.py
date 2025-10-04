import os
import json
import argparse
from datetime import datetime
from fpdf import FPDF


class ExportManager:
    """Handles exporting findings data to PDF."""

    def __init__(self):
        self.downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")

    def get_timestamp(self):
        """Generate timestamp for unique filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def export_to_pdf(self, data, filename=None):
        """Export findings to a PDF file."""
        try:
            if not filename:
                filename = f"FireFind_Report_{self.get_timestamp()}.pdf"
            filepath = os.path.join(self.downloads_folder, filename)

            pdf = FireFindPDF()
            pdf.add_page()
            pdf.add_findings_table(data)
            pdf.output(filepath)

            print(f"PDF exported successfully: {filepath}")
            return filepath

        except Exception as e:
            print(f"Export Error: {e}")
            return None


class FireFindPDF(FPDF):
    """Custom PDF class for FireFind reports."""

    def __init__(self):
        super().__init__()
        self.report_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def header(self):
        """Add header to each page."""
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 10, "FireFind Security Report", new_x="LMARGIN", new_y="NEXT", align="C")

        self.set_font("Helvetica", "", 10)
        self.cell(0, 8, f"Generated on: {self.report_datetime}", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(8)

    def footer(self):
        """Add footer to each page."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_findings_table(self, data):
        """Add findings data as a formatted, wrapped table that fits the page width."""
        if not data:
            self.set_font("Helvetica", "I", 10)
            self.cell(0, 10, "No findings to display.", align="Center")
            return

        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "Security Findings Summary", new_x="LMARGIN", new_y="NEXT", align="L")
        self.ln(5)

        headers = ["Rule ID", "Title", "Source", "Destination", "Service", "Severity", "Vendor"]

        # --- Dynamically compute column widths ---
        page_width = self.w - 2 * self.l_margin
        col_ratios = [0.08, 0.25, 0.15, 0.15, 0.15, 0.12, 0.10]  # must total ≈ 1.0
        col_widths = [page_width * r for r in col_ratios]

        # --- Header row ---
        self.set_font("Helvetica", "B", 9)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, header, border=1, align="C")
        self.ln()

        # --- Data rows ---
        self.set_font("Helvetica", "", 8)
        for finding in data:
            if self.get_y() > 270:
                self.add_page()
                self.set_font("Helvetica", "B", 9)
                for i, header in enumerate(headers):
                    self.cell(col_widths[i], 8, header, border=1, align="Center")
                self.ln()
                self.set_font("Helvetica", "", 8)

            rule_id = str(finding.get("rule_id") or finding.get("id", ""))
            title = str(finding.get("title") or finding.get("finding") or finding.get("name") or "No Title")
            src = ", ".join(finding.get("src_addrs", finding.get("source", []))) if isinstance(finding.get("src_addrs", []), list) else str(finding.get("src_addrs", ""))
            dst = ", ".join(finding.get("dst_addrs", finding.get("destination", []))) if isinstance(finding.get("dst_addrs", []), list) else str(finding.get("dst_addrs", ""))
            vendor = str(finding.get("vendor", ""))
            severity = str(finding.get("severity", "Unknown")).capitalize()

            # Format services
            services = finding.get("services", [])
            service_display = []
            for svc in services:
                protocol = svc.get("protocol", "")
                ports = svc.get("ports", [])
                port_texts = []
                for p in ports:
                    if isinstance(p, dict) and "from" in p and "to" in p:
                        port_texts.append(f"{p['from']}-{p['to']}" if p["from"] != p["to"] else str(p["from"]))
                if port_texts:
                    service_display.append(f"{protocol}/{','.join(port_texts)}")
                elif protocol:
                    service_display.append(protocol)
            service_text = ", ".join(service_display) or str(finding.get("service", ""))

            severity_color = {
                "High": (255, 120, 120),
                "Medium": (255, 200, 120),
                "Low": (160, 255, 160),
                "Unknown": (230, 230, 230),
            }.get(severity, (230, 230, 230))

            row = [rule_id, title, src, dst, service_text, severity, vendor]

            x_start = self.get_x()
            y_start = self.get_y()

            cell_heights = []
            wrapped_texts = []

            # Wrap text and calculate max height
            for i, val in enumerate(row):
                text = str(val) or "-"
                if i in [1, 2, 3, 4]:  # wrap long fields
                    lines = self.multi_cell(col_widths[i], 5, text, border=0, align="C", split_only=True)
                    wrapped_texts.append(lines)
                    cell_heights.append(5 * len(lines))
                else:
                    wrapped_texts.append([text])
                    cell_heights.append(5)

            max_height = max(cell_heights)

            # Draw cells
            for i, lines in enumerate(wrapped_texts):
                self.set_xy(x_start + sum(col_widths[:i]), y_start)
                if headers[i] == "Severity":
                    self.set_fill_color(*severity_color)
                    self.multi_cell(col_widths[i], 5, "\n".join(lines), border=1, align="C", fill=True)
                else:
                    self.multi_cell(col_widths[i], 5, "\n".join(lines), border=1, align="C")

            self.set_y(y_start + max_height)

def load_json_or_jsonl(filepath):
    """Load findings from JSON or JSONL file automatically."""
    findings = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            raise ValueError("Input file is empty.")

        # Try JSON array
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            else:
                return [data]
        except json.JSONDecodeError:
            pass  # Try JSONL

        # JSONL fallback
        for line in content.splitlines():
            line = line.strip()
            if line:
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Skipping invalid JSON line: {e}")
    return findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FireFind JSON/JSONL → PDF Export Tool (Color-coded)")
    parser.add_argument("input_file", help="Path to input file (.json or .jsonl)")
    parser.add_argument("--output", help="Optional output filename (e.g., report.pdf)")
    args = parser.parse_args()

    findings = load_json_or_jsonl(args.input_file)
    exporter = ExportManager()
    exporter.export_to_pdf(findings, filename=args.output)