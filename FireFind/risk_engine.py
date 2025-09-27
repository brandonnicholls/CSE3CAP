# firefind/risk_engine.py
import json
from typing import Dict, Any, List

def load_risk_rules(config_path: str = "risk_rules.json") -> List[Dict[str, Any]]:
    """Load risk rules from a JSON config file."""
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("rules", [])


def check_rule(rule: Dict[str, Any], ruleset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Check a normalized rule against the ruleset. Return list of findings."""
    findings: List[Dict[str, Any]] = []

    for r in ruleset:
        match = r.get("match", {})

        # --- Check for open admin ports ---
        if "services" in match:
            for svc in rule["services"]:
                for port_range in svc["ports"]:
                    if port_range["from"] in match["services"]:
                        findings.append({
                            "id": r["id"],
                            "severity": r["severity"],
                            "message": f"Rule {rule['rule_id']} allows admin port {port_range['from']} ({svc['protocol']})."
                        })

        # --- Check for ANY to ANY ---
        if match.get("src_any") and match.get("dst_any"):
            if "any" in rule["src_addrs"] and "any" in rule["dst_addrs"]:
                findings.append({
                    "id": r["id"],
                    "severity": r["severity"],
                    "message": f"Rule {rule['rule_id']} allows ANY → ANY traffic."
                })

    return findings
