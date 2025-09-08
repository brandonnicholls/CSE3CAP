import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG  = REPO / 'firefind'

# Names we accept for parser/evaluator (functions or class methods)
PARSER_NAMES = ['parse','parse_file','parse_xlsx','parse_csv','ingest','load','load_rules','read','read_rules','transform','to_schema']
ENGINE_NAMES = ['evaluate','assess','analyze','analyse','score','risk','check','run','run_checks','evaluate_rules']

def iter_py_files(root: Path):
    for p in root.rglob('*.py'):
        if p.name in {'__init__.py','parser.py','risk_engine.py','one.py'}:
            continue
        yield p

def read_ast(p: Path):
    try:
        return ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
    except Exception:
        return None

def score_path(p: Path, kind: str):
    name = str(p).lower()
    score = 0
    if kind == 'parser':
        for k in ['parser','ingest','read','xlsx','csv','palo','pan','checkpoint','forti','rules']:
            if k in name: score += 1
    else:
        for k in ['risk','engine','eval','score','assess','check']:
            if k in name: score += 1
    return score

def find_candidates(kind: str):
    target_names = PARSER_NAMES if kind=='parser' else ENGINE_NAMES
    hits = []
    for py in iter_py_files(PKG):
        tree = read_ast(py)
        if not tree: 
            continue
        # top-level functions
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and n.name in target_names:
                hits.append(('func', py, n.name, None, n.args))
        # class methods
        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                cls = n.name
                for m in n.body:
                    if isinstance(m, ast.FunctionDef) and m.name in target_names:
                        hits.append(('method', py, m.name, cls, m.args))
    # score & choose best
    def arg_score(args):
        # prefer functions/methods with 1 or 2 parameters (path/rules)
        total = len(getattr(args, 'args', []))
        return -abs(total-2)
    best, best_key = None, (-999, )
    for kind_, py, name, cls, args in hits:
        k = (score_path(py, kind), arg_score(args))
        if k > best_key:
            best, best_key = (kind_, py, name, cls), k
    return best  # (kind_, py, name, cls) or None

def dotted_from(py: Path):
    # Always make 'firefind.xxx.yyy' dotted path
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
    return tgt, f"{dotted}:{cls+'.' if cls else ''}{name}"

def write_engine_shim(kind_, py, name, cls):
    dotted = dotted_from(py)
    tgt = PKG / 'risk_engine.py'
    if kind_ == 'func':
        code = f"from {dotted} import {name} as _impl\n\ndef evaluate(rules):\n    return _impl(rules)\n\n__all__ = ['evaluate']\n"
    else:
        code = f"from {dotted} import {cls} as _Cls\n\ndef evaluate(rules):\n    return _Cls().{name}(rules)\n\n__all__ = ['evaluate']\n"
    tgt.write_text(code, encoding='utf-8')
    return tgt, f"{dotted}:{cls+'.' if cls else ''}{name}"

if __name__ == '__main__':
    parser = find_candidates('parser')
    if not parser:
        raise SystemExit("No parser found. Looked for names: " + ', '.join(PARSER_NAMES))
    engine = find_candidates('engine')
    if not engine:
        raise SystemExit("No risk engine found. Looked for names: " + ', '.join(ENGINE_NAMES))

    p_tgt, p_ref = write_parser_shim(*parser)
    e_tgt, e_ref = write_engine_shim(*engine)
    print('[shim] parser  ->', p_ref)
    print('[shim] engine  ->', e_ref)
    print('[shim] wrote   ->', p_tgt)
    print('[shim] wrote   ->', e_tgt)
