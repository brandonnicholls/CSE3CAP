# firefind/parsers/csv_parser.py
# CSV-only parser module (kept separate from XLSX).
# Reads header, maps aliases, yields rule dicts in a consistent shape.

from __future__ import annotations
import csv
from typing import List, Dict, Any, Optional

REQUIRED_KEYS = {"id", "action"}  # minimal keys to confirm header row

# Accept slight header wording differences (same set as XLSX for parity)
HEADER_ALIASES = {
    "id": {"id", "policy id", "policyid"},
    "name": {"name", "policy name"},
    "action": {"action"},
    "src_addr": {
        "address | user | device", "source", "src addr", "src address", "src addresses",
        "source address", "source addresses"
    },
    "dst_addr": {
        "address", "destination", "dst addr", "dst address", "dst addresses",
        "destination address", "destination addresses"
    },
    "service": {"service | name", "service", "services"},
    "comments": {"comments", "comment", "remarks", "notes"},
}

# Simple service name to default port map (same as XLSX)
WELL_KNOWN_SERVICES = {
    "ssh": 22,
    "rdp": 3389,
    "vnc": 5900,
    "http": 80,
    "https": 443,
}

def _norm(s) -> str:
    """Normalize any value to a stripped string (or empty)."""
    return "" if s is None else str(s).strip()

def _lower(s) -> str:
    """Lowercased normalized string."""
    return _norm(s).lower()

def _split_multi(val):
    """
    Split multi-value cells on newlines or commas.
    Normalize any-like tokens to ['any'].
    """
    if val is None:
        return []
    s = str(val).replace("\r", "").strip()
    if not s:
        return []
    parts = [p.strip() for p in s.split("\n") if p.strip()]
    if not parts and ("," in s):
        parts = [p.strip() for p in s.split(",") if p.strip()]
    # normalize “any”-like tokens
    if len(parts) == 1 and parts[0].lower() in {"any", "all", "0.0.0.0/0", "::/0"}:
        return ["any"]
    return parts

def _map_action(val) -> str:
    """Map vendor/wording variants into allow/deny/reject/other."""
    a = _lower(val)
    if a in {"accept", "allow", "permit"}: return "allow"
    if a in {"deny", "drop", "block"}:     return "deny"
    if a in {"reject"}:                    return "reject"
    return "other"

def _parse_services(cell):
    """
    Parse service tokens into [{protocol, ports:[{from,to}]}].
    - 'ssh' -> tcp/22
    - 'tcp/8080' -> tcp/8080
    - unknown groups -> protocol:any, ports:[]
    """
    tokens = _split_multi(cell)
    if not tokens:
        return [{"protocol": "any", "ports": []}]
    out = []
    for t in tokens:
        key = t.lower()
        if key in WELL_KNOWN_SERVICES:
            p = WELL_KNOWN_SERVICES[key]
            out.append({"protocol": "tcp", "ports": [{"from": p, "to": p}]})
        elif "/" in key:  # e.g., tcp/8080
            try:
                proto, port = key.split("/", 1)
                port = int(port)
                out.append({"protocol": proto.lower(), "ports": [{"from": port, "to": port}]})
            except Exception:
                out.append({"protocol": "any", "ports": []})
        else:
            out.append({"protocol": "any", "ports": []})
    return out

def _build_index_map(headers: List[str]) -> Dict[str, Optional[int]]:
    """
    Map canonical keys → column index by alias matching.
    """
    lower = [_lower(h) for h in headers]

    def find_idx(alias_set):
        for j, h in enumerate(lower):
            if h in alias_set:
                return j
        return None

    return {
        "id":    find_idx(HEADER_ALIASES["id"]),
        "name":  find_idx(HEADER_ALIASES["name"]),
        "action":find_idx(HEADER_ALIASES["action"]),
        "src":   find_idx(HEADER_ALIASES["src_addr"]),
        "dst":   find_idx(HEADER_ALIASES["dst_addr"]),
        "svc":   find_idx(HEADER_ALIASES["service"]),
        "cmt":   find_idx(HEADER_ALIASES["comments"]),
    }

def _looks_like_header(cells: List[str]) -> bool:
    """
    Decide if a row is a header by checking required keys + any of service/src/dst.
    """
    headers = [_norm(c) for c in cells]
    lower = [_lower(c) for c in headers]
    present = set()
    if any(h in HEADER_ALIASES["id"] for h in lower): present.add("id")
    if any(h in HEADER_ALIASES["action"] for h in lower): present.add("action")
    if any(h in HEADER_ALIASES["service"] for h in lower): present.add("service")
    if any(h in HEADER_ALIASES["src_addr"] for h in lower): present.add("src_addr")
    if any(h in HEADER_ALIASES["dst_addr"] for h in lower): present.add("dst_addr")
    return REQUIRED_KEYS.issubset(present) and ("service" in present or "src_addr" in present or "dst_addr" in present)

def _find_header_row_and_headers(rows: List[List[str]]):
    """
    Find header row within the first ~50 rows (CSV often has banner lines).
    Returns (row_index, headers_list). Fallback = first row.
    """
    scan = min(50, len(rows))
    for i in range(scan):
        if _looks_like_header(rows[i]):
            headers = [_norm(c) for c in rows[i]]
            # trim trailing empties
            while headers and headers[-1] == "":
                headers.pop()
            return i, headers
    first = rows[0] if rows else []
    headers = [_norm(c) for c in first]
    return 0, headers

class CsvParser:
    """
    CSV parser: detect header row, map columns by alias, emit rule dicts.
    """
    def parse(self, path: str) -> List[Dict[str, Any]]:
        rules: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return rules

        header_row_idx, headers = _find_header_row_and_headers(rows)
        idx = _build_index_map(headers)

        # If we didn't even find IDs & Action, nothing to do
        if idx["id"] is None or idx["action"] is None:
            return rules

        # iterate rows AFTER header row
        for r in rows[header_row_idx + 1:]:
            # Skip completely empty line
            if not any(c not in (None, "", " ") for c in r):
                continue

            def safe_get(j):
                return r[j] if j is not None and j < len(r) else None

            rid    = safe_get(idx["id"])
            action = safe_get(idx["action"])
            if rid in (None, "", 0):
                # Non-rule "section" rows typically have no ID
                continue

            # Grab a copy of raw (map header → value)
            rec = {headers[j]: (r[j] if j < len(r) else None) for j in range(len(headers))}

            name = safe_get(idx["name"])
            src  = safe_get(idx["src"])
            dst  = safe_get(idx["dst"])
            svc  = safe_get(idx["svc"])
            cmt  = safe_get(idx["cmt"])

            rule = {
                "rule_id": str(rid),
                "vendor": "fortinet",
                "name": name,
                "enabled": True,
                "action": _map_action(action),
                "src_addrs": _split_multi(src),
                "dst_addrs": _split_multi(dst),
                "services": _parse_services(svc),
                "comments": cmt,
                "raw": rec,
            }
            rules.append(rule)

        return rules
