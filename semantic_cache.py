"""
perf-build STAGE 2 — E-GRAPH SEMANTIC proof cache (Clock B: verification throughput, NOT Clock A latency).
============================================================================================================
The structural proof_cache (α-rename + sorted assumptions) MISSES surface refactorings that change tree shape:
associativity ((a+b)+c vs a+(b+c)), distributivity (a*(b+c) vs a*b+a*c), constant folding (x+0 vs x), and
opaque-subterm reshuffles. This layer keys the verdict on a SEMANTIC normal form so those all hit one entry.

★ MECHANISM (§2.1) — reuses the existing e-graph (egraph.py), no new engine ★
  arithmetic subterm → α-rename vars → e-graph saturate (commute/assoc/DISTRIBUTIVITY) + constant-fold →
  lowest-cost extraction → a deterministic normal form (flatten +/*, sort commutative operands, fold consts,
  a−b ≡ a+(−1)·b) → canonical string. Opaque subterms (calls, floats) are atoms (free unknowns). Comparisons
  are direction-normalized (< ↦ >, ≤ ↦ ≥ by swapping; ==/!= operands sorted).

★ SOUNDNESS (§5, §1.8) ★ every rewrite/normalization step is equivalence-preserving and α-rename is sound for
  a universally-closed goal, so two goals with the same semantic key DENOTE THE SAME ∀-statement ⇒ they share
  the verdict. We also AUDIT it: measure_semantic_cache re-solves every hit fresh and asserts the verdict
  matches (lossless). A wrong key (dogfood) is REJECTED.

★ ENTAILMENT (§2.2) ★ inequality implication (x>5 ⟹ x>0) is decided by INTERVAL-domain subsumption (O(1) ⊆),
  NOT by equality saturation (using an e-graph for implication would be unsound). General entailment stays a
  solver query.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import haran_ast as A
import z3_adapter as Z
from egraph import EGraph

# ── e-graph rewrites: commutativity / associativity (both directions) / distributivity (both directions) ──
_RULES: List[Tuple[tuple, tuple]] = [
    (("+", ("?", "a"), ("?", "b")), ("+", ("?", "b"), ("?", "a"))),
    (("*", ("?", "a"), ("?", "b")), ("*", ("?", "b"), ("?", "a"))),
    (("+", ("+", ("?", "a"), ("?", "b")), ("?", "c")), ("+", ("?", "a"), ("+", ("?", "b"), ("?", "c")))),
    (("+", ("?", "a"), ("+", ("?", "b"), ("?", "c"))), ("+", ("+", ("?", "a"), ("?", "b")), ("?", "c"))),
    (("*", ("*", ("?", "a"), ("?", "b")), ("?", "c")), ("*", ("?", "a"), ("*", ("?", "b"), ("?", "c")))),
    (("*", ("?", "a"), ("*", ("?", "b"), ("?", "c"))), ("*", ("*", ("?", "a"), ("?", "b")), ("?", "c"))),
    (("*", ("?", "a"), ("+", ("?", "b"), ("?", "c"))),
     ("+", ("*", ("?", "a"), ("?", "b")), ("*", ("?", "a"), ("?", "c")))),
    (("+", ("*", ("?", "a"), ("?", "b")), ("*", ("?", "a"), ("?", "c"))),
     ("*", ("?", "a"), ("+", ("?", "b"), ("?", "c")))),
]
_COST = {"+": 1, "-": 1, "*": 1, "var": 0, "const": 0}
_FLIP = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}     # for direction normalization
_SYMM = {"==", "!=", "eq", "neq"}


# ─────────────────────────────────────────────── HARAN expr → canonical tuple (ORIGINAL names; rename last)
def _to_tuple(e) -> tuple:
    """Structural tuple of any (sub)expression, KEEPING original variable names (the canonical α-rename is a
    single global pass done at the very end, on the already-normalized form)."""
    if isinstance(e, A.Num):
        return ("fconst", repr(e.value)) if e.is_float else ("const", int(e.value))
    if isinstance(e, A.BoolLit):
        return ("bool", bool(e.value))
    if isinstance(e, A.Var):
        return ("var", e.name)
    if isinstance(e, A.Un):
        return ("un", e.op, _to_tuple(e.operand))
    if isinstance(e, A.Bin):
        return ("bin", e.op, _to_tuple(e.lhs), _to_tuple(e.rhs))
    if isinstance(e, A.Call):
        fn = e.func.name if isinstance(e.func, A.Var) else "?"
        return ("call", fn) + tuple(_to_tuple(a) for a in e.args)
    if isinstance(e, A.Quant):
        return ("quant", e.kind, tuple(e.vars), _to_tuple(e.body))
    return ("node", type(e).__name__)


def _arith_term(e, atoms: Dict[tuple, str]) -> Optional[tuple]:
    """Convert a HARAN expr to an egraph Term over +,-,*; int leaves and Vars stay const/var (ORIGINAL names);
    any non-arithmetic subterm (Call, float, comparison, …) becomes a stable ATOM placeholder (a free unknown),
    its structural tuple remembered so its inner variables are restored — and renamed — afterwards. Returns
    None only for a bare non-arith node so the caller can keep it structural."""
    if isinstance(e, A.Num) and not e.is_float:
        return ("const", int(e.value))
    if isinstance(e, A.Var):
        return ("var", e.name)
    if isinstance(e, A.Bin) and e.op in ("+", "-", "*"):
        l = _arith_term(e.lhs, atoms)
        r = _arith_term(e.rhs, atoms)
        if l is not None and r is not None:
            return (e.op, l, r)
        return None
    # opaque subterm → atom placeholder keyed by its structural tuple (reused if seen again)
    s = _to_tuple(e)
    if s not in atoms:
        atoms[s] = f"@{len(atoms)}"
    return ("var", atoms[s])


# ─────────────────────────────────────────────── normal form (deterministic canonical string)
def _nf(t: tuple) -> tuple:
    """Canonical normal form of an egraph Term: flatten +/* chains, sort commutative operands, fold integer
    constants, drop +0 / *1 (and *0 → 0), and rewrite a−b ≡ a+(−1)·b. Equivalence-preserving."""
    op = t[0]
    if op in ("const", "var"):
        return t
    if op == "-":
        return _nf(("+", t[1], ("*", ("const", -1), t[2])))
    if op == "+":
        flat: List[tuple] = []
        _flatten("+", t, flat)
        const = 0
        terms: List[tuple] = []
        for s in (_nf(x) for x in flat):
            if s[0] == "const":
                const += s[1]
            else:
                terms.append(s)
        terms.sort(key=_key)
        if const != 0:
            terms.append(("const", const))
        if not terms:
            return ("const", 0)
        return terms[0] if len(terms) == 1 else _rebuild("+", terms)
    if op == "*":
        flat = []
        _flatten("*", t, flat)
        const = 1
        terms = []
        for s in (_nf(x) for x in flat):
            if s[0] == "const":
                const *= s[1]
            else:
                terms.append(s)
        if const == 0:
            return ("const", 0)
        terms.sort(key=_key)
        if const != 1 or not terms:
            terms.append(("const", const))
        return terms[0] if len(terms) == 1 else _rebuild("*", terms)
    return (op,) + tuple(_nf(c) if isinstance(c, tuple) else c for c in t[1:])  # opaque (call etc.): recurse tuples only


def _flatten(op: str, t: tuple, out: List[tuple]):
    if t[0] == op:
        for c in t[1:]:
            _flatten(op, c, out)
    else:
        out.append(t)


def _rebuild(op: str, terms: List[tuple]) -> tuple:
    acc = terms[0]
    for x in terms[1:]:
        acc = (op, acc, x)
    return acc


def _key(t) -> str:
    if not isinstance(t, tuple):
        return "s:" + str(t)
    if t[0] == "const":
        return "0const:" + str(t[1])
    if t[0] == "var":
        return "1var:" + str(t[1])
    return "2" + str(t[0]) + "(" + ",".join(_key(c) for c in t[1:]) + ")"


def _from_egraph(t: tuple) -> tuple:
    """Convert an extracted egraph Term (colon-encoded leaf ops 'const:V' / 'var:N') back to my tuple format
    ('const', int) / ('var', name) so _nf recognizes constants and variables."""
    op = t[0]
    if op.startswith("const:"):
        return ("const", int(op.split(":", 1)[1]))
    if op.startswith("var:"):
        return ("var", op.split(":", 1)[1])
    return (op,) + tuple(_from_egraph(c) for c in t[1:])


def _subst_atoms(t: tuple, rev: Dict[str, tuple]) -> tuple:
    """Replace atom placeholders ('var','@k') with their remembered structural tuple, so the inner variables
    are exposed to the final canonical rename."""
    if t[0] == "var" and isinstance(t[1], str) and t[1] in rev:
        return rev[t[1]]
    if t[0] in ("const", "var", "fconst", "bool"):
        return t
    return (t[0],) + tuple(_subst_atoms(c, rev) for c in t[1:])


def _canon_arith(term: tuple, atom_rev: Dict[str, tuple]) -> tuple:
    """Saturate the arith term in the e-graph (commute/assoc/distrib + const-fold), extract the lowest-cost
    representative, normal-form it, then restore atom placeholders → a deterministic canonical TUPLE."""
    eg = EGraph(deferred=True)
    root = eg.add_term(term)
    eg.saturate(_RULES, iters=8, node_cap=4000)
    # fold the constants the analysis discovered (merge each const-valued class with its const node)
    for cid in {eg.find(c) for c in range(len(eg.parent))}:
        v = eg.analysis.get(cid)
        if v is not None:
            eg.merge(cid, eg.add("const:" + str(v), ()))
    eg.rebuild()
    best, _cost = eg.extract(root, _COST)
    best = _from_egraph(best) if best is not None else term
    return ("A", _nf(_subst_atoms(best, atom_rev)))     # restore atoms first so _nf sorts them by structure


# ─────────────────────────────────────────────── semantic key of a whole goal (tuples; rename done last)
def _arith_key(e) -> tuple:
    atoms: Dict[tuple, str] = {}
    t = _arith_term(e, atoms)
    if t is None:
        return None
    rev = {ph: tup for tup, ph in atoms.items()}
    return _canon_arith(t, rev)


def _key_expr(e) -> tuple:
    # comparison → direction-normalize, then recurse on each side
    if isinstance(e, A.Bin) and e.op in _FLIP:
        op, l, r = e.op, e.lhs, e.rhs
        if op in ("<", "<="):                       # flip to the > / >= direction (swap operands)
            op, l, r = _FLIP[op], e.rhs, e.lhs
        return ("cmp", op, _key_expr(l), _key_expr(r))
    if isinstance(e, A.Bin) and (e.op in _SYMM):    # symmetric relation → sort the two sides
        a, b = sorted((_key_expr(e.lhs), _key_expr(e.rhs)))
        return ("cmp", e.op, a, b)
    if isinstance(e, A.Bin) and e.op in ("+", "-", "*"):
        k = _arith_key(e)
        if k is not None:
            return k
        return ("bin", e.op, _key_expr(e.lhs), _key_expr(e.rhs))
    if isinstance(e, A.Bin):                         # other binary (logical etc.) — structural
        return ("bin", e.op, _key_expr(e.lhs), _key_expr(e.rhs))
    if isinstance(e, A.Un):
        return ("un", e.op, _key_expr(e.operand))
    if isinstance(e, (A.Num, A.Var)):
        return _arith_key(e)
    return _to_tuple(e)


def _rename(t: tuple, ren: Dict[str, str]) -> tuple:
    """Single global canonical α-rename: every ('var', name) leaf → ('var', vK) by first occurrence in the
    already-normalized form. Sound for a universally-closed goal (a consistent bijective renaming)."""
    if t and t[0] == "var" and isinstance(t[1], str):
        if t[1] not in ren:
            ren[t[1]] = f"v{len(ren)}"
        return ("var", ren[t[1]])
    if not t or not isinstance(t, tuple):
        return t
    return tuple(_rename(c, ren) if isinstance(c, tuple) else c for c in t)


def semantic_key(goal, var_types: Dict[str, str], assumptions: List = ()) -> Tuple:
    ren: Dict[str, str] = {}
    g = _rename(_key_expr(goal), ren)
    asm = tuple(sorted(_rename(_key_expr(a), ren) for a in assumptions))
    types = tuple(sorted((ren[n], t) for n, t in var_types.items() if n in ren))
    return (g, asm, types)


# ─────────────────────────────────────────────── the cache (in-memory, no phone-home)
@dataclass
class _Stats:
    hits: int = 0
    misses: int = 0

    def rate(self) -> float:
        tot = self.hits + self.misses
        return round(self.hits / tot, 3) if tot else 0.0


_CACHE: Dict[Tuple, "Z.ProofResult"] = {}
STATS = _Stats()


def reset():
    _CACHE.clear()
    STATS.hits = STATS.misses = 0


def prove_forall_semantic(goal, var_types: Dict[str, str], assumptions: List = ()):
    """prove_forall with the SEMANTIC cache — a hit skips the solver. [Clock B] verification throughput."""
    key = semantic_key(goal, var_types, assumptions)
    if key in _CACHE:
        STATS.hits += 1
        c = _CACHE[key]
        return Z.ProofResult(c.verdict, c.backend + "+semcache", "semantic cache hit: " + c.detail, c.counterexample)
    STATS.misses += 1
    r = Z.prove_forall(goal, var_types, list(assumptions))
    _CACHE[key] = r
    return r


# ─────────────────────────────────────────────── §2.2 interval-domain entailment (NOT e-graph)
@dataclass(frozen=True)
class Interval:
    lo: float
    hi: float
    lo_open: bool
    hi_open: bool

    def subset_of(self, o: "Interval") -> bool:
        """self ⊆ other (this constraint is at least as strong)."""
        lo_ok = (o.lo < self.lo) or (o.lo == self.lo and (not o.lo_open or self.lo_open))
        hi_ok = (o.hi > self.hi) or (o.hi == self.hi and (not o.hi_open or self.hi_open))
        return lo_ok and hi_ok


def _interval(op: str, c: float) -> Interval:
    if op == ">":
        return Interval(c, math.inf, True, False)
    if op == ">=":
        return Interval(c, math.inf, False, False)
    if op == "<":
        return Interval(-math.inf, c, False, True)
    if op == "<=":
        return Interval(-math.inf, c, False, False)
    raise ValueError(op)


def entails_bound(fact_op: str, fact_c: float, goal_op: str, goal_c: float) -> bool:
    """For the SAME variable, does (x fact_op fact_c) ⟹ (x goal_op goal_c)?  Decided by interval subsumption
    in O(1) — no solver. e.g. (x>5) ⟹ (x>0) is True; (x>0) ⟹ (x>5) is False."""
    return _interval(fact_op, fact_c).subset_of(_interval(goal_op, goal_c))


# ─────────────────────────────────────────────── measurement (§2.4) + dogfood soundness
def measure_semantic_cache(workload) -> dict:
    """workload: list of (goal_ast, var_types, assumptions). Reports the SMT-BYPASS count (the Clock B metric:
    solver calls avoided) for semantic vs structural caching, the LOSSLESS audit (every hit re-solved fresh
    must match — the soundness guarantee), and the honest per-call COST break-even (the e-graph machinery is
    not free). Wall-clock single-pass comparisons are warmup-confounded, so we report warm per-call costs."""
    import time
    import proof_cache as PC

    reset()
    for goal, vt, asm in workload:
        prove_forall_semantic(goal, vt, asm)
    sem_hits, sem_misses = STATS.hits, STATS.misses

    PC.reset()
    for goal, vt, asm in workload:
        PC.prove_forall_cached(goal, vt, asm)
    struct_hits = PC.STATS.hits

    # LOSSLESS audit (soundness): every cached verdict must equal a fresh solve
    mism = 0
    for goal, vt, asm in workload:
        k = semantic_key(goal, vt, asm)
        if _CACHE[k].verdict != Z.prove_forall(goal, vt, list(asm)).verdict:
            mism += 1

    # warm per-call costs (the honest break-even): key cost vs the solver call it bypasses
    reps = 5
    t0 = time.perf_counter()
    for _ in range(reps):
        for goal, vt, asm in workload:
            semantic_key(goal, vt, asm)
    key_us = (time.perf_counter() - t0) / (reps * len(workload)) * 1e6
    t0 = time.perf_counter()
    for _ in range(reps):
        for goal, vt, asm in workload:
            Z.prove_forall(goal, vt, list(asm))
    solve_us = (time.perf_counter() - t0) / (reps * len(workload)) * 1e6

    return {"n": len(workload), "semantic_hits": sem_hits, "semantic_misses": sem_misses,
            "semantic_hit_rate": round(sem_hits / len(workload), 3), "structural_hits": struct_hits,
            "structural_hit_rate": round(struct_hits / len(workload), 3),
            "smt_bypass_extra": sem_hits - struct_hits, "lossless_mismatches": mism,
            "key_us": round(key_us, 1), "solve_us": round(solve_us, 1),
            "bypass_pays_off": solve_us > key_us}
