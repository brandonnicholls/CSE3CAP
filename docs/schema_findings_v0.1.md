# FireFind Findings Schema v0.1

This schema defines the output of the Risk Engine.  
Normalized firewall rules are evaluated against checks from `rules.yml`.  
Each match produces a **Finding** in this shape.

---

## Required fields
- **rule_id**: string (from normalized rule)
- **check_id**: string (from rules.yml)
- **severity**: one of {low, medium, high, critical}
- **title**: string (human-readable name of the risk)
- **reason**: string (explanation of why the rule matched)
- **recommendation**: string (guidance from rules.yml)
- **src_addrs**: array of strings (from normalized rule)
- **dst_addrs**: array of strings (from normalized rule)
- **services**: array of objects  
  - `{ protocol: "tcp"|"udp"|"icmp"|"any", ports: [ {from:int, to:int}, ... ] }`

## Optional fields
- **vendor**: string (from normalized rule)
- **name**: string|null (vendor rule name)
- **comments**: string|null
- **evidence**: object  
  - `policy_name`: string  
  - `hit_count`: int  
- **labels**: array of strings (from rules.yml)

---

## Example

```json
{
  "rule_id": "FW-123",
  "check_id": "R-INBOUND-ADMIN-OPEN",
  "severity": "critical",
  "title": "Inbound admin ports exposed",
  "reason": "Rule FW-123 allows inbound ANY to 10.0.1.0/24 on tcp/22",
  "recommendation": "Restrict SSH access to a bastion host",
  "src_addrs": ["any"],
  "dst_addrs": ["10.0.1.0/24"],
  "services": [
    { "protocol": "tcp", "ports": [ { "from": 22, "to": 22 } ] }
  ],
  "vendor": "fortinet",
  "name": "Edge SSH",
  "comments": "temporary rule",
  "evidence": {
    "policy_name": "Edge-1",
    "hit_count": 412
  },
  "labels": ["admin","exposure"]
}
