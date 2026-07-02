"""
§Q IDEA 1 — SEMANTIC CACHE-EQUIVALENCE: collapse a whole equivalence-class of differently-spelled requests to ONE I/O.
================================================================================================================
Ordinary caches hit only on EXACT key match. Two requests that are syntactically different but SEMANTICALLY identical
(`x>5 AND x>3` vs `x>5`; `f(a+b)` vs `f(b+a)`) both miss and both hit the backend. We PROVE equivalence with z3 and
share the cache entry, so the second I/O never happens.

★ THE UNIQUE WEAPON IS PROOF, NOT A GUESS. A cache-share is applied ONLY when z3 proves the two requests return the
identical result for ALL inputs (∀x: A(x) ⟺ B(x) for a predicate; ∀x: A(x) == B(x) for a value). z3 unknown/timeout or
a proved difference ⇒ treated as DISTINCT (a separate I/O) — NEVER shared on a guess. A wrong share would serve stale
/ incorrect data = a correctness violation = the build fails. Precision = 1.0 extends to I/O.

★ HONEST FRAMING: physical I/O latency is NOT reduced — we reduce the COUNT of I/Os (one fetch serves the whole proven
equivalence class). The count reduction is exactly measurable on a deterministic modeled request stream; real
wall-clock latency saved is modeled-pending-deployment.
"""
from __future__ import annotations

import ast
from typing import Dict, List, Optional, Tuple

# ── a restricted expr → z3 compiler over declared int/real variables (predicates + arithmetic) ──────────────
_ALLOWED = (ast.Expression, ast.BoolOp, ast.UnaryOp, ast.BinOp, ast.Compare, ast.Name, ast.Load,
            ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Mod, ast.USub,
            ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq, ast.Constant)


def _to_z3(expr: str, env: Dict):
    import z3
    tree = ast.parse(expr.strip(), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise ValueError(f"unsupported construct {type(node).__name__} in request {expr!r}")

    def rec(n):
        if isinstance(n, ast.Expression):
            return rec(n.body)
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if n.id not in env:
                raise ValueError(f"undeclared variable {n.id}")
            return env[n.id]
        if isinstance(n, ast.UnaryOp):
            return z3.Not(rec(n.operand)) if isinstance(n.op, ast.Not) else -rec(n.operand)
        if isinstance(n, ast.BoolOp):
            parts = [rec(v) for v in n.values]
            return z3.And(*parts) if isinstance(n.op, ast.And) else z3.Or(*parts)
        if isinstance(n, ast.BinOp):
            a, b = rec(n.left), rec(n.right)
            return {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b,
                    ast.Mod: lambda: a % b}[type(n.op)]()
        if isinstance(n, ast.Compare):
            a = rec(n.left)
            b = rec(n.comparators[0])
            return {ast.Gt: a > b, ast.GtE: a >= b, ast.Lt: a < b, ast.LtE: a <= b,
                    ast.Eq: a == b, ast.NotEq: a != b}[type(n.ops[0])]
        raise ValueError(f"unsupported node {type(n).__name__}")
    return rec(tree)


def prove_request_equiv(req_a: str, req_b: str, variables: Dict[str, str]) -> Tuple[bool, str]:
    """Prove req_a ≡ req_b for ALL inputs over `variables` ({name: 'Int'|'Real'}). For a predicate, prove A ⟺ B; for
    an arithmetic value, prove A == B. Returns (equivalent, witness/why). z3 unknown / a counterexample ⇒ NOT
    equivalent (treated distinct — never share on a guess)."""
    import z3
    env = {nm: (z3.Int(nm) if t == "Int" else z3.Real(nm)) for nm, t in variables.items()}
    try:
        za, zb = _to_z3(req_a, env), _to_z3(req_b, env)
    except Exception as e:  # noqa: BLE001
        return False, f"cannot encode ({e}) — treated distinct"
    if z3.is_bool(za) != z3.is_bool(zb):
        return False, "one request is a predicate, the other a value — trivially distinct"
    s = z3.Solver()
    s.add(za != zb)
    r = s.check()
    if r == z3.unsat:
        return True, "z3-proved identical for all inputs (∀x equivalence; residual=0)"
    if r == z3.sat:
        return False, f"z3 counterexample {s.model()} — provably DIFFERENT, kept distinct"
    return False, "z3 unknown/timeout — conservatively distinct (never share on a guess)"


class SemanticCache:
    """A cache that, on a miss against exact keys, attempts a BOUNDED z3-equivalence proof against existing keys and
    shares the entry on proof. Every fetch that is served from a proven-equivalent entry is an I/O AVOIDED."""

    def __init__(self, variables: Dict[str, str], max_compare: int = 32):
        self.variables = variables
        self.max_compare = max_compare
        self._keys: List[str] = []          # canonical exact keys held
        self._io_count = 0                  # real backend fetches issued
        self._shared = 0                    # fetches served by a proven-equivalent share

    def fetch(self, request: str) -> str:
        if request in self._keys:
            return "HIT(exact)"
        for k in self._keys[: self.max_compare]:                 # bounded equivalence search (honest cap)
            eq, _why = prove_request_equiv(request, k, self.variables)
            if eq:
                self._shared += 1
                return f"HIT(semantic≡{k})"                       # I/O avoided — proven same result
        self._keys.append(request)
        self._io_count += 1
        return "MISS(backend fetch)"

    def stats(self) -> dict:
        return {"distinct_io": self._io_count, "semantic_shares": self._shared,
                "io_avoided": self._shared, "keys_held": len(self._keys)}


def measure_stream(requests: List[str], variables: Dict[str, str]) -> dict:
    """Run a modeled request stream through the semantic cache; report the I/O-count reduction vs an exact-key cache.
    Count-reduction is exactly measured (deterministic); wall-clock latency saved is modeled-pending-deployment."""
    sem = SemanticCache(variables)
    for r in requests:
        sem.fetch(r)
    s = sem.stats()
    exact_distinct = len(set(requests))                          # an exact-key cache issues one I/O per distinct string
    return {"requests": len(requests), "exact_key_io": exact_distinct, "semantic_io": s["distinct_io"],
            "io_avoided_by_semantic_share": exact_distinct - s["distinct_io"],
            "reduction_fraction": round(1 - s["distinct_io"] / max(1, exact_distinct), 4),
            "note": "COUNT reduction (one fetch serves the proven equivalence class) — physical I/O latency is NOT "
                    "reduced; measured on a deterministic model, real latency saved is modeled-pending-deployment"}
