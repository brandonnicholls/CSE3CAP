# firefind/cli.py
import argparse, sys, csv
from pathlib import Path
from firefind import parser, risk_engine  # adjust imports to your modules

def write_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["vendor", "rule_id", "src", "dst", "service", "action", "reason", "severity"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def main():
    ap = argparse.ArgumentParser(description="FireFind CLI")
    ap.add_argument("-i", "--input", required=True, help="File or directory of CSV/XLSX exports")
    ap.add_argument("-o", "--out", default="results", help="Directory to write outputs (default: results)")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)  # <-- guarantee it exists

    # Collect files
    files = []
    if in_path.is_file():
        files = [in_path]
    elif in_path.is_dir():
        files = list(in_path.glob("*.csv")) + list(in_path.glob("*.xlsx"))
    if not files:
        print(f"No input files found in {in_path}", file=sys.stderr)
        sys.exit(2)

    all_rows = []
    for f in files:
        rules = list(parser.parse(str(f)))            # your existing parser
        findings = list(risk_engine.evaluate(rules))  # your risk checks
        write_csv(findings, out_dir / f"{f.stem}.findings.csv")
        for row in findings:
            row = dict(row)
            row["source_file"] = f.name
            all_rows.append(row)

    # optional: a simple run summary
    if all_rows:
        write_csv(all_rows, out_dir / "summary.findings.csv")

    print(f"✓ Wrote {len(files)} file(s) into {out_dir.resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
