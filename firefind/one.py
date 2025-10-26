# firefind/one.py
# Parser-only CLI: CSV/XLSX -> flat CSV + optional v0.1 JSONL
from __future__ import annotations
from .csv_robust import read_csv_loose_as_df, rebuild_with_header

import io

"""
quick context (for future me + marker):
this script is the small "parser-only" tool. it reads one firewall export
(csv or xlsx), tries to figure out the header row, extracts rule-ish columns,
and writes:
  1) a flat CSV (same fields as we parsed), and
  2) optionally a v0.1 normalized JSONL (for the rest of FireFind).
kept it simple on purpose: mild heuristics, some defaults (ex: severity=info),
and a helper to auto-try sheets/scan/skip combos if the header is messy.
"""

import argparse, csv, json, sys, re
from pathlib import Path
from typing import Optional, Dict, Any, List, Iterable, Tuple

import pandas as pd
from .v01 import to_v01

# small utils

def _lc(s: str | None) -> str:
    # lowercase/trim helper (used a couple of times)
    return (s or "").strip().lower()

def json_dumps(o: Any) -> str:
    # compact json (readable in git diffs; no weird escapes)
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))

def write_flat_csv(rows: List[dict], path: Path) -> None:
    # write the "flat" rules so folks can open in excel without drama
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["vendor","rule_id","src","dst","service","action","reason","severity"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            # bug fixed ( do not fill severity with info,if not exist leave empty)
            out = {k: r.get(k, "") for k in cols}
            w.writerow(out)

     #we will use if we end up dealing with multiple vendors this is will help instead of hardcoding
     #hundreds of more regexes into v01
"""""
def load_svc_map(path: Optional[str]) -> Optional[Dict[str, Any]]:
    # optional: user can pass a JSON map for vendor service names -> proto/ports
    if not path: return None
    p = Path(path)
    if not p.is_file():
        print(f"Warning: --svc-map not found: {p}", file=sys.stderr)
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as e:
        print(f"Warning: bad --svc-map JSON: {e}", file=sys.stderr)
        return None
       """

# vendor detection (file-level)
VENDOR_PATTERNS = [
    (r"forti[_\s\-]?(gate|os|net)",          "fortinet"),

    (r"\bsophos\b|\b(xg|utm)\b",             "sophos"),
    (r"\bbarracuda\b",                       "barracuda"),
    (r"\b(checkpoint|check\s*point|gaia)\b", "checkpoint"),
    (r"\bwatch\s*guard\b|\bwatchguard\b",    "watchguard"),
]

def _canon_vendor_text(s: str | None) -> str | None:
    if not s:
        return None
    text = str(s).lower()
    import re as _re
    for pat, slug in VENDOR_PATTERNS:
        if _re.search(pat, text):
            return slug
    return None

def detect_vendor_from_xlsx_header(xlsx_path: str) -> str | None:
    """Read just the top rows (merged header area) to spot vendor."""
    try:
        head = pd.read_excel(xlsx_path, nrows=6, header=None, dtype=str)
        blob = " | ".join(v for v in head.fillna("").to_numpy().ravel().tolist() if str(v).strip())
        return _canon_vendor_text(blob)
    except Exception:
        return None

def detect_vendor_from_filename(path: str) -> str | None:
    from pathlib import Path as _P
    return _canon_vendor_text(_P(path).name)


#### header detection

def _nk(s: str) -> str:
    # "normalize key": keep a-z0-9 only, so "Destination/s" -> "destinations"
    return re.sub(r"[^a-z0-9]+", "", str(s or "").strip().lower())

# candidates we look for across messy headers
CANDIDATES = {
    "rule_id": {
        "rule","ruleid","id","no","number","name","policyid","policy","uuid"
    },
    "src": {
        "source","sources","src","srcaddr","srcaddress","sourceaddress"
    },
    "dst": {
        "destination","destinations","destination/s","dst","dstaddr","dstaddress","destinationaddress"
    },
    "service": {
        "service","services","servicesapplications","services&applications"
    },
    "action": {
        "action","actions"
    },
    "reason": {
        "comment","comments","remark","remarks","reason","notes","description"
    },
    "severity": {
        "severity","risk","priority"
    },
}

def _score_header_row(row_vals: List[str]) -> Tuple[int, Dict[str,int]]:
    # count how many target fields appear in this row; return hit count + indexes
    hits = 0; idxs: Dict[str,int] = {}
    for i, v in enumerate(row_vals):
        k = _nk(v)
        for field, keys in CANDIDATES.items():
            if field in idxs: continue
            if k in keys:
                idxs[field] = i; hits += 1
    return hits, idxs

def _find_header(df: pd.DataFrame, scan_rows: int) -> Tuple[int, Dict[str,int]]:
    # look at the first N rows to guess the header row
    best_hits, best_idxs, best_row = -1, {}, -1
    scan = min(len(df), max(1, scan_rows))
    for r in range(scan):
        row_vals = [str(x) for x in df.iloc[r].tolist()]
        hits, idxs = _score_header_row(row_vals)
        # we only accept rows that at least have the core columns
        if hits > best_hits and {"src","dst","service","action"}.issubset(idxs):
            best_hits, best_idxs, best_row = hits, idxs, r
    return best_row, best_idxs

# parser (CSV + XLSX)

def list_sheets(path: str) -> List[str]:
    # if it's an excel file, list its sheet names (useful for --list-sheets)
    p = Path(path)
    if p.suffix.lower() not in {".xlsx",".xls"}:
        return []
    try:
        xf = pd.ExcelFile(str(p))
        return list(xf.sheet_names)
    except Exception:
        # could be a weird/corrupted file; just return empty
        return []

#  add near the top with other imports
import io

#  add below list_sheets() or nearby
def _read_weird_csv_into_df(path: Path) -> pd.DataFrame:
    """
    Fix CSVs where each line is wrapped in outer quotes and padded with trailing commas.
    Example raw line:  "num,name,source,...,comments",,,,,,
    We strip outer quotes + trailing commas, then parse.
    """
    lines_raw = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    cleaned = []
    for line in lines_raw:
        s = line.strip()
        if not s:
            continue
        s = re.sub(r'(,)+\s*$', '', s)              # drop trailing commas
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            s = s[1:-1]                             # strip one pair of outer quotes
        cleaned.append(s)
    buf = io.StringIO("\n".join(cleaned))
    return pd.read_csv(buf, header=None, dtype=str, na_filter=False, encoding="utf-8", on_bad_lines="skip")

def _try_read_csv_normal_then_fallback(path: Path) -> pd.DataFrame:
    """
    Try normal read. If we get a single column that still contains commas/quotes,
    switch to the weird-CSV cleaner.
    """
    df0 = pd.read_csv(str(path), header=None, dtype=str, na_filter=False, encoding="utf-8", on_bad_lines="skip")
    if df0.shape[1] == 1:
        first = str(df0.iloc[0, 0])
        if (first.count(",") >= 3) or ('"' in first):
            df0 = _read_weird_csv_into_df(path)
    return df0

def _force_csv_df(path: Path) -> pd.DataFrame:
    """
    Robust CSV reader for lines like: "num,name,source,...,comments",,,,,,
    Strips a single pair of outer quotes and trailing commas from each line,
    then parses via Python's csv (so embedded quotes/commas stay correct).
    Returns a DataFrame with the proper header row as columns.
    """
    text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    cleaned = []
    for line in text:
        s = line.strip()
        if not s:
            continue
        # drop trailing commas
        s = re.sub(r'(,)+\s*$', '', s)
        # strip exactly one pair of outer quotes
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            s = s[1:-1]
        cleaned.append(s)

    import csv
    rows = list(csv.reader(io.StringIO("\n".join(cleaned))))
    if not rows:
        return pd.DataFrame()

    # First row is the header; normalize but keep original text
    header = rows[0]
    data = rows[1:]
    # Build DataFrame with header
    df = pd.DataFrame(data, columns=header)
    # Drop completely empty rows
    df = df[[c for c in df.columns if c is not None]]
    df = df.replace({None: ""}).fillna("")
    return df





def _load_df(path: Path, sheet: Optional[str], header_scan_rows: int, skip_rows: int) -> Optional[pd.DataFrame]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx",".xls"}:
        df0 = pd.read_excel(str(path), sheet_name=sheet, header=None, dtype=str, na_filter=False)
    else:
        # NEW: robust CSV ingestion (tolerates outer quotes, trailing commas, stray quotes)
        df0 = read_csv_loose_as_df(path)

    if skip_rows > 0:
        df0 = df0.iloc[skip_rows:].reset_index(drop=True)

    header_row, _ = _find_header(df0, header_scan_rows)
    if header_row < 0:
        return None

    if suffix in {".xlsx",".xls"}:
        hdr = header_row + (skip_rows or 0)
        return pd.read_excel(str(path), sheet_name=sheet, header=hdr, dtype=str, na_filter=False)

    # CSV: rebuild using the detected header row
    return rebuild_with_header(df0, header_row)






def parse(path: str, *, sheet: Optional[str] = None, header_scan_rows: int = 15, skip_rows: int = 0) -> Iterable[Dict]:
    # main generator: yields flat rule dicts
    p = Path(path)
    df = _load_df(p, sheet, header_scan_rows, skip_rows)
    if df is None:
        return
    # build a normalized->original column name map (so we can fetch values safely)
    cols_norm = {_nk(c): c for c in df.columns}
    def col(name_set: set[str]) -> Optional[str]:
        for nk, orig in cols_norm.items():
            if nk in name_set:
                return orig
        return None
    c_rule = col(CANDIDATES["rule_id"])
    c_src  = col(CANDIDATES["src"])
    c_dst  = col(CANDIDATES["dst"])
    c_svc  = col(CANDIDATES["service"])
    c_act  = col(CANDIDATES["action"])
    c_rsn  = col(CANDIDATES["reason"])
    c_sev  = col(CANDIDATES["severity"])

    # mild vendor guess: some Check Point exports have "Firewall Policy" sheet
    #vendor_guess = "checkpoint" if (isinstance(sheet, str) and "firewall policy" in sheet.lower()) else "unknown"
    # Strengthening name detection
    # file-level vendor detection (prefer XLSX header, else filename)
    if p.suffix.lower() in {".xlsx", ".xls"}:
        vendor_guess = detect_vendor_from_xlsx_header(str(p)) or detect_vendor_from_filename(str(p)) or "unknown"
    else:
        vendor_guess = detect_vendor_from_filename(str(p)) or "unknown"

    # iterate rows and skip obvious banners or empty lines
    for _, row in df.iterrows():
        def val(cn: Optional[str]) -> str:
            # helper to read + trim a cell safely
            return ("" if cn is None else str(row.get(cn, "")).strip())

        v_rule = val(c_rule)
        v_src  = val(c_src)
        v_dst  = val(c_dst)
        v_svc  = val(c_svc)
        v_act  = val(c_act)
        v_rsn  = val(c_rsn)
        v_sev  = val(c_sev)  # bug fixed removed the follwing: or "info" (leave empty if not there)

        # Skip non-rule/banner lines
        if not any([v_rule, v_src, v_dst, v_svc, v_act]):
            continue
        if v_src.lower() == "normalized interface" and v_dst.lower() == "normalized interface":
            continue
        if v_svc.lower() == "name" and not v_act:
            continue

        # if it looks like a rule, yield a flat dict
        yield {
            "vendor":   vendor_guess,
            "rule_id":  v_rule,
            "src":      v_src,
            "dst":      v_dst,
            "service":  v_svc,
            "action":   v_act,
            "reason":   v_rsn,
            "severity": v_sev,
        }

#  CLI plumbing

def try_parse(in_file: Path, sheet: Optional[str], header_scan: int, skip_rows: int) -> List[dict]:
    # try the given params; if user’s pandas is older/newer and types clash, fallback
    try:
        return list(parse(str(in_file), sheet=sheet, header_scan_rows=header_scan, skip_rows=skip_rows))
    except TypeError:
        # some pandas versions can be picky; retry with defaults
        return list(parse(str(in_file)))

def auto_find_best(in_file: Path) -> Dict[str, Any]:
    # brute-force a few reasonable combos to see which yields the most rows
    sheets = list_sheets(str(in_file)) if in_file.suffix.lower() in {".xlsx",".xls"} else [None]
    header_scans = [10, 15, 20, 25, 30]
    skips = [0, 1, 2, 3, 4, 5]
    best = {"count": -1, "sheet": None, "scan": None, "skip": None, "rules": []}
    for s in sheets:
        for scan in header_scans:
            for sk in skips:
                rules = try_parse(in_file, s, scan, sk)
                cnt = len(rules)
                if cnt > best["count"]:
                    best = {"count": cnt, "sheet": s, "scan": scan, "skip": sk, "rules": rules}
    return best

def dump_sheet(in_file: Path, sheet: str, out_dir: Path, rows: int = 50):
    # quick peek tool: dump the first N raw rows for a given sheet (no parsing)
    raw = pd.read_excel(str(in_file), sheet_name=sheet, header=None, dtype=str).fillna("")
    out = out_dir / f"{in_file.stem}.{sheet}.debug.csv"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw.iloc[:rows].to_csv(out, index=False, header=False, encoding="utf-8")
    print(f"Dumped raw preview: {out.resolve()}")

def main() -> int:
    # basic CLI wiring; flags are kept small so it’s not overwhelming
    ap = argparse.ArgumentParser(description="FireFind (parser-only)")
    ap.add_argument("input", help="Path to ONE CSV/XLSX firewall export")
    ap.add_argument("-o","--out", default="results", help="Output folder")
    ap.add_argument("--preview", type=int, default=5, help="Print first N parsed rules")
    ap.add_argument("--list-sheets", action="store_true", help="List worksheet names and exit")
    ap.add_argument("--sheet", default=None, help="Worksheet name to parse")
    ap.add_argument("--header-scan", type=int, default=15, help="Rows to scan to detect header row")
    ap.add_argument("--skip-rows", type=int, default=0, help="Rows to skip before header detection")
    ap.add_argument("--auto", action="store_true", help="Try sheets/combos and pick the best")
    ap.add_argument("--dump-sheet", default=None, help="Dump raw first 50 rows of the given sheet to CSV")
    ap.add_argument("--json-v01", action="store_true", help="Also write normalized v0.1 JSONL")
    ap.add_argument("--svc-map", default=None, help="JSON mapping of service object names -> services")
    args = ap.parse_args()

    in_file = Path(args.input)
    if not in_file.is_file():
        print(f"Error: input path is not a file: {in_file}", file=sys.stderr); return 2

    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)

    # Only list / dump helpers
    if args.list_sheets and in_file.suffix.lower() in {".xlsx",".xls"}:
        for s in list_sheets(str(in_file)): print(s)
        return 0
    if args.dump_sheet:
        dump_sheet(in_file, args.dump_sheet, out_dir); return 0

    # Parse (either auto-pick best combo or use the exact args)
    if args.auto:
        best = auto_find_best(in_file)
        print(
            f"AUTO chose -> sheet={best['sheet']!r} header_scan={best['scan']} skip_rows={best['skip']}  count={best['count']}")
        rules = best["rules"]
        chosen_sheet = best["sheet"]
    else:
        rules = try_parse(in_file, args.sheet, args.header_scan, args.skip_rows)
        print(f"Chosen -> sheet={args.sheet!r} header_scan={args.header_scan} skip_rows={args.skip_rows}")
        chosen_sheet = args.sheet

    print(f"Parsed rules from {in_file.name}: {len(rules)}")
    if args.preview and rules:
        # light summary so users can sanity-check quickly in the terminal
        print(f"Preview (first {min(args.preview, len(rules))} rules):")
        for i, r in enumerate(rules[:args.preview], 1):
            d = dict(r)
            print(f"  {i}. rule_id={d.get('rule_id')} src={d.get('src')} dst={d.get('dst')} service={d.get('service')} action={d.get('action')}")

    if not rules:
        # if nothing parsed, drop a small hint file with suggested next steps
        (out_dir / f"{in_file.stem}.NO_RULES.txt").write_text(
            "0 rules. Try:\n  --list-sheets\n  --auto\n  --sheet <name> --skip-rows N --header-scan M\n  --dump-sheet <name>\n",
            encoding="utf-8")
        print(f"0 rules parsed. Wrote hint: {out_dir / (in_file.stem + '.NO_RULES.txt')}")
        return 3


    # Optional normalized JSONL v0.1 (feeds the rest of FireFind)
    if args.json_v01:
        v01_path = out_dir / f"{in_file.stem}.rules.v01.jsonl"
        # Prefer file header, else filename, else (very last resort) sheet-name heuristic
        vendor_hint = None
        if in_file.suffix.lower() in {".xlsx", ".xls"}:
            vendor_hint = detect_vendor_from_xlsx_header(str(in_file))
        if not vendor_hint:
            vendor_hint = detect_vendor_from_filename(str(in_file))
        if not vendor_hint and isinstance(chosen_sheet, str) and "firewall policy" in chosen_sheet.lower():
            vendor_hint = "checkpoint"

        # if future svc_map is needed uncomment line below
        '''svc_map = load_svc_map(args.svc_map)'''
        with v01_path.open("w", encoding="utf-8") as f:
            for r in rules:
                f.write(json_dumps(to_v01(r, vendor_hint)) + "\n")
        print(f"✓ Wrote: {v01_path.resolve()}")


    # Flat CSV (simple view; risk engine is not involved here)
    out_csv = out_dir / f"{in_file.stem}.findings.csv"
    write_flat_csv(rules, out_csv)
    print(f"✓ Wrote: {out_csv.resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
