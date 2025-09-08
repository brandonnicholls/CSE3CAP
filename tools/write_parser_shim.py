import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG  = REPO / 'firefind'

# Names we consider 'parser-like' (function or class method)
CANDIDATE_NAMES = ['parse','parse_file','parse_xlsx','parse_csv','ingest','load','read','read_rules','to_schema','transform']

def score_path(p: Path):
    name = str(p).lower()
    score = 0
    for k in ['parser','xlsx','excel','pan','palo','forti','checkpoint','rules','ingest','read']:
        if k in name: score += 1
    return score

def find_parser():
    best = None
    best_key = (-999,)
    for py in (PKG).rglob('*.py'):
        if py.name in {'__init__.py','parser.py','risk_engine.py','one.py'}:
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except Exception:
            continue
        # top-level functions
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and n.name in CANDIDATE_NAMES:
                k = (score_path(py), 0)  # prefer good file names
                if k > best_key:
                    best = ('func', py, n.name, None)
                    best_key = k
        # class methods
        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                for m in n.body:
                    if isinstance(m, ast.FunctionDef) and m.name in CANDIDATE_NAMES:
                        k = (score_path(py), 1)
                        if k > best_key:
                            best = ('method', py, m.name, n.name)
                            best_key = k
    return best

def dotted_from(py: Path) -> str:
    rel = py.relative_to(REPO).with_suffix('')
    return '.'.join(rel.parts)

def write_parser_shim(kind_, py, name, cls):
    dotted = dotted_from(py)
    tgt = PKG / 'parser.py'
    if kind_ == 'func':
        code = f"from {dotted} import {name} as _impl\n\ndef parse(path):\n    return _impl(path)\n\n__all__ = ['parse']\n"
    else:
        code = f"from {dotted} import {cls} as _Cls\n\ndef parse(path):\n    return _Cls().{name}(path)\n\n__all__ = ['parse']\n"
    tgt.write_text(code, encoding='utf-8')
    print('[shim] parser ->', f"{dotted}:{cls+'.' if cls else ''}{name}")
    print('[shim] wrote  ->', tgt)

if __name__ == '__main__':
    cand = find_parser()
    if not cand:
        raise SystemExit("No parser-like function/method found under firefind/. Looked for: " + ', '.join(CANDIDATE_NAMES))
    write_parser_shim(*cand)
