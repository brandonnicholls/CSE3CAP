import ast
from pathlib import Path
pkg_dir = Path(__file__).resolve().parents[1] / "firefind"
repo_dir = pkg_dir.parent
def find_module_with_func(root: Path, func_name: str, prefer_parts=("parsers", "engine", "risk")):
    best = None
    best_score = -1
    for py in root.rglob("*.py"):
        if py.name in {"__init__.py", "one.py", "parser.py", "risk_engine.py"}:
            continue
        try:
            src = py.read_text(encoding="utf-8")
            tree = ast.parse(src, filename=str(py))
        except Exception:
            continue
        has = any(isinstance(n, ast.FunctionDef) and n.name == func_name for n in tree.body)
        if not has:
            continue
        parts = [p.lower() for p in py.parts]
        score = 0
        for p in prefer_parts:
            if p in parts:
                score += 1
        if score > best_score:
            best = py
            best_score = score
    return best

def dotted_from_path(path: Path, base: Path) -> str:
    rel = path.relative_to(base).with_suffix("")
    return ".".join(rel.parts)

parse_mod = find_module_with_func(pkg_dir, "parse", prefer_parts=("parsers","ingest","reader"))
eval_mod  = find_module_with_func(pkg_dir, "evaluate", prefer_parts=("engine","risk"))

if not parse_mod:
    raise SystemExit("Could not find any module in 'firefind/' that defines a top-level function named parse()")
if not eval_mod:
    raise SystemExit("Could not find any module in 'firefind/' that defines a top-level function named evaluate()")

parse_dotted = dotted_from_path(parse_mod, repo_dir)
eval_dotted  = dotted_from_path(eval_mod,  repo_dir)

parser_py = pkg_dir / "parser.py"
risk_py   = pkg_dir / "risk_engine.py"

parser_py.write_text(f"from {parse_dotted} import parse\n__all__ = ['parse']\n", encoding="utf-8")
risk_py.write_text(f"from {eval_dotted} import evaluate\n__all__ = ['evaluate']\n", encoding="utf-8")

print("[shim] parser.py  ->", f"from {parse_dotted} import parse")
print("[shim] risk_engine.py ->", f"from {eval_dotted} import evaluate")
print("[shim] wrote:", parser_py)
print("[shim] wrote:", risk_py)
