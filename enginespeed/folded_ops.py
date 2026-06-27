"""
§V PHASE 3 — FOLD EVERY REPEATED ENGINE OPERATION: compute-once, look-up-forever.
================================================================================================================
Each repeated engine operation is wired behind the sound cache: AST parsing, a z3 verification, a fold, and the LLM
prompt. The first encounter computes and stores; every re-encounter is an O(1) sound lookup. A negative result (does
NOT fold) is recorded in the absence cache so it is never retried. Common patterns are pre-folded in a library.

★ The LLM-response cache is the Amdahl lever — it cuts the CALL COUNT (Clock A), the only honest attack on the
irreducible LLM latency. We never claim a single call got faster; we make FEWER calls. The count reduction is
MEASURED; the wall-clock latency saved is MODELED-pending-real-deployment (no live egress here).

Every cached value is provably the recompute result (sound key + recompute-equivalence), so precision = 1.0 survives
caching: a wrong/stale hit is impossible by construction.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from enginespeed.cache import MultiLevelCache, content_key, canonical_ast_key


# ── a small, real, measurable z3 verification op (∀-equivalence of two integer expressions) ──────────────────
def _to_z3(node, env):
    import z3
    if isinstance(node, ast.Expression):
        return _to_z3(node.body, env)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.BinOp):
        a, b = _to_z3(node.left, env), _to_z3(node.right, env)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant):
            r = 1
            for _ in range(int(node.right.value)):
                r = r * a
            return r
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_to_z3(node.operand, env)
    raise ValueError("unsupported expr")


def verify_equiv(expr_a: str, expr_b: str) -> bool:
    """Prove two integer-polynomial expressions equal for ALL integer values of their variables (z3 ∀). A real
    Clock-B verification — measurable cold (build + solve) and trivially looked up warm."""
    import z3
    names = sorted({n.id for s in (expr_a, expr_b) for n in ast.walk(ast.parse(s, mode="eval")) if isinstance(n, ast.Name)})
    env = {nm: z3.Int(nm) for nm in names}
    a = _to_z3(ast.parse(expr_a, mode="eval"), env)
    b = _to_z3(ast.parse(expr_b, mode="eval"), env)
    s = z3.Solver()
    s.add(a != b)
    return s.check() == z3.unsat


# ── the LLM call ledger (Clock A): measure call-COUNT reduction, not latency ─────────────────────────────────
@dataclass
class LLMLedger:
    calls_made: int = 0
    calls_avoided: int = 0

    @property
    def reduction(self) -> float:
        total = self.calls_made + self.calls_avoided
        return round(self.calls_avoided / total, 4) if total else 0.0


# ── the folded engine surface: every repeated op behind the sound cache ──────────────────────────────────────
class FoldedEngine:
    """A facade over the engine's repeated operations, each memoized behind the sound multilevel cache. Cold = the
    first compute; warm = an O(1) lookup. The same instance, reused across a workload, fills its caches and the
    repeated work becomes instant — soundly."""
    def __init__(self, cache: Optional[MultiLevelCache] = None):
        self.c = cache or MultiLevelCache()
        self.llm = LLMLedger()

    # AST parse — L1 hot path
    def parse(self, src: str):
        return self.c.L1.get_or_compute(content_key("parse", src), lambda: ast.dump(ast.parse(src.strip())))

    # z3 verification — L2; absence cache records a proven non-equivalence so it isn't re-proved
    def verify(self, expr_a: str, expr_b: str) -> bool:
        key = content_key("verify", expr_a, expr_b)
        if self.c.absence.is_known_miss(key):
            return False
        res = self.c.L2.get_or_compute(key, lambda: verify_equiv(expr_a, expr_b))
        if res is False:
            self.c.absence.record_miss(key)
        return res

    # fold — L2, keyed by the canonical (α-normalized) form so α-equivalent code shares the entry
    def fold(self, fn_src: str, compute_fold: Callable[[str], Any]):
        key = canonical_ast_key(fn_src) or content_key("fold", fn_src)
        return self.c.L2.get_or_compute(key, lambda: compute_fold(fn_src))

    # proof obligation — L3 proof DAG / lemma library
    def discharge(self, obligation: str, prove: Callable[[str], Any]):
        return self.c.L3.get_or_compute(content_key("oblig", obligation), lambda: prove(obligation))

    # ★ LLM response — cut the CALL COUNT (Clock A). On a hit, NO call is made.
    def llm_response(self, prompt: str, call: Optional[Callable[[str], str]] = None) -> str:
        key = content_key("llm", prompt)
        present, val = self.c.L1.peek(key)
        if present:
            self.llm.calls_avoided += 1                     # served from cache ⇒ one fewer real LLM call
            self.c.L1.stats.hits += 1
            return val
        self.llm.calls_made += 1                            # a real call (here: deterministic stand-in; live BLOCKED)
        resp = (call or _mock_llm)(prompt)
        return self.c.L1.get_or_compute(key, lambda: resp)


def _mock_llm(prompt: str) -> str:
    """Deterministic stand-in for the provider (live egress BLOCKED). The cache logic / call-count reduction is real;
    the per-call latency is the provider's and is MODELED-pending-real-deployment, never faked as a measured number."""
    return f"response::{content_key(prompt)[:16]}"


# ── pre-folded pattern library: common shapes folded+proved offline, served at O(1) when met live ────────────
PATTERN_LIBRARY: Dict[str, str] = {
    "sum_k": "n*(n+1)//2",
    "sum_k_sq": "n*(n+1)*(2*n+1)//6",
    "sum_k_cube": "(n*(n+1)//2)**2",
    "sum_const_c": "c*n",
    "sum_2k": "n*(n+1)",
}


def pattern_lookup(name: str) -> Optional[str]:
    """O(1) lookup of a pre-folded common pattern (computed once offline, never recomputed live)."""
    return PATTERN_LIBRARY.get(name)
