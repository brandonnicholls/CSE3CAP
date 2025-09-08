# firefind/v01.py
from __future__ import annotations
import re
from typing import Dict, List, Tuple, Optional, Any

"""
Purpose: Convert one flat firewall-rule row (CSV/XLSX) into the FireFind v0.1 shape.
Scope: normalize strings, map actions to a small set, split src/dst lists,
and parse service tokens into (protocol + ports).
Assumptions: if a service is unclear, we fall back to "any" so the pipeline keeps moving.
Notes: this is intentionally simple; vendor-specific refinements can be added later.
TODO (future): detect disabled rules and fill 'name' when vendors provide it.
"""

# ---------- helpers

def _clean(s: str) -> str:
    # Trim spaces and tolerate None (common in spreadsheets)
    return (s or "").strip()

def _lower(s: str) -> str:
    # Lowercased version for easier matching/comparisons
    return _clean(s).lower()

def _split_multi(s: str) -> List[str]:
    """Split on newlines/semicolons/commas and drop empties."""
    # Some exports cram multiple values into one cell with \n, ;, or ,
    if not s:
        return []
    parts = re.split(r"[\n;,]+", str(s))
    return [p.strip() for p in parts if p and p.strip()]

def _strip_group_prefix(s: str) -> str:
    # Example: "Group Member (2): 10.1.1.0/24" → "10.1.1.0/24"
    return re.sub(r"^Group Member\s*\(\d+\):\s*", "", s, flags=re.IGNORECASE)

def _strip_label_prefixes(s: str) -> str:
    # Example: "FQDN: example.com" or "IP/Netmask: 10.0.0.0/8" → keep just the value
    return re.sub(r"^(FQDN:|IP/Netmask:\s*)", "", s, flags=re.IGNORECASE)

def _norm_addrs(field: Any) -> List[str]:
    # Normalize src/dst into a list; empty means "any" (explicit default)
    s = _clean(str(field))
    if not s:
        return ["any"]
    s = _strip_group_prefix(s)
    items = _split_multi(s)
    items = [_strip_label_prefixes(x) for x in items]
    return items or ["any"]

# ---------- action/vendor normalization

# Collapse vendor action verbs into a compact set we use everywhere
_ACTION_MAP = {
    "accept": "allow",
    "allow": "allow",
    "permit": "allow",
    "drop": "drop",
    "deny": "deny",
    "reject": "reject",
}

def _norm_action(a: Any) -> str:
    # Unrecognized actions become "other" so they’re visible in QA later
    a = _lower(str(a))
    return _ACTION_MAP.get(a, "other")

def _norm_vendor(vendor_hint: Optional[str], flat_vendor: Any) -> str:
    # Prefer the row’s vendor; if absent, try the hint; otherwise "unknown"
    v = (_lower(flat_vendor) or _lower(vendor_hint) or "unknown")
    return v

# ---------- service parsing

# Alias map: common names seen in real exports. Not exhaustive on purpose.
# Maps token -> list[(protocol, from_port, to_port)]. ICMP has no ports.
_ALIAS: Dict[str, List[Tuple[str, Optional[int], Optional[int]]]] = {
    # common L4
    "all":      [("any", None, None)],
    "any":      [("any", None, None)],
    "http":     [("tcp", 80, 80)],
    "https":    [("tcp", 443, 443)],
    "ssh":      [("tcp", 22, 22)],
    "ssh_version_2": [("tcp", 22, 22)],
    "telnet":   [("tcp", 23, 23)],
    "ftp":      [("tcp", 21, 21), ("tcp", 20, 20)],
    "ftp_basic":[("tcp", 21, 21), ("tcp", 20, 20)],
    "smtp":     [("tcp", 25, 25)],
    "rdp":      [("tcp", 3389, 3389)],
    "remote_desktop_protocol": [("tcp", 3389, 3389)],
    "ms-sql-server": [("tcp", 1433, 1433)],
    "mssql":    [("tcp", 1433, 1433)],
    "dns":      [("udp", 53, 53), ("tcp", 53, 53)],
    "dns_":     [("udp", 53, 53), ("tcp", 53, 53)],
    "kerberos": [("udp", 88, 88), ("tcp", 88, 88)],
    "kerberos_":[("udp", 88, 88), ("tcp", 88, 88)],
    "ntp":      [("udp", 123, 123)],
    "ntp-udp":  [("udp", 123, 123)],
    "microsoft-ds": [("tcp", 445, 445)],
    "tcp_135":  [("tcp", 135, 135)],
    "tcp_445":  [("tcp", 445, 445)],
    # ICMP-ish
    "icmp":           [("icmp", None, None)],
    "icmp-comms":     [("icmp", None, None)],
    "echo-request":   [("icmp", None, None)],
    "echo-reply":     [("icmp", None, None)],
    # NetBIOS shorthand sometimes appears as "NBT_"
    "nbt_":      [("udp", 137, 137), ("tcp", 139, 139)],
    # seen on a few sheets
    "syslog":    [("udp", 514, 514), ("tcp", 514, 514)],
    "shell":     [("tcp", 514, 514)],  # historic name for a TCP service
}

# Regex patterns for the common service string formats we encountered
_RE_COLON_PAIR = re.compile(r"(?i)^(tcp|udp)[^0-9]*([0-9]+):([0-9]+)$")              # e.g., UDP/67:68
_RE_PROTO_NUM_RANGE = re.compile(r"(?i)^(tcp|udp)[^0-9]*([0-9]+)[\s_\-–:]+([0-9]+)$") # e.g., tcp_1024-65535
_RE_PROTO_NUM = re.compile(r"(?i)^(tcp|udp)[^0-9]*([0-9]+)$")                          # e.g., tcp_443 or udp53
# Embedded forms like 'VPN_TCP-10000' or 'PIX_8490-tcp'
_RE_EMBEDDED = re.compile(r"(?i)(tcp|udp)[^0-9]*([0-9]+)(?:[\s_\-–:]+([0-9]+))?")

