# FireFind Normalized Schema v0.1

Required fields:
- rule_id: string
- vendor: string (lowercase)
- enabled: boolean
- action: one of {allow, deny, drop, reject, other}
- src_addrs: array of strings (e.g., ["any", "10.0.0.0/24", "HR_Group"])
- dst_addrs: array of strings
- services: array of objects: 
  - { protocol: "tcp"|"udp"|"icmp"|"any", ports: [ {from:int, to:int}, ... ] }
- raw: object (original vendor row)

Optional (nice-to-have):
- name: string|null
- comments: string|null

Normalization rules:
- Lowercase `vendor`, `action`, `protocol`.
- Treat Any/all/0.0.0.0/0/::/0 as "any".
- Single port `22` stored as `{from:22,to:22}`.
- Keep groups/aliases as strings in src/dst; don’t expand in v0.1.