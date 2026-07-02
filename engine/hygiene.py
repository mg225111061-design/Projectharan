"""
§3 ENGINE — LOOP D (cycle 5): HYGIENE self-audit of the engine/ package (drift guard, codified).
================================================================================================================
The autonomous engine writes its own modules (loop_a, loop_b, red_team, this file). This gate audits the engine/
package against the HONESTY-SPINE invariants so future cycles cannot silently drift:
  H1 zero-dep     — no BLACKLISTED external heavy dep (pyzx/cadabra/torch/tensorflow/jax/scipy/pandas/sklearn/...);
                    only z3 + stdlib + numpy + grandfathered sympy + repo-internal modules.
  H2 no banned bigram — the permanently-banned phrase ("quantum"+" "+"speedup") never appears contiguously in source.
  H3 no agent-id leak — the running model identifier never appears in engine/ source (it belongs in chat only; NOTE:
                    the PRODUCT's own backend-model config elsewhere in the repo is legitimate and out of scope — this
                    gate audits ONLY the engine/ package the autonomous loop authors).
  H4 no float-EXACT — engine/ does exact arithmetic over Fraction/int; no module computes an EXACT verdict from a
                    Python float (the float→DECLINE discipline of §1-Q3 / free_fermion._exact).
★ A NEGATIVE CONTROL proves each detector actually fires (a synthetic bad source must be flagged) — a green audit that
can't detect a violation is worthless.
"""
from __future__ import annotations

import ast
import glob
import os
from typing import Dict, List

# external heavy deps the zero-dep oath forbids (z3/numpy/grandfathered-sympy are NOT here — they are permitted)
_BLACKLIST = {"pyzx", "cadabra", "cadabra2", "torch", "tensorflow", "jax", "scipy", "pandas", "sklearn",
              "scikit", "networkx", "cvxpy", "galois", "sage", "pari", "flint", "gmpy2"}
# the banned bigram, assembled by concatenation so the literal never appears contiguously in THIS file either
_BANNED_BIGRAM = "quantum" + " " + "speedup"
# the running model identifier, assembled by parts so this guard file does not itself contain the literal
_MODEL_ID = "claude" + "-opus-" + "4-8"


def _engine_files() -> List[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    return sorted(f for f in glob.glob(os.path.join(here, "*.py")))


def _imports_of(src: str) -> List[str]:
    """Top-level module roots imported by the source (ast-based, robust). Includes nested/in-function imports."""
    roots = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                roots.add(node.module.split(".")[0])
    return sorted(roots)


def audit() -> Dict:
    """Audit every engine/*.py against H1–H4. Returns per-file violations + an overall clean flag."""
    files = _engine_files()
    violations = {"H1_blacklisted_import": [], "H2_banned_bigram": [], "H3_model_id_leak": [], "H4_float_exact": []}
    for path in files:
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        name = os.path.basename(path)
        for root in _imports_of(src):
            if root in _BLACKLIST:
                violations["H1_blacklisted_import"].append(f"{name}: imports {root}")
        if _BANNED_BIGRAM in src:
            violations["H2_banned_bigram"].append(name)
        if _MODEL_ID in src:
            violations["H3_model_id_leak"].append(name)
        # H4 heuristic: a float literal flowing into a verdict constructor on the same logical line. The engine modules
        # use Fraction/int for all values; floats appear only in reported RATES (0.0/0.33) and docstrings. Flag any
        # `KV.exact(` call that also contains a bare float literal token on its line (none expected).
        for ln in src.splitlines():
            s = ln.strip()
            if s.startswith("#") or s.startswith('"') or s.startswith("'"):
                continue
            if "exact(" in s and any(tok in s for tok in (".0", ".5", "float(")) and "Fraction" not in s:
                violations["H4_float_exact"].append(f"{name}: {s[:60]}")
    clean = all(len(v) == 0 for v in violations.values())
    return {"files_audited": [os.path.basename(f) for f in files], "violations": violations, "clean": clean}


def _detect_on(src: str) -> Dict:
    """Run the four detectors on an arbitrary source string (for the negative control)."""
    roots = _imports_of(src)
    return {"H1": any(r in _BLACKLIST for r in roots), "H2": _BANNED_BIGRAM in src,
            "H3": _MODEL_ID in src,
            "H4": any(("exact(" in l and any(t in l for t in (".0", ".5", "float(")) and "Fraction" not in l)
                      for l in src.splitlines())}


def adversarial_battery() -> Dict:
    """★ the engine/ package is CLEAN on H1–H4 (zero-dep / no banned bigram / no agent-id leak / no float-EXACT); ★★ a
    NEGATIVE CONTROL proves every detector fires — a synthetic source that imports a blacklisted dep, uses the banned
    bigram, leaks the model id, and computes a float EXACT is flagged on all four axes (a detector that cannot detect
    is worthless)."""
    a = audit()
    bad = ("import torch\n"
           "# this claims a " + "quantum" + " " + "speedup" + " and leaks " + "claude" + "-opus-" + "4-8" + "\n"
           "def f():\n    return KV.exact(0.5, 'x', 'y', None)\n")
    det = _detect_on(bad)
    cases = {
        "engine_package_clean": a["clean"],
        "neg_control_H1_import": det["H1"],
        "neg_control_H2_bigram": det["H2"],
        "neg_control_H3_modelid": det["H3"],
        "neg_control_H4_floatexact": det["H4"],
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v],
            "audit": a}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2, default=str))
