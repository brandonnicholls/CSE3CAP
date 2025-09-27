# firefind/uploader.py
import pandas as pd
import os

def upload_rules_file(filepath: str, output_csv: str = "firewall_rules.csv") -> str:
    """
    Upload a firewall rules file (CSV or XLSX) and convert it into a standard CSV.
    
    Args:
        filepath: Path to the uploaded file (.csv or .xlsx).
        output_csv: Name of the standardized CSV file to save.
    
    Returns:
        Path to the saved CSV file.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    elif filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath, engine="openpyxl")
    else:
        raise ValueError("Unsupported file format. Only .csv and .xlsx are supported.")

    # Save standardized CSV (overwrite old one if exists)
    df.to_csv(output_csv, index=False)

    print(f"✅ Uploaded {filepath} → standardized as {output_csv}")
    return output_csv


# Example usage
if __name__ == "__main__":
    # Upload either a CSV or Excel file
    upload_rules_file("my_rules.xlsx")
    # or:
    # upload_rules_file("my_rules.csv")