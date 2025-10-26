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

#  helpers

def _clean(s: str) -> str:
    # Trim spaces and tolerate None
    return (s or "").strip()

def _lower(s: str) -> str:
    # Lowercased version for easier matching/comparisons
    return _clean(s).lower()

def _split_multi(s: str) -> List[str]:
    if not s:
        return []
    parts = re.split(r"[\n;,]+", str(s))  # ← NO spaces here
    return [p.strip() for p in parts if p and p.strip()]



def _strip_group_prefix(s: str) -> str:
    # Example: "Group Member (2): 10.1.1.0/24" → "10.1.1.0/24"
    return re.sub(r"^Group Member\s*\(\d+\):\s*", "", s, flags=re.IGNORECASE)

def _strip_label_prefixes(s: str) -> str:
    # Example: "FQDN: example.com" or "IP/Netmask: 10.0.0.0/8" → keep just the value
    return re.sub(r"^(FQDN:|IP/Netmask:\s*)", "", s, flags=re.IGNORECASE)

def _norm_addrs(field: Any) -> List[str]:
    s = _clean(str(field))
    if not s:
        return ["any"]

    s = re.sub(r"\s+address\s+", "\n", s, flags=re.IGNORECASE)
    s = _strip_group_prefix(s)
    items = _split_multi(s)
    items = [_strip_label_prefixes(x) for x in items]
    items = [ "any" if _lower(x) == "all" else x for x in items ]
    items = [ x for x in items if _lower(x) != "address" ]

    def maybe_split_obj_like(token: str) -> List[str]:
        token = token.strip()
        if " " not in token:
            return [token]

        parts = token.split()

        # NEW: if the *first* part is object-like (has '_' or '-'),
        # split into [first_part, rest_preserved]
        if ("_" in parts[0]) or ("-" in parts[0]):
            rest = " ".join(parts[1:]).strip()
            return [parts[0]] + ([rest] if rest else [])

        # Existing conservative split: only split when *all* parts look object-like
        if all(("_" in p) or ("-" in p) for p in parts):
            return parts

        return [token]

    exploded = []
    for it in items:
        exploded.extend(maybe_split_obj_like(it))

    return exploded or ["any"]







# action/vendor normalization

# Collapse vendor action verbs into a compact set we use everywhere
_ACTION_MAP = {
    # allow-equivalent
    "accept": "allow",
    "allow": "allow",
    "permit": "allow",
    "enable": "allow",
    "enabled": "allow",
    "https": "allow",
    "http": "allow",
    "ssh": "allow",
    "rdp": "allow",
    "any": "allow",

    # deny-equivalent
    "drop": "drop",
    "deny": "deny",
    "blocked": "deny",
    "reject": "deny",

    # fallback stays "other"
}


def _norm_action(a: Any) -> str:
    # Unrecognized actions become "other" so they’re visible in QA later
    a = _lower(str(a))
    return _ACTION_MAP.get(a, "other")

def _norm_vendor(vendor_hint: Optional[str], flat_vendor: Any) -> str:
    # Prefer the row’s vendor; if absent, try the hint; otherwise "unknown"
    v = (_lower(flat_vendor) or _lower(vendor_hint) or "unknown")
    return v

