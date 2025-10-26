# export_manager.py
# FireFind — Professional stakeholder PDF (severity-coloured cards; no data grid)
# USAGE:
#   python -m firefind.export_manager <input.jsonl|json> --out results/firefind_report.pdf [--ttf assets/fonts/DejaVuSans.ttf]
#
# Notes:
# - If --ttf is provided and the TTF exists, we render full Unicode. Otherwise we sanitize to ASCII for core fonts.
# - Layout: Cover → Summary → Finding Cards (one section per finding)

import os
import re
import json
import argparse
from datetime import datetime
from fpdf import FPDF

# ASCII fallbacks (only used when no TTF provided)
_ASCII_MAP = {
    "\u2013": "-", "\u2014": "-",
    "\u2018": "'", "\u2019": "'",
    "\u201C": '"', "\u201D": '"',
    "\u2026": "...",
    "\u00A0": " ",
}
def _ascii_sanitize(s):
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

def _service_to_str(service: dict) -> str:
    """Turn one service object into human-readable 'proto/port,port2' or 'any'."""
    if not service:
        return ""
    proto = (service.get("protocol") or "").lower()
    ports = service.get("ports") or []
    if proto == "any" or not ports:
        return proto or "any"
    frags = []
    for p in ports:
        lo, hi = p.get("from"), p.get("to")
        frags.append(str(lo) if lo == hi else f"{lo}-{hi}")
    return f"{proto}/{','.join(frags)}"

def _format_services(services: list) -> str:
    """Join service strings; keep it short but accurate."""
    parts = []
    for s in services or []:
        parts.append(_service_to_str(s))
    return ", ".join([p for p in parts if p]) or "—"

def _csvish_join(vals: list) -> str:
    return ", ".join([str(v) for v in (vals or [])]) or "—"

