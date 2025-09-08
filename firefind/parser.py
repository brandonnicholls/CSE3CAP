# firefind/parser.py
# Robust parser for CSV/XLSX firewall exports -> FireFind schema rows.
# Schema fields per row: vendor, rule_id, src, dst, service, action, reason, severity

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Dict, Any, List, Optional, Tuple
import re
import pandas as pd


# ---------- normalization & synonyms ----------

def _norm(s: str) -> str:
    """Normalize header-ish strings for matching: lowercase, strip, drop non-alphanumerics."""
    s = (str(s) if s is not None else "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "", s)

# Canonical field names -> acceptable (normalized) header tokens
CANDS = {
    "vendor":  {"vendor","device","platform","firewall","fw"},
    "rule_id": {"ruleid","id","name","rule","policyid","policy","rulename","uuid","no","number"},
    "src":     {"src","source","from","srcip","sourceip","srcaddress","sourceaddress","srcaddr",
                "sourceaddr","sourcezone","srczone","srcinterface","srcintf","origsrc","originalsource"},
    "dst":     {"dst","destination","to","dstip","destip","destinationaddress","dstaddress","dstaddr",
                "destinationaddr","destzone","dstzone","dstinterface","dstintf","origdst","originaldestination"},
    "service": {"service","services","application","applications","appid","app","protocol","port",
                "serviceport","servicesapplications","servicesandapplications"},
    "action":  {"action","decision"},
    "reason":  {"reason","comment","description","notes","note","remark"},
    "severity":{"severity","risk","risklevel","level","priority"},
}
ALL_CANDS = set().union(*CANDS.values())


# ---------- action handling & filters ----------

_VALID_ACTIONS = {"accept","allow","permit","deny","drop","reject","reset","block"}
_ACTION_ALIASES = {
    "allow": "accept",
    "permit": "accept",
    "accept": "accept",
    "deny": "deny",
    "drop": "drop",
    "reject": "reject",
    "reset": "reset",
    "block": "block",
}

def _normalize_action(val: str) -> str:
    if not val:
        return ""
    return _ACTION_ALIASES.get(val.strip().lower(), "")

def _is_real_action(val: str) -> bool:
    return _normalize_action(val) != ""


# ---------- sheet utilities ----------

def list_sheets(path: str) -> List[str]:
    """Return Excel sheet names (if Excel)."""
    xls = pd.ExcelFile(path)
    return list(xls.sheet_names)


# ---------- header detection for stacked/merged headers ----------

def _dedup_headers(headers: List[str]) -> List[str]:
    seen = {}
    out: List[str] = []
    for h in headers:
        base = (h or "").strip() or "col"
        key = base.lower()
        if key not in seen:
            seen[key] = 1; out.append(base)
        else:
            seen[key] += 1; out.append(f"{base}_{seen[key]}")
    return out

def _header_token_score(vals: List[str]) -> int:
    # Score a set of cell values for how "header-like" they are (token presence).
    n = 0
    for v in vals:
        vn = _norm(v)
        if vn in ALL_CANDS or any(t in vn for t in ALL_CANDS):
            n += 1
    return n

def _detect_header_base(raw: pd.DataFrame, scan_rows: int) -> int:
    """
    Pick a base row index likely to be header by scanning a window
    (rows i-1, i, i+1) and maximizing header-token score.
    """
    best_i, best_score = 0, -1
    limit = min(scan_rows, len(raw))
    for i in range(limit):
        window: List[str] = []
        for r in (i-1, i, i+1):
            if 0 <= r < len(raw):
                window.extend([str(x) for x in raw.iloc[r].tolist()])
        score = _header_token_score(window)
        if score > best_score:
            best_i, best_score = i, score
    return best_i

def _compose_headers_from_window(raw: pd.DataFrame, base: int) -> List[str]:
    """
    For each column, choose the lowest non-empty label among (base+1, base, base-1).
    This handles stacked headers like:
        Row N-1:  Name   Source   Destination   Service  Action
        Row N:           Src IP   Dst IP        Apps     Decision
    """
    cols = raw.shape[1]
    headers: List[str] = []
    for j in range(cols):
        chosen = ""
        for r in (base+1, base, base-1):
            if 0 <= r < len(raw):
                val = str(raw.iat[r, j]) if raw.iat[r, j] is not None else ""
                val = val.strip()
                if val and val != "-":
                    chosen = val; break
        headers.append(chosen or f"col{j+1}")
    return _dedup_headers(headers)

def _read_with_stacked_headers(path: str, sheet: Optional[str], scan: int, skip: int) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str).fillna("")
    if skip:
        raw = raw.iloc[skip:].reset_index(drop=True)
    base = _detect_header_base(raw, scan)
    headers = _compose_headers_from_window(raw, base)
    # Drop header rows we consumed (up to base+1). Simple and robust:
    start = min(base + 2, len(raw) - 1)
    df = raw.iloc[start + 1:].copy()
    df.columns = headers
    return df.fillna("")

def _read_best_sheet(path: str, scan: int) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    best_df, best_score = None, -1
    for s in xls.sheet_names:
        df = _read_with_stacked_headers(path, s, scan, skip=0)
        score = sum(1 for v in _pick_columns(df).values() if v)
        if score > best_score:
            best_df, best_score = df, score
    return best_df if best_df is not None else pd.read_excel(path, dtype=str).fillna("")


# ---------- column picking & value-based guessing ----------

