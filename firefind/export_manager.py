# export_manager.py
# this script handles exporting firefind findings to a clean professional-lookinig PDF report.
# table ismoreconsistent now, no more data cluttering
# Feel free to delete all commented functions,(anything related to csv, xslx and so on...) they are not needed
# This specific version is stable and works however it can benefit from some  user recommendations
# based on the findings ( we can work on it next sprint)
#

#USAGE:
#   python -m firefind.export_manager <input.jsonl> [--out results/report.pdf]
#
#   Example:
#       python -m firefind.export_manager .\results\findings.jsonl --out .\results\firefind_report.pdf

## Feel free to delete all uncommented functions below

# import csv  # not needed Json findings already exist from the stupid risk engine
import os
import re
from datetime import datetime
# from tkinter import filedialog, messagebox  # not needed
# import pandas as pd  # not needed, xlsx was something to worry about in the early stages
from fpdf import FPDF
from textwrap import wrap

# new ascii map unicode helpers
_ASCII_MAP = {
    "\u2013": "-", "\u2014": "-",  # dashes
    "\u2018": "'", "\u2019": "'",  # single quotes
    "\u201C": '"', "\u201D": '"',  # double quotes
    "\u2026": "...",               # ellipsis
    "\u00A0": " ",                 # nbsp
}
def _ascii_sanitize(s):
    """Make text safe for core fonts (no TTF)."""
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    for k, v in _ASCII_MAP.items():
        s = s.replace(k, v)
    try:
        return s.encode("latin-1", "ignore").decode("latin-1")
    except Exception:
        return s

def _safe_ascii(s: str) -> str:
    # replace common Unicode punctuation with ASCII equivalents
    return (s or "").replace("…", "...") \
                    .replace("–", "-").replace("—", "-") \
                    .replace("’", "'").replace("‘", "'") \
                    .replace("“", '"').replace("”", '"')


def _format_services_for_table(services):
    """Same logic as before, just factored out for reuse in PDF table."""
    parts = []
    for service in services or []:
        protocol = service.get('protocol', '') or ''
        ports = service.get('ports', []) or []
        port_ranges = []
        for port in ports:
            port_from = port.get('from')
            port_to = port.get('to')
            if port_from == port_to:
                port_ranges.append(str(port_from))
            else:
                port_ranges.append(f"{port_from}-{port_to}")
        if port_ranges:
            parts.append(f"{protocol}/{','.join(port_ranges)}")
        elif protocol:
            parts.append(protocol)
    return "; ".join(parts)

def _wrap_to_width(pdf, text: str, col_w: float) -> list[str]:
    """
    Greedy wrap that:
      - allows breaks after commas/semicolons
      - forces a break inside very long tokens that exceed the column width
    """
    # 1) normalize and inject a space after punctuation so it can break
    txt = pdf._safe(str(text or ""))
    txt = re.sub(r'([,;])(\S)', r'\1 \2', txt)  # ",X" -> ", X"   ";X" -> "; X"

    words = txt.split()
    if not words:
        return [""]

    def _force_break(token: str) -> list[str]:
        """Break a single very-long token into pieces that fit the column."""
        parts = []
        cur = ""
        for ch in token:
            trial = cur + ch
            if pdf.get_string_width(trial) <= (col_w - 2):
                cur = trial
            else:
                if cur:
                    parts.append(cur)
                cur = ch
        if cur:
            parts.append(cur)
        return parts

    lines, cur = [], words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if pdf.get_string_width(trial) <= (col_w - 2):
            cur = trial
        else:
            lines.append(cur)
            cur = w

    # finalize last line
    if pdf.get_string_width(cur) <= (col_w - 2):
        lines.append(cur)
    else:
        # last token still too wide -> forced chunks
        lines.extend(_force_break(cur))

    # safety: if any individual word is still too wide (first word case), chunk it
    fixed = []
    for ln in lines:
        if pdf.get_string_width(ln) <= (col_w - 2):
            fixed.append(ln)
        else:
            fixed.extend(_force_break(ln))
    return fixed or [""]

