# tests/run_engine_cli.py
# Run the Risk Engine on REAL normalized outputs in results/.
# usage examples can be single or multiple files ex below:::
#   python -m tests.run_engine_cli results/normalized.jsonl
#   python -m tests.run_engine_cli results/normalized/   (folder with many files)

import sys, json, pathlib
from typing import List, Dict, Any
from firefind.risk_engine import run_engine

def read_normalized(path_str: str) -> List[Dict[str, Any]]:
    """
    Load normalized rules v0.1 from a file or folder.
    Supports:
      - JSONL (one JSON object per line)  -> *.jsonl
      - JSON  (array of objects)          -> *.json
    """
    path = pathlib.Path(path_str)
    rows: List[Dict[str, Any]] = []

    def _load_file(p: pathlib.Path):
        if p.suffix.lower() == ".jsonl":
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        elif p.suffix.lower() == ".json":
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                rows.extend(data)
            else:
                print(f"[WARN] {p} is JSON but not a list; skipping")
        else:
            print(f"[SKIP] {p} (not .json or .jsonl)")

    if path.is_file():
        _load_file(path)
    elif path.is_dir():
        for p in sorted(path.glob("**/*")):
            if p.is_file() and p.suffix.lower() in (".jsonl", ".json"):
                _load_file(p)
    else:
        raise FileNotFoundError(f"Path not found: {path}")

    return rows

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m tests.run_engine_cli <file_or_folder> [rules.yml]")
        print("Example: python -m tests.run_engine_cli results/normalized.jsonl docs/rules.yml")
        sys.exit(1)

    src_path = sys.argv[1]
    rules_path = sys.argv[2] if len(sys.argv) > 2 else "docs/rules.yml"

    # 1) read real normalized rules from disk
    normalized = read_normalized(src_path)
    print(f"Loaded {len(normalized)} normalized rules from {src_path}")

    # 2) run the engine (uses rules_loader inside)
    findings = run_engine(normalized, rules_path=rules_path)
    print(f"Engine produced {len(findings)} findings\n")

    # 3) quick human summary
    by_check = {}
    by_sev = {}
    for f in findings:
        by_check[f["check_id"]] = by_check.get(f["check_id"], 0) + 1
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1

    if by_sev:
        print("By severity:", ", ".join(f"{k}:{v}" for k,v in sorted(by_sev.items(), key=lambda x: -x[1])))
    if by_check:
        top = sorted(by_check.items(), key=lambda x: -x[1])[:10]
        print("Top checks:", ", ".join(f"{k}={v}" for k,v in top))

    # 4) print first few findings so we see schema
    for f in findings[:5]:
        print(f"- {f['rule_id']} -> {f['check_id']} ({f['severity']}): {f['reason']}")

    from pprint import pprint
    pprint(findings[:5])


if __name__ == "__main__":
    main()
