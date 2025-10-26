# firefind/csv_robust.py
from __future__ import annotations
import csv, io, re
from pathlib import Path
from typing import List
import pandas as pd

# line + cell fixers

def _fix_line_shape(s: str) -> str:
    """
    Normalize a CSV line which might be wrapped in one outer quote and padded
    with trailing commas, e.g.:
      "num,name,source,...,comments",,,,,,
    """
    s = (s or "").strip()
    if not s:
        return ""
    s = re.sub(r'(,)+\s*$', '', s)  # drop any number of trailing commas
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]                  # strip a single outer quote pair
    return s

def _strip_outer_quotes(x: str) -> str:
    # remove *balanced* outer quotes repeatedly:  "foo" -> foo, ""bar"" -> bar
    x = x.strip()
    while len(x) >= 2 and x[0] == '"' and x[-1] == '"':
        x = x[1:-1].strip()
    return x

def _fix_cell(x: str) -> str:
    """
    Collapse doubled quotes and remove stray trailing quotes that remained from
    odd exports (e.g., Internal_Net"" -> Internal_Net).
    """
    x = (x or "").replace('""', '"').strip()
    x = _strip_outer_quotes(x)
    # if anything still ends with an orphan quote, drop it
    if x.endswith('"') and not x.startswith('"'):
        x = x[:-1].strip()
    return x

#  public helpers

def read_csv_loose_as_df(path: Path) -> pd.DataFrame:
    """
    Read a problematic CSV (outer quotes + trailing commas per line) into a
    DataFrame of *raw rows* (no header yet). Header detection in one.py will
    run unchanged on this DataFrame.
    """
    text_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    cleaned: List[str] = []
    for line in text_lines:
        fixed = _fix_line_shape(line)
        if fixed:
            cleaned.append(fixed)

    rows = [[_fix_cell(c) for c in row]
            for row in csv.reader(io.StringIO("\n".join(cleaned)))]

    if not rows:
        return pd.DataFrame()

    # Return as raw rows (header=first row, but we don't assign yet)
    return pd.DataFrame(rows)

def rebuild_with_header(df_all: pd.DataFrame, header_row_index: int) -> pd.DataFrame:
    """
    Given a raw-rows DataFrame, build a proper DataFrame using the detected
    header row. This also runs cell cleanup already applied in read_csv_loose_as_df.
    """
    header_vals = [str(x) for x in df_all.iloc[header_row_index].tolist()]
    df = df_all.iloc[header_row_index + 1 :].reset_index(drop=True)
    df.columns = header_vals
    return df
