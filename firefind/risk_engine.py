from typing import Iterable, Dict, Any
def evaluate(rules: Iterable[Dict[str, Any]]):
    for r in rules:
        d = dict(r)
        yield {
            'vendor':   d.get('vendor') or d.get('source_vendor') or 'unknown',
            'rule_id':  d.get('rule_id') or d.get('id') or d.get('name') or '',
            'src':      d.get('src') or d.get('source') or d.get('src_ip') or '',
            'dst':      d.get('dst') or d.get('destination') or d.get('dst_ip') or '',
            'service':  d.get('service') or d.get('app') or d.get('protocol') or '',
            'action':   d.get('action') or d.get('decision') or '',
            'reason':   d.get('reason') or '',
            'severity': d.get('severity') or 'info',
        }
