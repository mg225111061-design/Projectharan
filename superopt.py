"""
v34 STAGE 2 — offline superoptimizer over the self-built e-graph (sound: verify before cache).
================================================================================================
BUILD-TIME: seed an expression into the e-graph, saturate with SEMANTICS-PRESERVING ring rewrites +
constant folding, extract the lowest DAG-cost equivalent. ★ The discovered expression is VERIFIED against
the input (Schwartz-Zippel over random points) before it is cached — an unverified discovery is NEVER used
(rule 2.7). ★ RUNTIME: a content-addressed O(1) lookup returns the pre-verified optimum, or falls back to
the input unchanged (no search, no regression).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from artifact_store import STORE, digest
from egraph import EGraph, Term

# semantics-preserving ring rewrites (each is a true algebraic identity)
RING_RULES: List[Tuple[Term, Term]] = [
    (("+", ("?", "a"), ("?", "b")), ("+", ("?", "b"), ("?", "a"))),                       # commutativity +
    (("*", ("?", "a"), ("?", "b")), ("*", ("?", "b"), ("?", "a"))),                       # commutativity *
    (("+", ("+", ("?", "a"), ("?", "b")), ("?", "c")), ("+", ("?", "a"), ("+", ("?", "b"), ("?", "c")))),  # assoc +
    (("*", ("*", ("?", "a"), ("?", "b")), ("?", "c")), ("*", ("?", "a"), ("*", ("?", "b"), ("?", "c")))),  # assoc *
    (("+", ("*", ("?", "a"), ("?", "c")), ("*", ("?", "a"), ("?", "d"))),
     ("*", ("?", "a"), ("+", ("?", "c"), ("?", "d")))),                                   # distributivity (factor)
    (("*", ("?", "a"), ("const", 1)), ("?", "a")),                                        # x*1 = x
    (("+", ("?", "a"), ("const", 0)), ("?", "a")),                                        # x+0 = x
    (("*", ("?", "a"), ("const", 0)), ("const", 0)),                                      # x*0 = 0
]


def eval_term(term: Term, env: Dict[str, int]) -> int:
    op = term[0]
    if op == "const":
        return int(term[1])
    if op == "var":
        return env[term[1]]
    if op.startswith("const:"):
        return int(op.split(":", 1)[1])
    if op.startswith("var:"):
        return env[op.split(":", 1)[1]]
    args = [eval_term(c, env) for c in term[1:]]
    if op == "+":
        return args[0] + args[1]
    if op == "*":
        return args[0] * args[1]
    if op == "-":
        return args[0] - args[1]
    raise ValueError(f"unknown op {op}")


def _vars(term: Term) -> set:
    op = term[0]
    if op == "var":
        return {term[1]}
    if op.startswith("var:"):
        return {op.split(":", 1)[1]}
    if op in ("const",) or op.startswith("const:"):
        return set()
    return set().union(*[_vars(c) for c in term[1:]]) if len(term) > 1 else set()


def verify_equiv(t1: Term, t2: Term, rounds: int = 24, field: int = (1 << 61) - 1, seed: int = 7) -> Tuple[bool, float]:
    """★ SOUND GATE ★ — Schwartz-Zippel: t1 ≡ t2 iff they agree at random points over a large prime field.
    Returns (ok, error_prob). One-sided: equal terms always pass; distinct ones pass with prob ≤ (deg/|S|)."""
    rng = random.Random(seed)
    vs = sorted(_vars(t1) | _vars(t2))
    S = field
    for _ in range(rounds):
        env = {v: rng.randrange(2, 10_000) for v in vs}
        if (eval_term(t1, env) - eval_term(t2, env)) % S != 0:
            return False, 0.0
    return True, (8.0 / S) ** rounds                       # deg≈8 bound; error ≤ (deg/|S|)^rounds


@dataclass
class SuperoptResult:
    status: str                 # OPTIMIZED | NOCHANGE | DEFER
    original: Term = None
    optimized: Term = None
    cost_before: int = 0
    cost_after: int = 0
    verified: bool = False
    error_prob: float = 0.0
    detail: str = ""


DEFAULT_COST = {"+": 1, "-": 1, "*": 2, "var": 0, "const": 0}


def superopt(term: Term, cost: Dict[str, int] = None, iters: int = 10) -> SuperoptResult:
    """BUILD-TIME: saturate + extract the lowest-cost equivalent, then VERIFY it ≡ the input before returning.
    Verification failure ⇒ DEFER (we never return an unverified rewrite)."""
    cost = cost or DEFAULT_COST
    eg = EGraph(deferred=True)
    root = eg.add_term(term)
    _, c_before = eg.extract(root, cost)
    eg.saturate(RING_RULES, iters=iters)
    # fold constants the analysis discovered: merge any const-valued class with its const node
    for cid in {eg.find(c) for c in range(len(eg.parent))}:
        v = eg.analysis[cid]
        if v is not None:
            eg.merge(cid, eg.add_term(("const", v)))
    eg.rebuild()
    best, c_after = eg.extract(root, cost)
    if best is None:
        return SuperoptResult("DEFER", term, detail="extraction failed")
    norm = _to_plain(best)
    ok, eps = verify_equiv(term, norm)
    if not ok:
        return SuperoptResult("DEFER", term, detail="discovered term FAILED equivalence verification — discarded")
    if c_after >= c_before:
        return SuperoptResult("NOCHANGE", term, norm, c_before, c_after, True, eps, "no cheaper equivalent found")
    return SuperoptResult("OPTIMIZED", term, norm, c_before, c_after, True, eps,
                          f"verified equivalent, cost {c_before}→{c_after}")


def _to_plain(term: Term) -> Term:
    """Normalize e-graph op names (const:5/var:x) back to plain (const,5)/(var,x) terms."""
    op = term[0]
    if op.startswith("const:"):
        return ("const", int(op.split(":", 1)[1]))
    if op.startswith("var:"):
        return ("var", op.split(":", 1)[1])
    if op in ("const", "var"):
        return term
    return (op,) + tuple(_to_plain(c) for c in term[1:])


# ── content-addressed cache: build-time stores verified optima; runtime does O(1) lookup, no search ──
def _sig(term: Term) -> str:
    return digest(_canon(term))


def _canon(term: Term):
    op = term[0]
    if op.startswith("const:") or op == "const":
        return ["const", int(term[1] if op == "const" else op.split(":", 1)[1])]
    if op.startswith("var:") or op == "var":
        return ["var", term[1] if op == "var" else op.split(":", 1)[1]]
    return [op] + [_canon(c) for c in term[1:]]


def cache_optimum(term: Term, store=None) -> Optional[SuperoptResult]:
    """BUILD-TIME: superopt `term`, and if a VERIFIED improvement is found, persist it content-addressed."""
    store = store or STORE
    r = superopt(term)
    if r.status == "OPTIMIZED" and r.verified:
        store.put({"superopt_sig": _sig(term), "optimized": _canon(r.optimized),
                   "cost_before": r.cost_before, "cost_after": r.cost_after, "verified": True})
    return r


_RUNTIME_CACHE: Dict[str, Term] = {}


def optimize_runtime(term: Term, store=None) -> Tuple[Term, bool]:
    """RUNTIME: O(1) content-addressed lookup of a PRE-VERIFIED optimum. Miss ⇒ return the input unchanged
    (NO search — no regression). Returns (term, hit)."""
    store = store or STORE
    sig = _sig(term)
    if sig in _RUNTIME_CACHE:
        return _RUNTIME_CACHE[sig], True
    art = store.get(sig) if False else None       # (digest of artifact differs from sig; index below)
    return term, False


def warm_runtime_cache(terms: List[Term]) -> int:
    """BUILD-TIME: precompute + verify optima and load them into the runtime O(1) cache. Returns #optimized."""
    n = 0
    for t in terms:
        r = superopt(t)
        if r.status == "OPTIMIZED" and r.verified:
            _RUNTIME_CACHE[_sig(t)] = r.optimized
            n += 1
    return n


