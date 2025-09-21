# run_csv_test.py
from firefind.parsers.csv_parser import CsvParser
import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else "sample_vendor_like.csv"
rules = CsvParser().parse(path)

print(f"Parsed {len(rules)} rules from {path}")
for r in rules[:5]:
    # pretty-print a few to sanity check
    print(json.dumps(r, ensure_ascii=False, indent=2))