def _truncate(s, n):
    """Keep cells neat (ASCII-safe)."""
    s = "" if s is None else str(s)
    if len(s) <= n:
        return s
    if n <= 3:
        return s[:n]
    # Use ASCII ellipsis to avoid Unicode issues with core fonts
    return s[: n - 3] + "..."



class ExportManager:
    """Handles exporting findings data to various formats."""

    def __init__(self):
        self.downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")

    def get_timestamp(self):
        """Generate timestamp for unique filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # CSV
    def _flatten_finding_for_csv(self, finding):
        """Convert new schema finding to flat CSV row (kept for reference)."""
        # ?????????????????
        services = finding.get('services', [])
        service_str = []
        for service in services:
            protocol = service.get('protocol', '')
            ports = service.get('ports', [])
            port_ranges = []
            for port in ports:
                port_from = port.get('from')
                port_to = port.get('to')
                if port_from == port_to:
                    port_ranges.append(str(port_from))
                else:
                    port_ranges.append(f"{port_from}-{port_to}")
            if port_ranges:
                service_str.append(f"{protocol}/{','.join(port_ranges)}")
            else:
                service_str.append(protocol)

        vendor = finding.get('vendor')
        name = finding.get('name')
        comments = finding.get('comments')
        evidence = finding.get('evidence', {})

        return {
            "Rule ID": finding.get('rule_id', ''),
            "Check ID": finding.get('check_id', ''),
            "Title": finding.get('title', ''),
            "Severity": (finding.get('severity', '') or '').capitalize(),
            "Reason": finding.get('reason', ''),
            "Recommendation": finding.get('recommendation', ''),
            "Source Addresses": ', '.join(finding.get('src_addrs', []) or []),
            "Destination Addresses": ', '.join(finding.get('dst_addrs', []) or []),
            "Services": ', '.join(service_str),
            "Vendor": vendor.capitalize() if vendor else '',
            "Rule Name": name if name is not None else '',
            "Comments": comments if comments is not None else '',
            "Policy Name": evidence.get('policy_name', '') if evidence else '',
            "Hit Count": evidence.get('hit_count', '') if evidence else '',
            "Labels": ', '.join(finding.get('labels', []) or []),
        }

    def export_to_csv(self, data, filename=None, show_dialog=True):
        """
        Export data to CSV format.
        """
        # We already have JSON findings; CSV flattens structure and GUI dialogs break automation.
        # CSV parser should be a seperated file to avoid noise
        raise NotImplementedError("CSV export disabled for CLI pipeline (use JSON findings + PDF).")

        # all uncommented below is not needed
        # try:
        #     if show_dialog:
        #         filepath = filedialog.asksaveasfilename(
        #             defaultextension=".csv",
        #             filetypes=[("CSV files", "*.csv")],
        #             initialdir=self.downloads_folder
        #         )
        #         if not filepath:
        #             return None
        #     else:
        #         if filename is None:
        #             filename = f"FireFind_Results_{self.get_timestamp()}.csv"
        #         filepath = os.path.join(self.downloads_folder, filename)
        #
        #     with open(filepath, "w", newline="", encoding="utf-8") as f:
        #         if data:
        #             csv_data = [self._flatten_finding_for_csv(item) for item in data]
        #             headers = ["Rule ID", "Check ID", "Title", "Severity", "Reason", "Recommendation",
        #                        "Source Addresses", "Destination Addresses", "Services", "Vendor",
        #                        "Rule Name", "Comments", "Policy Name", "Hit Count", "Labels"]
        #             writer = csv.DictWriter(f, fieldnames=headers)
        #             writer.writeheader()
        #             writer.writerows(csv_data)
        #         else:
        #             writer = csv.writer(f)
        #             writer.writerow(headers)
        #
        #     messagebox.showinfo("Export Complete", f"CSV exported successfully to:\n{filepath}")
        #     return filepath
        # except Exception as e:
        #     messagebox.showerror("Export Error", f"Failed to export CSV:\n{str(e)}")
        #     return None

    # Excel disabled not needed heavy deps, unrelated at this stage of the pipeline
    def export_to_excel(self, data, filename=None, show_dialog=True):
        """
        Export data to Excel format.
        """
        raise NotImplementedError("Excel export disabled for CLI pipeline (use JSON findings + PDF).")

        # no need for code below
        # try:
        #     if show_dialog:
        #         filepath = filedialog.asksaveasfilename(
        #             defaultextension=".xlsx",
        #             filetypes=[("Excel files", "*.xlsx")],
        #             initialdir=self.downloads_folder
        #         )
        #         if not filepath:
        #             return None
        #     else:
        #         if filename is None:
        #             filename = f"FireFind_Results_{self.get_timestamp()}.xlsx"
        #         filepath = os.path.join(self.downloads_folder, filename)
        #
        #     if data:
        #         excel_data = [self._flatten_finding_for_csv(item) for item in data]
        #         df = pd.DataFrame(excel_data)
        #     else:
        #         df = pd.DataFrame(columns=[...])
        #
        #     with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        #         df.to_excel(writer, sheet_name='FireFind Results', index=False)
        #         # formatting...
        #
        #     messagebox.showinfo("Export Complete", f"Excel file exported successfully to:\n{filepath}")
        #     return filepath
        # except Exception as e:
        #     messagebox.showerror("Export Error", f"Failed to export Excel:\n{str(e)}")
        #     return None

    # PDF modified
    def export_to_pdf(self, data, filename=None, show_dialog=True,
                      *, logo_path=None, ttf_path=None):
        """
        Export data to PDF format with professional formatting.

        whats changed frorm original code:
        - No GUI popups; we always write directly to a file.
        - Unicode-safe: if ttf_path is provided, use it; otherwise ASCII-sanitize text.
        - Signature kept compatible (show_dialog exists but is ignored).
        """
        # ignore GUI flow; select a path directly
        if filename is None:
            filename = f"FireFind_Report_{self.get_timestamp()}.pdf"
            filepath = os.path.join(self.downloads_folder, filename)
        else:
            filepath = filename

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        # Create PDF
        pdf = FireFindPDF(ttf_path=ttf_path, logo_path=logo_path)
        pdf.add_page()

        # Add findings
        if data:
            pdf.add_findings_table(data)
        else:
            pdf._set_font_regular(12)
            pdf.cell(0, 10, pdf._safe('No findings to report.'), new_x="LMARGIN", new_y="NEXT")

        # Output PDF
        pdf.output(filepath)
        return filepath


class FireFindPDF(FPDF):
    """Custom PDF class for FireFind reports."""

    def __init__(self, ttf_path=None, logo_path=None):
        super().__init__()
        self.report_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logo_path = logo_path  # CHANGED: no hardcoded file; pass path if you have a logo

        #  Unicode-safe: try to register a TTF; fallback to core fonts + ASCII sanitizer
        self.using_unicode = False
        if ttf_path and os.path.exists(ttf_path):
            try:
                self.add_font("UNI", "", ttf_path, uni=True)
                self.add_font("UNIB", "", ttf_path, uni=True)
                self.using_unicode = True
            except Exception:
                self.using_unicode = False

    # tiny helpers to pick fonts safely
    def _set_font_regular(self, size):
        if self.using_unicode:
            self.set_font('UNI', '', size)
        else:
            self.set_font('Helvetica', '', size)

    def _set_font_bold(self, size):
        if self.using_unicode:
            self.set_font('UNIB', '', size)
        else:
            self.set_font('Helvetica', 'B', size)

    def _safe(self, text):
        return text if self.using_unicode else _ascii_sanitize(text)

    def header(self):
        """Add header to each page."""
        # (Old behavior kept, but logo now optional via param)
        if self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, x=10, y=8, w=10, h=10)

        self._set_font_bold(20)
        self.cell(0, 10, self._safe('FireFind Security Report'), new_x="LMARGIN", new_y="NEXT", align='C')

        self._set_font_regular(12)
        self.cell(0, 10, self._safe(f'Generated on: {self.report_datetime}'),
                  new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(10)

    def footer(self):
        """Add footer to each page."""
        self.set_y(-15)
        self._set_font_regular(8)
        self.cell(0, 10, self._safe(f'Page {self.page_no()}'), align='C')

    def _safe_ascii(self, s: str) -> str:
        """Make text safe for the default core font (replace problematic unicode)."""
        if s is None:
            return ""
        s = str(s)
        return (s.replace("…", "...")
                .replace("–", "-").replace("—", "-")
                .replace("’", "'").replace("‘", "'")
                .replace("“", '"').replace("”", '"'))

    def _prepare_for_wrap(self, s: str) -> str:
        """Sanitize text and add break opportunities after commas/semicolons."""
        txt = self._safe_ascii(s)
        # ensure ",X" -> ", X" and ";X" -> "; X" so FPDF can wrap after punctuation
        return re.sub(r'([,;])(\S)', r'\1 \2', txt)

    def _service_to_str(self, s: dict) -> str:
        proto = s.get('protocol', '')
        ports = s.get('ports', []) or []
        if proto == 'any' or not ports:
            return proto or 'any'
        parts = []
        for rng in ports:
            lo = rng.get('from')
            hi = rng.get('to')
            if lo == hi:
                parts.append(f"{proto}/{lo}")
            else:
                parts.append(f"{proto}/{lo}-{hi}")
        return ','.join(parts)


    def add_findings_table(self, data):
        """Add findings data as a formatted table with robust wrapping/alignment."""
        self.set_font(self._base_font if hasattr(self, "_base_font") else "Helvetica", 'B', 12)
        self.cell(0, 10, 'Security Findings Summary', new_x="LMARGIN", new_y="NEXT", align='L')
        self.ln(5)

        # Summary counts
        severity_counts = {}
        for finding in data:
            severity = finding.get('severity', 'Unknown').title()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        self.set_font(self._base_font if hasattr(self, "_base_font") else "Helvetica", '', 10)
        self.cell(0, 6, f'Total Findings: {len(data)}', new_x="LMARGIN", new_y="NEXT", align='L')
        for severity, count in sorted(severity_counts.items()):
            self.cell(0, 6, f'{severity}: {count}', new_x="LMARGIN", new_y="NEXT", align='L')
        self.ln(5)

        # Table headers
        self.set_font(self._base_font if hasattr(self, "_base_font") else "Helvetica", 'B', 6)
        col_widths = [15, 40, 35, 35, 25, 15, 15]  # adjust widths to your taste
        headers = ['Rule ID', 'Title', 'Source', 'Destination', 'Service', 'Severity', 'Vendor']
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, header, border=1, align='C')
        self.ln()

        # We will manage page breaks manually during the table
        SAFE_BOTTOM = 20  # mm; must be >= footer height (footer uses set_y(-15))
        self.set_auto_page_break(auto=False, margin=SAFE_BOTTOM)

        # Table rows
        self.set_font(self._base_font if hasattr(self, "_base_font") else "Helvetica", '', 7)
        self.set_auto_page_break(auto=False, margin=self.b_margin)
        line_h = 6  # line height when writing wrapped lines

        for finding in data:
            # 1) build text for each column (keep your current column order)
            row_data = [
                str(finding.get('rule_id', '')),
                str(finding.get('title', '') or ''),
                ', '.join(finding.get('src_addrs', [])),
                ', '.join(finding.get('dst_addrs', [])),
                ', '.join(self._service_to_str(s) for s in finding.get('services', [])),
                str(finding.get('severity', '')).capitalize(),
                (str(finding.get('vendor')) or '').capitalize(),
            ]

            # 2) measure wrapped lines for each column (no drawing yet)
            line_h = 7  # line height; smaller -> more lines fit
            measured = []
            for i, text in enumerate(row_data):
                txt = self._prepare_for_wrap(text)  # make commas breakable, sanitize
                lines = self.multi_cell(col_widths[i],  # << use your existing col_widths
                                        line_h,
                                        txt,
                                        border=0,
                                        align='L',
                                        split_only=True)  # << important: measure only
                measured.append(lines or [""])

            # 3) pick row height = tallest column (in lines) * line height
            max_lines = max(len(ls) for ls in measured)
            row_h = max_lines * line_h

            # 4) page-break preflight: if row won’t fit, new page + redraw headers
            SAFE_BOTTOM = 20  # mm, bigger than your footer
            if self.get_y() + row_h > self.h - SAFE_BOTTOM:
                self.add_page()
                self.set_font("Helvetica", 'B', 7)
                for i, header in enumerate(headers):
                    self.cell(col_widths[i], 8, header, border=1, align='C')
                self.ln()
                self.set_font("Helvetica", '', 7)

            # 5) draw row: one rectangle per cell with same height, then print lines inside
            y_top = self.get_y()
            x_left = self.l_margin
            for i, lines in enumerate(measured):
                w = col_widths[i]
                # left edge of this cell = left margin + sum of previous widths
                x_cell = x_left + sum(col_widths[:i])
                y_cell = y_top

                # border box for the entire cell (expands vertically)
                self.rect(x_cell, y_cell, w, row_h)

                # write each wrapped line inside with small padding
                for j, ln in enumerate(lines):
                    self.set_xy(x_cell + 2, y_cell + j * line_h + 1)
                    self.multi_cell(w - 4, line_h, self._safe_ascii(ln), border=0, align='L')

            # 6) move cursor to the next row (same left, y + row height)
            self.set_xy(x_left, y_top + row_h)

        # restore normal page-break behavior after the table
       # self.set_auto_page_break(auto=True, margin=SAFE_BOTTOM)


# Demo
def demo_export():
    """Quick demo for sanity (uses new-schema-ish rows)."""
    sample_data = [
        {
            "rule_id": "419",
            "vendor": "fortinet",
            "enabled": True,
            "action": "allow",
            "src_addrs": ["CLIENT_CloudPC"],
            "dst_addrs": ["OUT-PRD-VL0"],
            "services": [{"protocol": "any", "ports": []}],
            "raw": {"vendor": "fortinet", "rule_id": "419", "src": "CLIENT_CloudPC", "dst": "OUT-PRD-VL0",
                    "service": "ALL", "action": "Accept", "reason": "", "severity": "info"},
            "name": None,
            "comments": None,
            "title": "Rule 419",
            "severity": "low",
        }
    ]
    exporter = ExportManager()
    print("Testing export to PDF (no GUI)...")
    out = exporter.export_to_pdf(sample_data, filename=os.path.join("results", "report.pdf"),
                                 logo_path=None, ttf_path=None)
    print("PDF ->", os.path.abspath(out))


#  CLI runner so we can do: python -m firefind.export_manager <inputfile> [--out results/report.pdf]
if __name__ == "__main__":
    import sys, json, argparse

    parser = argparse.ArgumentParser(description="Generate FireFind PDF report from JSON or JSONL findings file.")
    parser.add_argument("input", help="Path to input .json or .jsonl file (from the risk engine output).")
    parser.add_argument("--out", help="Output PDF path (default: results/report.pdf)", default="results/report.pdf")
    parser.add_argument("--ttf", help="Optional Unicode TTF font (e.g., assets/fonts/DejaVuSans.ttf)", default=None)
    args = parser.parse_args()

    # Load the input file (handles JSON or JSONL)
    if not os.path.exists(args.input):
        sys.exit(f"[ERROR] File not found: {args.input}")

    with open(args.input, "r", encoding="utf-8") as f:
        if args.input.lower().endswith(".jsonl"):
            data = [json.loads(line) for line in f if line.strip()]
        else:
            data = json.load(f)

    exporter = ExportManager()
    pdf_path = exporter.export_to_pdf(data, filename=args.out, ttf_path=args.ttf)

    print(f"[OK] PDF report created at: {os.path.abspath(pdf_path)}")

