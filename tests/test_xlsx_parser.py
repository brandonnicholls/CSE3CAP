# tests/test_xlsx_parser.py
import pathlib
import pytest
from firefind.parsers.xlsx_parser import XlsxParser

DATA_DIR = pathlib.Path(__file__).parent.parent / "sample_data" / "xlsx-files"
parser = XlsxParser()

@pytest.mark.parametrize("xlsx_file", DATA_DIR.glob("*.xlsx"))
def test_parse_all_xlsx_files(xlsx_file):
    rules = list(parser.parse(str(xlsx_file)))
    assert len(rules) > 0, f"{xlsx_file} produced no rules"
    for r in rules:
        # minimal schema validation
        assert "rule_id" in r and r["rule_id"]
        assert "vendor" in r
        assert "action" in r
        assert isinstance(r["src_addrs"], list)
        assert isinstance(r["dst_addrs"], list)
        assert isinstance(r["services"], list)
        assert isinstance(r["raw"], dict)