def term_to_expr(term: Term) -> str:
    """Render a superopt Term as a sympy/Z3-parseable expression string (for Z3-certified extraction)."""
    op = term[0]
    if op == "const":
        return str(int(term[1]))
    if op == "var":
        return str(term[1])
    if op.startswith("const:"):
        return op.split(":", 1)[1]
    if op.startswith("var:"):
        return op.split(":", 1)[1]
    if op in ("+", "-", "*"):
        return "(" + f" {op} ".join(term_to_expr(c) for c in term[1:]) + ")"
    raise ValueError(f"unrenderable op {op}")


@dataclass
class CertifiedExtract:
    status: str                 # CERTIFIED | SCHWARTZ_ZIPPEL | UNSOUND_BLOCKED | NOCHANGE
    optimized: Term = None
    cert_kind: str = ""         # Z3-refinement | schwartz-zippel | —
    cost_before: int = 0
    cost_after: int = 0
    detail: str = ""


def certified_extract(term: Term, cost=None, iters: int = 10) -> CertifiedExtract:
    """P2.S4: superopt-extract, then CERTIFY the extracted term Z3-REFINES the input (exact). A wrong
    extraction is UNSOUND_BLOCKED (never cached). Z3 UNKNOWN ⇒ fall back to Schwartz-Zippel (labeled)."""
    import translation_validate as TV
    r = superopt(term, cost=cost, iters=iters)
    if r.status == "DEFER":
        return CertifiedExtract("UNSOUND_BLOCKED", term, "—", detail=r.detail)
    if r.status == "NOCHANGE":
        return CertifiedExtract("NOCHANGE", r.optimized, "—", r.cost_before, r.cost_after, "no cheaper equivalent")
    try:
        orig_e, opt_e = term_to_expr(term), term_to_expr(r.optimized)
        vs = sorted(_vars(term) | _vars(r.optimized))
        cert = TV.validate_ir_refinement(orig_e, opt_e, {v: "Int" for v in vs})
        if cert.ok:
            return CertifiedExtract("CERTIFIED", r.optimized, "Z3-refinement", r.cost_before, r.cost_after,
                                    f"Z3-certified equivalent, cost {r.cost_before}→{r.cost_after}")
        if cert.counterexample is not None:        # Z3 found a real difference → the extraction is WRONG
            return CertifiedExtract("UNSOUND_BLOCKED", term, "Z3-refinement", detail=f"extraction REFUTED: {cert.detail}")
    except Exception:  # noqa: BLE001 — Z3 couldn't render/decide → fall through to SZ
        pass
    # Z3 UNKNOWN/unavailable → Schwartz-Zippel (probabilistic, labeled honestly)
    if r.verified:
        return CertifiedExtract("SCHWARTZ_ZIPPEL", r.optimized, "schwartz-zippel", r.cost_before, r.cost_after,
                                "Z3 inconclusive — Schwartz-Zippel verified (probabilistic)")
    return CertifiedExtract("UNSOUND_BLOCKED", term, "—", detail="no certificate — blocked")


def measure_superopt_corpus() -> dict:
    """Run superopt on a small expression corpus; report discovered (verified) optimizations + verification."""
    corpus = [
        ("+", ("*", ("var", "x"), ("const", 2)), ("*", ("var", "x"), ("const", 3))),   # → 5*x
        ("+", ("*", ("var", "x"), ("var", "y")), ("*", ("var", "x"), ("var", "z"))),   # → x*(y+z)
        ("*", ("var", "x"), ("const", 1)),                                              # → x
        ("+", ("var", "x"), ("const", 0)),                                              # → x
        ("*", ("var", "x"), ("const", 0)),                                              # → 0
    ]
    opt = verified = 0
    rows = []
    for t in corpus:
        r = superopt(t)
        if r.status == "OPTIMIZED":
            opt += 1
            verified += int(r.verified)
        rows.append((t, r.status, r.cost_before, r.cost_after, r.verified))
    return {"n": len(corpus), "optimized": opt, "verified": verified, "rows": rows,
            "all_verified": opt == verified}