#  service parsing

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

    # name bundles
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
    "ping":           [("icmp", None, None)],

    # NetBIOS shorthand sometimes appears as "NBT_"
    "nbt_":      [("udp", 137, 137), ("tcp", 139, 139)],

    # seen on a few sheets
    "syslog":    [("udp", 514, 514), ("tcp", 514, 514)],
    "shell":     [("tcp", 514, 514)],  # historic name for a TCP service

    # vendor UI strings we observed
    "microsoft remote desktop [rdp]": [("tcp", 3389, 3389)],
    "microsoft terminal services [rdp]": [("tcp", 3389, 3389)],
    "microsoft terminal services [udp]": [("udp", 3389, 3389)],
    "grp_terminal_services": [("tcp", 3389, 3389), ("udp", 3389, 3389)],
    "grp_netbios": [
        ("udp", 137, 137), ("udp", 138, 138),
        ("tcp", 139, 139), ("tcp", 445, 445)
    ],
    "grp_ad_connectivity": [
        ("tcp", 88, 88), ("udp", 88, 88),
        ("tcp", 389, 389), ("tcp", 636, 636),
        ("tcp", 445, 445), ("udp", 123, 123)
    ],
    "windows ad": [
        ("tcp", 389, 389), ("tcp", 445, 445),
        ("tcp", 88, 88),  ("udp", 88, 88)
    ],
    "grp_http": [("tcp", 80, 80), ("tcp", 443, 443)],
    r"grp_http\\s": [("tcp", 80, 80), ("tcp", 443, 443)],

    # citrix / workspace
    "citrix ica": [("tcp", 1494, 1494)],
    "tcp_1494": [("tcp", 1494, 1494)],
    "tcp_2598": [("tcp", 2598, 2598)],
    "udp_2598": [("udp", 2598, 2598)],
    "udp_16500-16509": [("udp", 16500, 16509)],

    # monitoring / mgmt bits we saw
    "snmp": [("udp", 161, 161)],
    "snmp-traps": [("udp", 162, 162)],
    "tcp_541": [("tcp", 541, 541)],

    # ldap variants
    "ldap": [("tcp", 389, 389)],
    "ldap_ssl": [("tcp", 636, 636)],
    "ldap-ssl": [("tcp", 636, 636)],
    "ldap_udp": [("udp", 389, 389)],

    # misc one-offs in the data
    "tcp_4505-4506": [("tcp", 4505, 4506)],
    "udp_6559": [("udp", 6559, 6559)],
    "tcp_3007-3008": [("tcp", 3007, 3008)],
    "tcp_8006-8007": [("tcp", 8006, 8007)],
    "tcp_30175": [("tcp", 30175, 30175)],
    "tcp_8530": [("tcp", 8530, 8530)],
    "tcp_8531": [("tcp", 8531, 8531)],
    "tcp_54443": [("tcp", 54443, 54443)],   # added
    "tcp_10004": [("tcp", 10004, 10004)],
    "tcp_15000": [("tcp", 15000, 15000)],
    "grp_sccm-server-ports": [("tcp", 8530, 8530), ("tcp", 8531, 8531)],
    "tcp_5556": [("tcp", 5556, 5556)],
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
    # Parse a single token (etc "dns", "tcp_443") and update 'out' via _add
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

    # 4) Single port with protocol ( udp53, tcp_8162)
    m = _RE_PROTO_NUM.match(t2)
    if m:
        proto, p = m.group(1).lower(), int(m.group(2))
        _add(out, proto, p, p)
        return

    # 5) Embedded protocol/ports ( VPN_TCP-10000, PIX_8490-tcp)
    m = _RE_EMBEDDED.search(t)
    if m:
        proto, lo, hi = m.group(1).lower(), int(m.group(2)), m.group(3)
        _add(out, proto, lo, int(hi) if hi else lo)
        return

    # 6) If nothing matched, we leave it. Caller will decide about "any".

def _services_from_field(svc_field: Any) -> List[Dict[str, Any]]:
    raw = _clean(str(svc_field))
    # Convert alpha/alpha slashes to commas so "HTTP/HTTPS" -> "HTTP,HTTPS"
    raw = re.sub(r'(?i)\b([a-z][a-z0-9_\-+]*)\s*/\s*([a-z][a-z0-9_\-+]*)\b', r'\1,\2', raw)

    tokens = _split_multi(raw)

    if len(tokens) <= 1 and (" " in raw):
        tokens = [t for t in raw.split() if t.strip()]

    services: List[Dict[str, Any]] = []
    for tok in tokens or []:
        _parse_token(tok, services)

    if not services:
        return [{"protocol": "any", "ports": []}]

    for s in services:
        s["ports"] = sorted(s["ports"], key=lambda r: (r["from"], r["to"]))
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
           # "severity": flat.get("severity"),
        },


        "name": None,  # may be filled by vendor-specific logic later
        "comments": (flat.get("reason") or None),  # reuse "reason" as comments for now
    }
    return v01
