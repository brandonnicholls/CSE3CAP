# tests/conftest.py
import sys, pathlib
# add project root (FireFind/) to sys.path so "firefind" can be imported
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
