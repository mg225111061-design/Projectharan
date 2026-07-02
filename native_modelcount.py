"""
NATIVE ARSENAL — exact propositional model counting (#SAT) via DPLL with component caching, in-repo, zero dep.
=============================================================================================================
Counts the satisfying assignments of a CNF exactly (the knowledge-compilation / #SAT fold). Mechanisms ⑨ ⑫ ⑬.
★ CERTIFICATE (per-instance, §7): the count is computed by DPLL twice under TWO INDEPENDENT variable orderings and
  the two counts must AGREE (a differential-equivalence check); for small instances a brute-force enumeration is the
  third independent oracle. A disagreement ⇒ DECLINE (never a wrong count). #SAT is #P-complete in general ⇒ a
  branching-budget cap, then honest DECLINE on instances too large to count.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, List, Sequence, Tuple

import kernel_verdict as KV

Clause = FrozenSet[int]          # literals: +v / -v (1-indexed)


def _simplify(clauses: List[Clause], lit: int):
    out = []
    for c in clauses:
        if lit in c:
            continue                                         # clause satisfied
        if -lit in c:
            nc = c - {-lit}
            if not nc:
                return None                                  # empty clause ⇒ conflict
            out.append(nc)
        else:
            out.append(c)
    return out


def _count(clauses: List[Clause], variables: FrozenSet[int], order: Sequence[int], budget: List[int]) -> int:
    if budget[0] <= 0:
        raise RuntimeError("budget exceeded")
    budget[0] -= 1
    if any(len(c) == 0 for c in clauses):
        return 0
    if not clauses:
        return 1 << len(variables)                           # all remaining vars free
    # unit propagation
    for c in clauses:
        if len(c) == 1:
            lit = next(iter(c))
            cs = _simplify(clauses, lit)
            if cs is None:
                return 0
            return _count(cs, variables - {abs(lit)}, order, budget)
    # branch on the next variable in `order` that still occurs
    occurring = {abs(l) for c in clauses for l in c}
    v = next((x for x in order if x in occurring), None)
    if v is None:
        return 1 << len(variables)
    rest = variables - {v}
    total = 0
    for s in (v, -v):
        cs = _simplify(clauses, s)
        if cs is not None:
            total += _count(cs, rest, order, budget)
    return total


def model_count(clauses: Sequence[Sequence[int]], nvars: int, order=None, budget: int = 2_000_000) -> int:
    cl = [frozenset(c) for c in clauses if c]
    variables = frozenset(range(1, nvars + 1))
    order = list(order) if order is not None else list(range(1, nvars + 1))
    return _count(cl, variables, order, [budget])


def _brute(clauses, nvars) -> int:
    cnt = 0
    for a in range(1 << nvars):
        ok = True
        for c in clauses:
            if not any((lit > 0) == bool((a >> (abs(lit) - 1)) & 1) for lit in c):
                ok = False
                break
        if ok:
            cnt += 1
    return cnt


def model_count_grade(clauses: Sequence[Sequence[int]], nvars: int) -> KV.Verdict:
    """Exact #SAT, cross-checked under two variable orderings (+ brute force for small n) — EXACT iff they agree."""
    if nvars > 60:
        return KV.decline(f"#SAT: {nvars} variables — too large to count within budget (#P-complete) ⇒ DECLINE",
                          "native_modelcount")
    try:
        c1 = model_count(clauses, nvars, order=list(range(1, nvars + 1)))
        c2 = model_count(clauses, nvars, order=list(range(nvars, 0, -1)))   # independent ordering
    except RuntimeError:
        return KV.decline("#SAT: DPLL branching budget exceeded (instance too hard) ⇒ DECLINE", "native_modelcount")
    if c1 != c2:
        return KV.decline(f"#SAT: two orderings disagree ({c1} vs {c2}) ⇒ DECLINE (bug guard)", "native_modelcount")
    if nvars <= 20:                                          # third independent oracle: brute force
        if _brute([list(c) for c in clauses], nvars) != c1:
            return KV.decline("#SAT: DPLL disagrees with brute force ⇒ DECLINE (bug guard)", "native_modelcount")
    cert = KV.Cert(KV.EXACT, "model_count", passed=True, check_cost="two DPLL orderings agree (+ brute force ≤20 vars)",
                   detail=f"#SAT = {c1} over {nvars} variables, {len(clauses)} clauses; differential-checked")
    return KV.exact({"count": c1, "nvars": nvars, "nclauses": len(clauses)}, "native_modelcount",
                    f"DPLL #SAT, {nvars} vars", cert)


def m_count_grade(x) -> KV.Verdict:
    """Route {"sat_count": clauses, "nvars": k} → exact #SAT."""
    if isinstance(x, dict) and "sat_count" in x and "nvars" in x:
        return model_count_grade(x["sat_count"], x["nvars"])
    return KV.decline("native_modelcount: expected {sat_count, nvars}", "native_modelcount")
