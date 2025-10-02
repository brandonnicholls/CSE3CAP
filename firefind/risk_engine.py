# firefind/risk_engine.py
# Risk Engine - applies rules.yml checks (via rules_loader) to normalized firewall rules.
# Output = list of findings (schema defined in docs/schema_findings_v0.1.md)

from typing import List, Dict, Any, Tuple
from firefind.rules_loader import load_rules


def run_engine(normalized_rules: List[Dict[str, Any]], rules_path: str = "docs/rules.yml") -> List[Dict[str, Any]]:
    """
    Run the risk engine:
    - Load compiled checks from rules.yml
    - Loop through normalized rules
    - Apply predicates from the loader
    - Build findings when matches occur
    Returns: list of findings (each dict follows schema_findings_v0.1.md)
    """
    findings: List[Dict[str, Any]] = []

    # 1. Load compiled checks (predicates already built by loader)
    checks = load_rules(rules_path)

    # 2. Loop through every firewall rule (normalized schema v0.1)
    for rule in normalized_rules:
        for chk in checks:
            matched, reason = chk["predicate"](rule)
            if matched:
                findings.append(make_finding(rule, chk, reason))

    return findings


def make_finding(rule: Dict[str, Any], chk: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """
    Build a single finding object based on:
    - Rule (normalized schema v0.1)
    - Check (from rules.yml)
    - Reason (from predicate)
    Output = dict matching docs/schema_findings_v0.1.md
    """
    return {
        "rule_id": rule.get("rule_id", ""),
        "check_id": chk.get("id", ""),
        "severity": chk.get("severity", "low"),
        "title": chk.get("name", chk.get("id", "")),
        "reason": reason or chk.get("rationale", ""),
        "recommendation": chk.get("recommendation", ""),
        "src_addrs": rule.get("src_addrs", []),
        "dst_addrs": rule.get("dst_addrs", []),
        "services": rule.get("services", []),
        "vendor": rule.get("vendor", ""),
        "name": rule.get("name"),
        "comments": rule.get("comments"),
        "evidence": {
            "policy_name": rule.get("raw", {}).get("policy_name", "") if isinstance(rule.get("raw"), dict) else "",
            "hit_count": rule.get("raw", {}).get("hit_count", "") if isinstance(rule.get("raw"), dict) else ""
        },
        "labels": chk.get("labels", [])
    }


if __name__ == "__main__":
    # Small demo runner (for testing)
    sample_rules = [
        {
            "rule_id": "FW-123",
            "vendor": "fortinet",
            "enabled": True,
            "action": "allow",
            "src_addrs": ["any"],
            "dst_addrs": ["10.0.1.0/24"],
            "services": [
                {"protocol": "tcp", "ports": [{"from": 22, "to": 22}]}
            ],
            "raw": {"policy_name": "Edge-1", "hit_count": 412},
            "name": "Allow SSH",
            "comments": "Temporary access"
        }
    ]

    results = run_engine(sample_rules)
    print(f"Generated {len(results)} findings:")
    for f in results:
        print(f"- {f['check_id']} ({f['severity']}): {f['reason']}")
