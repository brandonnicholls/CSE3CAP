# firefind/rules_loader.py
# This file loads rules.yml, checks that it is valid,
# and turns each YAML rule into a real function (predicate)
# that can be run against firewall rules.

import os
import yaml
import ipaddress
from typing import List, Dict, Any, Tuple, Callable


Check = Dict[str, Any]


#MAIN LOADER

def load_rules(path: str = "rules.yml") -> List[Check]:
    """
    Load rules.yml into memory, validate, normalize, and compile them.
    Returns a list of rules, each with a .predicate(rule) function.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Rules file not found: {path}")

    # open the file and read yaml
    with open(path, "r", encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error in {path}: {e}")

    # check that file actually has "rules" key
    if not config or "rules" not in config:
        raise ValueError(f"Invalid config: expected top-level 'rules' key in {path}")

    rules = config["rules"]

    # load port_groups and cidr_groups (reusable sets in the yaml)
    port_groups = config.get("sets", {}).get("port_groups", {})
    cidr_groups = config.get("sets", {}).get("cidr_groups", {})
    name_groups = config.get("sets", {}).get("addr_names", {})


    # check that each rule has required fields and valid severity
    validate_rules_schema(rules)

    # compile each rule's "when" into a real predicate function
    compiled = []
    for r in rules:
        pred = compile_predicate(r["when"], port_groups, cidr_groups, name_groups, r)
        r["predicate"] = pred  # attach function to rule
        compiled.append(r)

    return compiled


def validate_rules_schema(rules: List[Dict[str, Any]]) -> None:
    """
    to make sure each rule has required fields and correct severity.
    """
    allowed_severity = {"low", "medium", "high", "critical"}
    required_fields = {"id", "name", "severity", "rationale", "when"}

    for idx, r in enumerate(rules, start=1):
        missing = required_fields - r.keys()
        if missing:
            raise ValueError(f"Rule #{idx} missing fields: {', '.join(missing)}")

        if r["severity"] not in allowed_severity:
            raise ValueError(
                f"Rule {r['id']} has invalid severity '{r['severity']}'. "
                f"Allowed: {', '.join(sorted(allowed_severity))}"
            )

        if not isinstance(r["when"], dict):
            raise ValueError(f"Rule {r['id']} has malformed 'when' block (expected dict).")


def hot_reload(path: str, last_mtime: float, cache: List[Check]) -> List[Check]:
    """
    Reload rules.yml if it has been modified.
    If not changed, return the cached rules.
    """
    mtime = os.path.getmtime(path)
    if mtime != last_mtime:
        new_rules = load_rules(path)
        return new_rules
    return cache


#PREDICATE COMPILER

def compile_predicate(
    when: Dict[str, Any],
    port_groups: Dict[str, List[int]],
    cidr_groups: Dict[str, List[str]],
    name_groups: Dict[str, List[str]],   # ← ADD
    rule_meta: Dict[str, Any]
) -> Callable[[Dict[str, Any]], Tuple[bool, str]]:

    """
    Build predicate(rule) for a YAML rule.
    This will run when we test a firewall rule against this check.
    """

    def predicate(rule: Dict[str, Any]) -> Tuple[bool, str]:
        # first, compute extra fields the YAML expects (like src.any, port_span, etc.)
        row = enrich_rule(rule)
        # now test the "when" block against this enriched rule
        return eval_condition(when, row, port_groups, cidr_groups, name_groups, rule_meta)

    return predicate


def eval_condition(
    cond: Dict[str, Any],
    rule: Dict[str, Any],
    port_groups: Dict[str, List[int]],
    cidr_groups: Dict[str, List[str]],
    name_groups: Dict[str, List[str]],
    rule_meta: Dict[str, Any]
) -> Tuple[bool, str]:

    # Always return (bool, str)
    if not isinstance(cond, dict):
        return False, ""

    def _ensure_tuple(res):
        if isinstance(res, tuple) and len(res) == 2 and isinstance(res[0], bool):
            return res
        return False, ""

    # logical blocks
    if "all" in cond:
        subs = cond.get("all") or []
        if not isinstance(subs, list):
            return False, ""
        for sub in subs:
            matched, reason = _ensure_tuple(eval_condition(sub, rule, port_groups, cidr_groups, name_groups, rule_meta))
            if not matched:
                return False, ""
        return True, rule_meta.get("rationale", "")

    if "any" in cond:
        subs = cond.get("any") or []
        if not isinstance(subs, list):
            return False, ""
        for sub in subs:
            matched, reason = _ensure_tuple(eval_condition(sub, rule, port_groups, cidr_groups, name_groups, rule_meta))
            if matched:
                return True, reason
        return False, ""

    #  builtin shortcuts (optional)
    if "builtin" in cond:
        b = cond["builtin"]
        if b == "unknown_service":
            if rule.get("service", {}).get("name") == "unknown":
                return True, rule_meta.get("rationale", "")
            return False, ""
        if b == "reciprocal":
            return False, ""
        return False, ""

    # field ops
    field = cond.get("field")
    op    = cond.get("op")
    value = cond.get("value")

    if field is None or op is None:
        return False, ""

    # resolve set_ref
    if isinstance(value, dict) and "set_ref" in value:
        ref = value["set_ref"]
        if ref.startswith("port_groups."):
            value = port_groups.get(ref.split(".", 1)[1], [])
        elif ref.startswith("cidr_groups."):
            value = cidr_groups.get(ref.split(".", 1)[1], [])
        elif ref.startswith("addr_names."):
            value = name_groups.get(ref.split(".", 1)[1], [])

    field_val = get_field(rule, field)

    # comparisons
    if op == "equals":
        return (field_val == value, rule_meta.get("rationale", ""))
    if op == "is_true":
        return (bool(field_val) is True, rule_meta.get("rationale", ""))
    if op == "is_false":
        return (bool(field_val) is False, rule_meta.get("rationale", ""))
    if op == "contains":
        ok = False
        if isinstance(field_val, list):
            ok = value in field_val
        elif isinstance(field_val, str):
            ok = isinstance(value, str) and value in field_val
        return (ok, rule_meta.get("rationale", ""))
    if op == "overlaps":
        fv = field_val if isinstance(field_val, list) else []
        vv = value if isinstance(value, list) else []
        return (bool(set(fv) & set(vv)), rule_meta.get("rationale", ""))

    # proper numeric range overlap
    if op == "overlaps_range":
        fv = field_val if isinstance(field_val, list) else []
        vv = value if isinstance(value, list) else []
        # list of discrete ports (e.g., admin_ports)
        if vv and not (len(vv) == 2 and all(isinstance(x, int) for x in vv)):
            return (bool(set(fv) & set(vv)), rule_meta.get("rationale", ""))
        # numeric range [lo, hi]
        if len(vv) == 2 and all(isinstance(x, int) for x in vv):
            lo, hi = vv
            if hi < lo: lo, hi = hi, lo
            # service.any overlaps everything
            if get_field(rule, "service.any"):
                return True, rule_meta.get("rationale", "")
            # endpoints check
            for p in fv:
                if isinstance(p, int) and lo <= p <= hi:
                    return True, rule_meta.get("rationale", "")
            return False, ""
        return False, ""

    if op == "gte":
        if field_val is None: return False, ""
        return (field_val >= value, rule_meta.get("rationale", ""))
    if op == "lte":
        if field_val is None: return False, ""
        return (field_val <= value, rule_meta.get("rationale", ""))

    # case-insensitive contains helpers (for DHCP exclusions etc.)
    if op == "ilike_any":
        s = field_val if isinstance(field_val, str) else ""
        terms = value if isinstance(value, list) else [value]
        ok = any(isinstance(t, str) and t.lower() in s.lower() for t in terms)
        return (ok, rule_meta.get("rationale", ""))
    if op == "not_ilike_any":
        s = field_val if isinstance(field_val, str) else ""
        terms = value if isinstance(value, list) else [value]
        ok = all(isinstance(t, str) and t.lower() not in s.lower() for t in terms)
        return (ok, rule_meta.get("rationale", ""))

    # unknown op → clean fail
    return False, ""




def get_field(rule: Dict[str, Any], dotted: str) -> Any:
    """
    Look up a value in the rule using dot notation.
    Example: "service.ports" means rule["service"]["ports"]
    """
    parts = dotted.split(".")
    val: Any = rule
    for p in parts:
        if isinstance(val, dict) and p in val:
            val = val[p]
        else:
            return None
    return val


#ENRICH RULE

def enrich_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    r = dict(rule)
    src_list = r.get("src_addrs") or r.get("src") or []
    dst_list = r.get("dst_addrs") or r.get("dst") or []

    src_info = _compute_addr_info(src_list)
    dst_info = _compute_addr_info(dst_list)

    r["src"] = {"any": src_info["any"], "cidr": src_info["cidrs"], "max_prefix_len": src_info["max_prefix_len"]}
    r["dst"] = {"any": dst_info["any"], "cidr": dst_info["cidrs"], "max_prefix_len": dst_info["max_prefix_len"], "is_private": dst_info["has_private"]}
    r["src_list"] = src_list
    r["dst_list"] = dst_list

    svcs = r.get("services") or []
    has_any = False
    has_icmp = False
    port_count = 0
    span_max = 0
    flat_ports: List[int] = []

    for s in svcs:
        proto = (s.get("protocol") or "").lower()
        if proto == "any":
            has_any = True; continue
        if proto == "icmp":
            has_icmp = True; continue
        if proto in ("tcp","udp"):
            for rng in (s.get("ports") or []):
                try:
                    lo = int(rng.get("from")); hi = int(rng.get("to"))
                except Exception:
                    continue
                if hi < lo: lo, hi = hi, lo
                span = hi - lo
                if span > span_max: span_max = span
                port_count += 1
                if lo == hi:
                    flat_ports.append(lo)
                else:
                    flat_ports.extend([lo, hi])

    if has_any and port_count == 0:
        span_max = 65535

    r["service"] = {
        "any": has_any,
        "port_count": port_count,
        "port_span": span_max,
        "ports": flat_ports,
        "has_icmp": has_icmp,
    }

    r.setdefault("logging", {})
    if "enabled" not in r["logging"]:
        r["logging"]["enabled"] = True
    if "direction" not in r:
        r["direction"] = "any"
    return r





def _compute_addr_info(items: List[str]) -> Dict[str, Any]:
    """
    Compute info from src/dst list.
    - any: True if "any" or 0.0.0.0/0
    - cidrs: valid cidr strings
    - max_prefix_len: smallest prefix length (broadest range)
    - has_private: True if private range found
    """
    any_tokens = {"any", "0.0.0.0/0", "::/0"}
    has_any = any(tok in any_tokens for tok in items)

    cidrs = []
    max_prefix = None
    has_private = False

    for s in items:
        try:
            net = ipaddress.ip_network(s, strict=False)
            cidrs.append(str(net))
            plen = net.prefixlen
            if max_prefix is None or plen < max_prefix:
                max_prefix = plen
            if net.is_private:
                has_private = True
        except Exception:
            continue

    if max_prefix is None:
        max_prefix = 32  # safe default

    return {
        "any": has_any,
        "cidrs": cidrs,
        "max_prefix_len": max_prefix,
        "has_private": has_private
    }


def _normalize_ports(ports: List[Any]) -> List[int]:
    """


    """
    out = []
    for p in ports:
        if isinstance(p, int):
            out.append(p)
        elif isinstance(p, str):
            if "-" in p:
                a, b = p.split("-", 1)
                try:
                    a = int(a); b = int(b)
                    if a <= b:
                        out.extend(range(a, b + 1))
                except:
                    pass
            elif p != "*":
                try:
                    out.append(int(p))
                except:
                    pass
        # ignore "*"
    return out


def _compute_port_span(ports: List[int]) -> int:
    """
    Calculate span of port range.
    If empty, treat as wide open.
    """
    if not ports:
        return 65535
    return max(ports) - min(ports) + 1


#DEBUG

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "docs/rules.yml"
    try:
        rules = load_rules(path)
        print(f"Loaded {len(rules)} compiled rules from {path}")
        # test against a fake firewall rule
        test_rule = {
            "action": "allow",
            "direction": "inbound",
            "src": ["any"],
            "dst": ["any"],
            "service": {"ports": [22]}
        }
        for r in rules[:3]:
            ok, reason = r["predicate"](test_rule)
            print(f"- {r['id']}: predicate → {ok}, reason={reason}")
    except Exception as e:
        print(f"Error: {e}")
