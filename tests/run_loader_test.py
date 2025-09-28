# tests/run_loader_test.py
import json

from firefind.rules_loader import load_rules

# load compiled rules
rules = load_rules("docs/rules.yml")

# fake firewall rule to test
test_rule = {
    "vendor": "fortinet",
    "rule_id": "FW-123",
    "action": "allow",
    "direction": "inbound",
    "src": ["any"],
    "dst": ["10.0.1.0/24"],
    "service": {
        "proto": "tcp",
        "ports": [22, 443]
    },
    "meta": {
        "policy_name": "Edge-1",
        "hit_count": 412
    }
}

# run the test rule through each compiled predicate
print(f"Testing rule {test_rule['rule_id']} ...\n")
for r in rules:
    matched, reason = r["predicate"](test_rule)
    if matched:
        print(f"[MATCH] {r['id']} ({r['severity']}) → {reason}")
    else:
        print(f"[OK]    {r['id']} did not match")