def _add(services: List[Dict[str, Any]], proto: str, lo: Optional[int], hi: Optional[int]):
    """Append or merge a service entry into the list."""
    # Strategy: one dict per protocol; accumulate unique ranges in 'ports'
    proto = proto.lower()
    if proto == "icmp":
        # ICMP: protocol only, no ports
        if not any(s["protocol"] == "icmp" for s in services):
            services.append({"protocol": "icmp", "ports": []})
        return
    if proto == "any":
        # Only set 'any' if nothing else exists; do not overwrite real ports
        if not services:
            services.append({"protocol": "any", "ports": []})
        return
    lo = None if lo is None else int(lo)
    hi = lo if hi is None else int(hi)
    rng = {"from": lo, "to": hi}
    # Merge into an existing protocol bucket if present
    for s in services:
        if s["protocol"] == proto:
            if rng not in s["ports"]:
                s["ports"].append(rng)
            return
    services.append({"protocol": proto, "ports": [rng]})

def _from_alias(tok: str) -> List[Tuple[str, Optional[int], Optional[int]]]:
    # Helper wrapper (easy to swap the alias source later if needed)
    return _ALIAS.get(tok, [])

def _parse_token(tok: str, out: List[Dict[str, Any]]):
    # Parse a single token (e.g., "dns", "tcp_443") and update 'out' via _add
    t = _lower(tok)
    if not t:
        return

    # 1) Direct alias (fast path)
    for proto, lo, hi in _from_alias(t):
        _add(out, proto, lo, hi)
    if _from_alias(t):
        return

    # 2) Colon-separated pair: UDP/67:68 (two singles)
    m = _RE_COLON_PAIR.match(t)
    if m:
        proto, p1, p2 = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        _add(out, proto, p1, p1)
        _add(out, proto, p2, p2)
        return

    # 3) Normalize some separators, then try a port range
    t2 = t.replace("/", "_").replace(":", "-")
    m = _RE_PROTO_NUM_RANGE.match(t2)
    if m:
        proto, lo, hi = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        if lo > hi:
            # If reversed, swap so the data still makes sense
            lo, hi = hi, lo
        _add(out, proto, lo, hi)
        return

    # 4) Single port with protocol (e.g., udp53, tcp_8162)
    m = _RE_PROTO_NUM.match(t2)
    if m:
        proto, p = m.group(1).lower(), int(m.group(2))
        _add(out, proto, p, p)
        return

    # 5) Embedded protocol/ports (e.g., VPN_TCP-10000, PIX_8490-tcp)
    m = _RE_EMBEDDED.search(t)
    if m:
        proto, lo, hi = m.group(1).lower(), int(m.group(2)), m.group(3)
        _add(out, proto, lo, int(hi) if hi else lo)
        return

    # 6) If nothing matched, we leave it. Caller will decide about "any".

def _services_from_field(svc_field: Any) -> List[Dict[str, Any]]:
    # High-level: split the cell → parse tokens → sort ranges for stability
    raw = _clean(str(svc_field))
    tokens = _split_multi(raw)
    services: List[Dict[str, Any]] = []
    for tok in tokens or []:
        _parse_token(tok, services)

    # If we recognized nothing at all, default to 'any'
    if not services:
        return [{"protocol": "any", "ports": []}]

    # Deterministic ordering (useful for tests and diffs)
    for s in services:
        s["ports"] = sorted(s["ports"], key=lambda r: (r["from"], r["to"]))

    # Note: if an alias like 'dns' added both tcp/udp 53, we keep both
    return services

# ---------- public API

def to_v01(flat: Dict[str, Any], vendor_hint: Optional[str] = None, svc_map: Optional[dict] = None) -> Dict[str, Any]:
    """
    Convert a 'flat' row (vendor CSV/XLSX) into FireFind v0.1 normalized object.
    Expected flat keys: vendor, rule_id, src, dst, service, action, reason, severity
    """
    # Gather normalized fields; defaults are intentional ("any", "other", etc.)
    vendor = _norm_vendor(vendor_hint, flat.get("vendor"))
    rule_id = _clean(str(flat.get("rule_id", "")))
    src_addrs = _norm_addrs(flat.get("src"))
    dst_addrs = _norm_addrs(flat.get("dst"))
    services = _services_from_field(flat.get("service"))
    action = _norm_action(flat.get("action"))
    enabled = True  # Until we parse disabled markers from vendor exports

    v01 = {
        "rule_id": rule_id,
        "vendor": vendor,
        "enabled": enabled,
        "action": action,
        "src_addrs": src_addrs,
        "dst_addrs": dst_addrs,
        "services": services,
        "raw": {
            # Keep the original row for traceability and debugging
            "vendor": flat.get("vendor"),
            "rule_id": flat.get("rule_id"),
            "src": flat.get("src"),
            "dst": flat.get("dst"),
            "service": flat.get("service"),
            "action": flat.get("action"),
            "reason": flat.get("reason"),
            "severity": flat.get("severity"),
        },
        "name": None,  # may be filled by vendor-specific logic later
        "comments": (flat.get("reason") or None),  # reuse "reason" as comments for now
    }
    return v01
