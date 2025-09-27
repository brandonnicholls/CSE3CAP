# firefind/rules_loader.py
import os
import yaml
from typing import List, Dict, Any

def load_rules(path: str = "rules.yml") -> List[Dict[str, Any]]:
    """
    Load rules.yml into memory.
    Raises errors if the file is missing or invalid.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Rules file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error in {path}: {e}")

    if not config or "rules" not in config:
        raise ValueError(f"Invalid config: expected top-level 'rules' key in {path}")

    rules = config["rules"]
    validate_rules_schema(rules)
    return rules

def validate_rules_schema(rules: List[Dict[str, Any]]) -> None:
    """
    Validate rules.yml structure to make sure it follows the expected format.
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

def hot_reload(path: str, last_mtime: float, cache: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Reload rules.yml if the file has been modified.
    Returns updated rules if changed, otherwise returns the cached rules.
    """
    mtime = os.path.getmtime(path)
    if mtime != last_mtime:
        new_rules = load_rules(path)
        return new_rules
    return cache

if __name__ == "__main__":
    try:
        rules = load_rules("rules.yml")
        print(f"Loaded {len(rules)} rules from rules.yml")
        for r in rules[:3]:  # preview first 3 rules
            print(f"- {r['id']}: {r['name']} ({r['severity']})")
    except Exception as e:
        print(f"Error: {e}")