def _pick_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Map dataframe columns to canonical fields using exact or substring matches
    on normalized header names.
    """
    cols_norm = {c: _norm(c) for c in df.columns}
    chosen: Dict[str, Optional[str]] = {}
    for field, options in CANDS.items():
        found = None
        # exact
        for c, cn in cols_norm.items():
            if cn in options:
                found = c; break
        # substring (handles "Service & Applications" -> "service")
        if not found:
            for c, cn in cols_norm.items():
                if any(opt in cn for opt in options):
                    found = c; break
        chosen[field] = found
    return chosen

# Prefer real service/app words or tcp/udp/port notation (avoid bare numbers)
_SVC_NAME_PAT = re.compile(r"\b(http|https|ssh|dns|smtp|imap|pop3|rdp|ftp|ntp|snmp|sql|mysql|mssql|oracle)\b", re.I)
_SVC_PORT_PAT = re.compile(r"\b(?:tcp/\d+|udp/\d+|port\s*\d+)\b", re.I)
_IP_PAT       = re.compile(r"\b(\d{1,3}\.){1,3}\d{1,3}(?:/\d{1,2})?\b")
_ADDR_HINTS   = ("any","group","addr","address","host","net","zone","subnet","range","object")

def _score_service_col(vals: List[str]) -> int:
    s = 0
    for v in vals:
        v = str(v or "")
        if _SVC_NAME_PAT.search(v): s += 2
        if _SVC_PORT_PAT.search(v): s += 1
    return s

def _score_addr_col(vals: List[str]) -> int:
    s = 0
    for v in vals:
        v = (str(v) or "").lower()
        if _IP_PAT.search(v): s += 2
        if any(h in v for h in _ADDR_HINTS): s += 1
        if v in ("any","all"): s += 1
    return s

def _guess_by_values(df: pd.DataFrame, picks: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """If headers didn't map, infer service/src/dst by looking at values."""
    sample = df.head(200)
    cols = list(sample.columns)
    col_vals = {c: [str(x) for x in sample[c].tolist()] for c in cols}

    # service
    if not picks.get("service"):
        scores = sorted(((c, _score_service_col(col_vals[c])) for c in cols),
                        key=lambda x: x[1], reverse=True)
        if scores and scores[0][1] > 0:
            picks["service"] = scores[0][0]

    # src/dst
    addr_scores = sorted(((c, _score_addr_col(col_vals[c])) for c in cols),
                         key=lambda x: x[1], reverse=True)
    used = {picks.get("service"), picks.get("action"),
            picks.get("vendor"), picks.get("reason"),
            picks.get("severity"), picks.get("rule_id")}
    addr_candidates = [c for c, sc in addr_scores if sc > 0 and c not in used]

    if not picks.get("src") and addr_candidates:
        picks["src"] = addr_candidates[0]
    if not picks.get("dst") and len(addr_candidates) > 1:
        picks["dst"] = addr_candidates[1] if addr_candidates[1] != picks.get("src") \
                       else (addr_candidates[2] if len(addr_candidates) > 2 else None)

    return picks


# ---------- helpers for cell values ----------

def _flat(v: Any) -> str:
    """Flatten multiline cells to a single-line, semicolon-separated string."""
    s = "" if v is None else str(v)
    return " ; ".join(s.splitlines()).strip()


# ---------- public API ----------

def parse(path: str,
          sheet: Optional[str] = None,
          header_scan_rows: int = 15,
          skip_rows: int = 0) -> Iterable[Dict[str, Any]]:
    """
    Parse a vendor CSV/XLSX export into FireFind schema rows.

    Args:
        path: path to CSV/XLSX file.
        sheet: Excel sheet name (if None, auto-pick the best sheet).
        header_scan_rows: how many initial rows to scan to detect stacked headers.
        skip_rows: lines to skip before header detection (rarely needed).

    Returns:
        Iterable of dicts with keys:
        vendor, rule_id, src, dst, service, action, reason, severity
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(path)

    # Read dataframe
    if p.suffix.lower() in {".xlsx", ".xls"}:
        df = _read_with_stacked_headers(str(p), sheet, header_scan_rows, skip_rows) \
             if sheet else _read_best_sheet(str(p), header_scan_rows)
    elif p.suffix.lower() == ".csv":
        # Let pandas infer delimiter; keep text
        df = pd.read_csv(p, dtype=str, engine="python").fillna("")
    else:
        raise ValueError(f"Unsupported file type: {p.suffix}")

    # Column mapping, with value-based fallback if needed
    picks = _pick_columns(df)
    if not (picks.get("src") and picks.get("dst") and picks.get("service")):
        picks = _guess_by_values(df, picks)

    # Optional vendor inference from sheet name (helps your EXTERNAL-FW-DC export)
    vendor_default = "unknown"
    if sheet and "firewall policy" in sheet.lower():
        vendor_default = "checkpoint"

    # Build normalized records
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        action_raw = row.get(picks.get("action",""), "") if picks.get("action") else ""
        action = _normalize_action(action_raw)

        rec = {
            "vendor":   (_flat(row.get(picks.get("vendor",""), "")) if picks.get("vendor") else vendor_default) or vendor_default,
            "rule_id":  _flat(row.get(picks.get("rule_id",""),  "")) if picks.get("rule_id")  else "",
            "src":      _flat(row.get(picks.get("src",""),      "")) if picks.get("src")      else "",
            "dst":      _flat(row.get(picks.get("dst",""),      "")) if picks.get("dst")      else "",
            "service":  _flat(row.get(picks.get("service",""),  "")) if picks.get("service")  else "",
            "action":   action if action else "",
            "reason":   _flat(row.get(picks.get("reason",""),   "")) if picks.get("reason")   else "",
            "severity": _flat(row.get(picks.get("severity",""), "")) if picks.get("severity") else "info",
        }

        # Keep only real rules: must have a valid action and at least one other identifying field
        if _is_real_action(rec["action"]) and any(rec[k] for k in ("src","dst","service","rule_id")):
            records.append(rec)

    return records
