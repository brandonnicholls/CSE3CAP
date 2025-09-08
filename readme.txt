FireFind – quick usage for devs

1- What to look at:

Only these matter for testing:

firefind/one.py --> CLI entry point.

firefind/v01.py --> v0.1 schema + normalizer.

docs/scehma.md --> our schema

Ignore other code files, they’re just stubs for testing and future features.



2- Installing dependencies:

To be able to use and test those scripts you need to install the libraries and tools from requirements.txt
with the following command:

pip install -r requirements.txt (if you don't have pip, install it or use an alternative)



3- Basic Commands:

Basic commands (Windows paths shown; adjust as needed)

List sheets in a workbook
python -m firefind.one .\sample_data\xlsx-files\outside_fw.xlsx --list-sheets

Auto-detect, preview rows
python -m firefind.one .\sample_data\xlsx-files\inside_fw01_with_risk.xlsx --auto --preview 10

Auto-detect and emit normalized JSON v0.1 to console
python -m firefind.one .\sample_data\xlsx-files\inside_fw01_with_risk.xlsx --auto --json-v01 --preview 5

Write normalized JSONL to a folder (+ short preview)
python -m firefind.one .\sample_data\xlsx-files\inside_fw01_with_risk.xlsx --auto -o .\results --json-v01 --preview 5

Manual sheet selection (when needed)
python -m firefind.one .\sample_data\xlsx-files\outside_fw.xlsx --sheet "Firewall Policy-OUTSIDE-FW" --header-scan 10 --skip-rows 0 --preview 5 --json-v01 -o .\results