# PDF renderer
class FireFindPDF(FPDF):
    """
    Professional stakeholder report.
    - Flexible fonts: Unicode TTF if provided; else Helvetica + ASCII sanitization.
    - Sections: cover, summary, finding cards.
    """

    def __init__(self, *, ttf_path: str | None = None, logo_path: str | None = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=False, margin=18)
        self.logo_path = logo_path
        self.report_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Font config
        self.using_unicode = False
        self.base_font_reg = "Helvetica"
        self.base_font_bold = "Helvetica"

        if ttf_path and os.path.exists(ttf_path):
            try:
                # Register the same TTF twice for "regular" and "bold" weights (fpdf2 doesn't fake bold on TTF)
                self.add_font("UNI", "", ttf_path, uni=True)
                self.add_font("UNIB", "", ttf_path, uni=True)
                self.base_font_reg = "UNI"
                self.base_font_bold = "UNIB"
                self.using_unicode = True
            except Exception:
                self.using_unicode = False

        # Severity palette (WCAG-ish contrast friendly)
        self.sev_palette = {
            "Critical": (220, 53, 69),   # red
            "High":     (255, 127, 17),  # orange
            "Medium":   (255, 193, 7),   # amber
            "Low":      (13, 110, 253),  # blue
            "Info":     (108, 117, 125), # gray (fallback)
        }

        # Neutral accents
        self.accent_grey = (245, 246, 248)
        self.text_muted = (80, 85, 90)
        self.text_dark  = (25, 28, 32)
        self.rule_line  = (220, 224, 228)

    #  font helpers
    def _font(self, size=10, bold=False):
        if bold:
            self.set_font(self.base_font_bold, "", size)
        else:
            self.set_font(self.base_font_reg, "", size)

    def _safe(self, s: str) -> str:
        return s if self.using_unicode else _ascii_sanitize(s)

    #  drawing helpers
    def _hline(self, x=None, y=None, w=None):
        if x is None: x = self.l_margin
        if y is None: y = self.get_y()
        if w is None: w = self.w - self.l_margin - self.r_margin
        r,g,b = self.rule_line
        self.set_draw_color(r,g,b)
        self.line(x, y, x + w, y)

    def _section_title(self, text: str):
        self._font(13, bold=True)
        self.set_text_color(*self.text_dark)
        self.cell(0, 8, self._safe(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self._hline()
        self.ln(2)

    def _will_exceed(self, height: float) -> bool:
        """Check if adding 'height' would run past bottom margin."""
        safe_bottom = 18
        return (self.get_y() + height) > (self.h - safe_bottom)

    def _ensure_space(self, needed: float):
        """Insert a new page if content of height 'needed' won't fit."""
        if self._will_exceed(needed):
            self.add_page()

    # header/footer
    def header(self):
        # Simple, clean header (logo optional)
        top = 10
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, x=self.l_margin, y=top, w=16)
            except Exception:
                pass

        self._font(18, bold=True)
        self.set_text_color(*self.text_dark)
        self.set_y(top)
        self.cell(0, 10, self._safe("FireFind Security Report"), align="C", new_x="LMARGIN", new_y="NEXT")

        self._font(10)
        self.set_text_color(*self.text_muted)
        self.cell(0, 6, self._safe(f"Generated on: {self.report_datetime}"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-13)
        self._font(8)
        self.set_text_color(*self.text_muted)
        self.cell(0, 6, self._safe(f"Page {self.page_no()}"), align="C")

    #  cover + summary
    def add_cover(self, counts: dict):
        """Hero cover with big title & quick severity counts."""
        self.add_page()
        self.ln(30)

        self._font(22, bold=True)
        self.set_text_color(*self.text_dark)
        self.cell(0, 12, self._safe("Firewall Risk Identification — Findings Overview"),
                  align="C", new_x="LMARGIN", new_y="NEXT")

        self._font(11)
        self.set_text_color(*self.text_muted)
        self.cell(0, 7, self._safe("Automated analysis of firewall rules across vendors"),
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(10)

        # Card with counts
        left = self.l_margin
        width = self.w - self.l_margin - self.r_margin
        box_h = 40
        self._ensure_space(box_h + 8)
        self.set_fill_color(*self.accent_grey)
        self.rect(left, self.get_y(), width, box_h, style="F")
        self.ln(4)

        self._font(12, bold=True)
        self.set_text_color(*self.text_dark)
        self.cell(0, 8, self._safe("Security Findings Summary"), new_x="LMARGIN", new_y="NEXT")
        self._font(11)
        self.set_text_color(*self.text_muted)
        total = sum(counts.values())
        self.cell(0, 6, self._safe(f"Total Findings: {total}"),
                  new_x="LMARGIN", new_y="NEXT")

        # row of coloured chips
        self.ln(1)
        chip_h = 8
        for label in ["Critical", "High", "Medium", "Low"]:
            n = counts.get(label, 0)
            r,g,b = self.sev_palette.get(label, self.sev_palette["Info"])
            self.set_fill_color(r,g,b)
            self.set_text_color(255,255,255)
            self._font(10, bold=True)
            txt = f" {label}: {n} "
            self.cell(self.get_string_width(txt) + 4, chip_h, self._safe(txt), align="C", fill=True)
            self.cell(4, chip_h, "")  # spacing

        # reset text colour
        self.set_text_color(*self.text_dark)
        self.ln(12)

    # finding cards
    def _sev_color(self, severity: str):
        key = (severity or "").capitalize()
        return self.sev_palette.get(key, self.sev_palette["Info"])

    def _pair(self, label: str, value: str, label_w=40, line_h=6):
        """One-row label/value pair (wraps value)."""
        x = self.get_x(); y = self.get_y()
        self._font(9, bold=True); self.set_text_color(*self.text_muted)
        self.multi_cell(label_w, line_h, self._safe(label), border=0)
        self.set_xy(x + label_w, y)
        self._font(10); self.set_text_color(*self.text_dark)
        self.multi_cell(0, line_h, self._safe(value), border=0)
        self.ln(1)

    # measuring helpers (use split_only to avoid drawing while measuring)
    def _measure_lines(self, text: str, width: float, *, size=10, bold=False, line_h=6) -> int:
        """Return how many lines a multi_cell would consume with given font/width."""
        self._font(size, bold)
        lines = self.multi_cell(width, line_h, self._safe(text or "—"), split_only=True)
        return max(1, len(lines or [""]))

    def _measure_block(self, label: str, value: str, *, label_w: float, content_w: float,
                       label_size=9, value_size=10, line_h=6) -> float:
        """Label above value: total height (label + value + small spacing)."""
        n_label = self._measure_lines(label, content_w, size=label_size, bold=True, line_h=line_h)
        n_val   = self._measure_lines(value, content_w, size=value_size,  bold=False, line_h=line_h)
        # label line_h + value lines + spacing
        return (n_label * line_h) + (n_val * line_h) + 2.0

    def add_finding_cards(self, findings: list):
        self._section_title("Detailed Findings")

        # layout constants
        pad_x = 8.0
        pad_y_top = 4.0
        pad_y_bottom = 6.0
        line_h = 6.0

        for f in findings:
            # Extract fields
            rule_id = str(f.get("rule_id", "—"))
            name = str(f.get("name") or f.get("title") or "—")
            reason = str(f.get("reason") or "—")
            rec = str(f.get("recommendation") or "—")
            sev = str(f.get("severity") or "Info").capitalize()
            vendor = str(f.get("vendor") or "—").capitalize()
            src = _csvish_join(f.get("src_addrs"))
            dst = _csvish_join(f.get("dst_addrs"))
            svc = _format_services(f.get("services"))

            # measure everything BEFORE drawing the card
            x0 = self.l_margin
            w0 = self.w - self.l_margin - self.r_margin
            inner_x = x0 + pad_x + 2.0
            inner_w = w0 - (pad_x * 2) - 4.0

            # title + meta heights
            title_lines = self._measure_lines(name, inner_w, size=11, bold=True, line_h=line_h)
            meta_txt = f"Rule ID: {rule_id}    Vendor: {vendor}"
            meta_lines = self._measure_lines(meta_txt, inner_w, size=9, bold=False, line_h=line_h)

            # severity chip (fixed)
            chip_h = line_h

            # content blocks (label above value)
            h_reason = self._measure_block("Reason:", reason, label_w=26, content_w=inner_w, line_h=line_h)
            h_rec = self._measure_block("Recommendation:", rec, label_w=26, content_w=inner_w, line_h=line_h)
            h_sd = self._measure_block("Source → Destination:", f"{src}  →  {dst}", label_w=42, content_w=inner_w,
                                       line_h=line_h)
            h_svc = self._measure_block("Services:", svc, label_w=26, content_w=inner_w, line_h=line_h)

            # total card height
            need_h = (
                    pad_y_top
                    + (title_lines * line_h)
                    + 1.0
                    + (meta_lines * line_h)
                    + 1.0
                    + chip_h + 2.0
                    + 2.0
                    + h_reason + h_rec + h_sd + h_svc
                    + pad_y_bottom
            )

            # ensure space; if not, new page first
            self._ensure_space(need_h + 2.0)

            # draw card background (exact measured height) + severity ribbon
            y0 = self.get_y()
            self.set_fill_color(*self.accent_grey)
            self.rect(x0, y0, w0, need_h, style="F")
            r, g, b = self._sev_color(sev)
            self.set_fill_color(r, g, b)
            self.rect(x0, y0, 4.0, need_h, style="F")

            # now render content using the same widths/fonts used in measurement
            cur_y = y0 + pad_y_top
            self.set_xy(inner_x, cur_y)
            self._font(11, bold=True);
            self.set_text_color(*self.text_dark)
            self.multi_cell(inner_w, line_h, self._safe(name));
            cur_y = self.get_y()

            self.set_xy(inner_x, cur_y + 1.0)
            self._font(9);
            self.set_text_color(*self.text_muted)
            self.multi_cell(inner_w, line_h, self._safe(meta_txt));
            cur_y = self.get_y()

            # severity chip
            self.set_xy(inner_x, cur_y + 1.0)
            chip_txt = f" {sev} "
            cw = self.get_string_width(chip_txt) + 4.0
            self.set_fill_color(r, g, b);
            self.set_text_color(255, 255, 255)
            self._font(9, bold=True)
            self.cell(cw, chip_h, self._safe(chip_txt), fill=True, new_x="LMARGIN", new_y="NEXT")
            cur_y = self.get_y() + 2.0

            # block renderer (label above value)
            def block(label, value):
                nonlocal cur_y
                self.set_xy(inner_x, cur_y)
                self._font(9, bold=True);
                self.set_text_color(*self.text_muted)
                self.multi_cell(inner_w, line_h, self._safe(label))
                self.set_xy(inner_x, self.get_y())
                self._font(10);
                self.set_text_color(*self.text_dark)
                self.multi_cell(inner_w, line_h, self._safe(value))
                cur_y = self.get_y() + 2.0

            block("Reason:", reason)
            block("Recommendation:", rec)
            block("Source → Destination:", f"{src}  →  {dst}")
            block("Services:", svc)

            # move cursor to after the card
            self.set_y(y0 + need_h + 4.0)

    # glue
    def build(self, findings: list):
        # severity order
        order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

        def sev_key(f):
            s = str(f.get("severity", "Low")).capitalize()
            return order.get(s, 3)

        # sort first
        sorted_findings = sorted(findings or [], key=sev_key)

        # counts for cover
        counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for f in sorted_findings:
            s = str(f.get("severity", "Low")).capitalize()
            counts[s] = counts.get(s, 0) + 1

        self.add_cover(counts)
        self.add_finding_cards(sorted_findings)


class ExportManager:
    """CLI-facing manager (PDF only; CSV/XLSX intentionally disabled)."""

    def __init__(self):
        self.downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")

    def get_timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # Disabled (intentionally)
    def export_to_csv(self, *_args, **_kwargs):
        raise NotImplementedError("CSV export disabled for CLI pipeline (use JSON findings + PDF).")

    def export_to_excel(self, *_args, **_kwargs):
        raise NotImplementedError("Excel export disabled for CLI pipeline (use JSON findings + PDF).")

    def export_to_pdf(self, data: list, filename: str | None = None, show_dialog: bool = False,
                      *, logo_path: str | None = None, ttf_path: str | None = None) -> str:
        """Generate the stakeholder-friendly PDF."""
        if filename is None:
            filename = f"FireFind_Report_{self.get_timestamp()}.pdf"
            filepath = os.path.join(self.downloads_folder, filename)
        else:
            filepath = filename
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        pdf = FireFindPDF(ttf_path=ttf_path, logo_path=logo_path)
        data = data or []
        pdf.build(data)
        pdf.output(filepath)
        return filepath


# CLI runner
def _load_input(path: str) -> list:
    if not os.path.exists(path):
        raise SystemExit(f"[ERROR] File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        if path.lower().endswith(".jsonl"):
            return [json.loads(line) for line in f if line.strip()]
        return json.load(f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate FireFind stakeholder PDF from JSON/JSONL findings.")
    parser.add_argument("input", help="Path to findings .json or .jsonl")
    parser.add_argument("--out", help="Output PDF path (default: results/firefind_report.pdf)",
                        default="results/firefind_report.pdf")
    parser.add_argument("--ttf", help="Optional Unicode TTF (e.g., assets/fonts/DejaVuSans.ttf)", default=None)
    parser.add_argument("--logo", help="Optional logo image path (PNG/JPG)", default=None)
    args = parser.parse_args()

    findings = _load_input(args.input)
    exporter = ExportManager()
    out = exporter.export_to_pdf(findings, filename=args.out, ttf_path=args.ttf, logo_path=args.logo)
    print(f"[OK] PDF report created at: {os.path.abspath(out)}")
