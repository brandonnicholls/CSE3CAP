# firefind/loader.py
import pandas as pd
from typing import List, Dict, Any, Optional
from v01 import to_v01
from risk_engine import check_rule  # risk checking logic

def load_and_check_rules(
    filepath: str, 
    vendor_hint: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Load firewall rules from CSV or Excel, normalize them, and check against risk engine.
    Returns an array of dicts: each rule + its risk findings.
    """
    # Step 1: Read file (CSV or XLSX)
    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    elif filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath, engine="openpyxl")
    else:
        raise ValueError("Unsupported file format. Use .csv or .xlsx")

    rules: List[Dict[str, Any]] = []

    # Step 2: Iterate rows and normalize + check
    for _, row in df.iterrows():
        flat_row = row.to_dict()

        # Normalize
        normalized = to_v01(flat_row, vendor_hint=vendor_hint)

        # Check against rule engine
        findings = check_rule(normalized)

        # Store results
        rules.append({
            "rule": normalized,
            "findings": findings
        })

    return rules


# Example usage
if __name__ == "__main__":
    filepath = "firewall_rules.xlsx"  # change to .csv if needed
    all_rules = load_and_check_rules(filepath, vendor_hint="cisco")

    print(f"Checked {len(all_rules)} rules")
    for entry in all_rules[:5]:  # show first 5
        print("Rule ID:", entry["rule"]["rule_id"])
        print("Findings:", entry["findings"])
        print("---")
