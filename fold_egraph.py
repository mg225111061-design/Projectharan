"""
perf-build STAGE 3 — FOLD as a first-class e-graph rewrite (fold penetrates the whole pipeline).
=================================================================================================
The fold kernels (Faulhaber power-sums, C-finite linear recurrences) are registered as e-graph REWRITE RULES,
reusing egraph.py (no new engine). When the LLM-recognized structure appears, saturation substitutes the
O(n) summation/recurrence node with its O(1)/O(log n) CLOSED node — and the e-graph's cost extraction then
picks the cheap form. This is the sound realization of the effect earlier docs mis-attributed.

★ SOUND-OR-DECLINE (§3.3) ★ a fold rule is created ONLY after its certificate passes:
    • Faulhaber Σk^p : the closed polynomial is numeric-rechecked == the naive sum for several n;
    • C-finite       : verify_cfinite (companion_nth ≡ naive_nth, exact integers).
  A wrong/unprovable closed form yields NO rule ⇒ the node stays O(n) ⇒ honest DECLINE. Never a wrong fold.

★ CACHE NORMALIZATION (§3.2) ★ the certified CLOSED node is canonical, so fold-equivalent expressions reduce
  to the same form (and thus the same semantic-cache key).

★ HARAN-FIRST (§3.4) ★ each rewrite rule is an algebraic identity that is MACHINE-VERIFIED (the certificate),
  not trusted; dogfood feeds a forced-wrong closed form and the gate must reject it.

[Clock C] this accelerates EMITTED evaluation (O(n) → O(1)/O(log n), bit-exact); measured below, no fake numbers.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cfinite
from egraph import EGraph


# ───────────────────────────── closed forms + their soundness certificates
def faulhaber(p: int, n: int) -> int:
    """Closed form of Σ_{k=1}^{n} k^p for p∈{1,2,3} — exact integers (the products are divisible)."""
    if p == 1:
        return n * (n + 1) // 2
    if p == 2:
        return n * (n + 1) * (2 * n + 1) // 6
    if p == 3:
        t = n * (n + 1) // 2
        return t * t
    raise ValueError(f"no Faulhaber kernel for p={p}")


def powersum_naive(p: int, n: int) -> int:
    """O(n) reference: Σ_{k=1}^{n} k^p."""
    return sum(k ** p for k in range(1, n + 1))


def certify_powersum(p: int, ns=(5, 10, 17, 33, 64), closed=faulhaber) -> bool:
    """SOUND GATE: the closed form must equal the naive sum for every probe n (exact integers)."""
    try:
        return all(closed(p, n) == powersum_naive(p, n) for n in ns)
    except Exception:  # noqa: BLE001
        return False


# ───────────────────────────── the fold-aware e-graph
@dataclass
class FoldEGraph:
    recs: Dict[int, Tuple[Tuple[int, ...], Tuple[int, ...]]] = field(default_factory=dict)  # recid → (c, init)
    closed: Dict[int, "callable"] = field(default_factory=dict)                              # p → closed fn
    rules: List[Tuple[tuple, tuple]] = field(default_factory=list)
    certified: Dict[str, bool] = field(default_factory=dict)

    def register_powersum(self, p: int, closed=faulhaber) -> bool:
        """Register Σk^p → Closed iff the closed form certifies. Returns whether it was admitted."""
        ok = certify_powersum(p, closed=closed)
        self.certified[f"powersum:{p}"] = ok
        if ok:
            self.closed[p] = closed
            self.rules.append((("PowerSum", ("const", p), ("?", "n")),
                               (f"Closed:faulhaber:{p}", ("?", "n"))))
        return ok

    def register_linrec(self, recid: int, c: Tuple[int, ...], init: Tuple[int, ...]) -> bool:
        """Register a C-finite recurrence → companion (O(log n)) iff verify_cfinite passes."""
        ok, _checked = cfinite.verify_cfinite(list(c), list(init))
        self.certified[f"linrec:{recid}"] = ok
        if ok:
            self.recs[recid] = (tuple(c), tuple(init))
            self.rules.append((("LinRec", ("const", recid), ("?", "n")),
                               (f"Closed:companion:{recid}", ("?", "n"))))
        return ok

    # ── build an e-graph, saturate with the CERTIFIED fold rules + simple ring rules, return (eg, root) ──
    def saturate(self, term: tuple) -> Tuple[EGraph, int]:
        eg = EGraph(deferred=True)
        root = eg.add_term(term)
        eg.saturate(self.rules, iters=6, node_cap=20000)
        return eg, root

    def folds_in(self, eg: EGraph, root: int) -> bool:
        """Did a fold fire? — i.e. does root's e-class now contain a Closed node (the O(1)/O(log n) form)?"""
        rc = eg.find(root)
        return any(node.op.startswith("Closed:") for node in eg.classes.get(rc, []))

    # ── cost extraction: a summation/recurrence is "expensive" (O(n)); a Closed node is cheap (O(1)) ──
    _COST = {"PowerSum": 1000, "LinRec": 1000, "+": 1, "*": 1, "-": 1, "var": 0, "const": 0}

    def extract_best(self, eg: EGraph, root: int) -> tuple:
        best, _c = eg.extract(root, self._COST)
        return best


# ───────────────────────────── evaluator (O(n) naive vs O(1)/O(log n) closed) — for bit-exactness + timing
def eval_node(term: tuple, env: Dict[str, int], fe: FoldEGraph) -> int:
    """Evaluate an (egraph-encoded) term. PowerSum/LinRec are O(n)/O(n); Closed:* are O(1)/O(log n)."""
    op = term[0]
    if op.startswith("const:"):
        return int(op.split(":", 1)[1])
    if op.startswith("var:"):
        return env[op.split(":", 1)[1]]
    if op == "PowerSum":
        p = eval_node(term[1], env, fe)
        n = eval_node(term[2], env, fe)
        return powersum_naive(p, n)
    if op == "LinRec":
        recid = eval_node(term[1], env, fe)
        n = eval_node(term[2], env, fe)
        c, init = fe.recs[recid]
        return cfinite.naive_nth(list(c), list(init), n)
    if op.startswith("Closed:faulhaber:"):
        p = int(op.rsplit(":", 1)[1])
        return fe.closed[p](p, eval_node(term[1], env, fe))
    if op.startswith("Closed:companion:"):
        recid = int(op.rsplit(":", 1)[1])
        c, init = fe.recs[recid]
        return cfinite.companion_nth(list(c), list(init), eval_node(term[1], env, fe))
    if op == "+":
        return eval_node(term[1], env, fe) + eval_node(term[2], env, fe)
    if op == "*":
        return eval_node(term[1], env, fe) * eval_node(term[2], env, fe)
    if op == "-":
        return eval_node(term[1], env, fe) - eval_node(term[2], env, fe)
    raise ValueError(f"cannot eval {op}")


# ───────────────────────────── measurement: O(n) → O(1)/O(log n), bit-exact [Clock C]
def measure_fold(kind: str, ns=(1000, 10000, 100000)) -> dict:
    """Measure the emitted-evaluation speedup of the folded (closed) form vs the naive form, bit-exact."""
    fe = FoldEGraph()
    if kind == "powersum2":
        fe.register_powersum(2)
        naive = ("PowerSum", ("const:2",), ("var:n",))
    elif kind == "fib":
        fe.register_linrec(0, (1, 1), (0, 1))                  # Fibonacci
        naive = ("LinRec", ("const:0",), ("var:n",))
    else:
        raise ValueError(kind)
    eg, root = fe.saturate(_to_eg_input(naive))
    closed = fe.extract_best(eg, root)
    out = {"kind": kind, "fold_fired": fe.folds_in(eg, root), "bit_exact": True, "points": []}
    for n in ns:
        env = {"n": n}
        t = time.perf_counter()
        a = eval_node(naive, env, fe)
        naive_ms = (time.perf_counter() - t) * 1000
        t = time.perf_counter()
        b = eval_node(closed, env, fe)
        closed_ms = (time.perf_counter() - t) * 1000
        if a != b:
            out["bit_exact"] = False
        out["points"].append({"n": n, "naive_ms": round(naive_ms, 4), "closed_ms": round(closed_ms, 6),
                               "speedup": round(naive_ms / closed_ms, 1) if closed_ms > 0 else None})
    return out


def _to_eg_input(term: tuple) -> tuple:
    """Convert my colon-encoded eval term to the add_term input format ('const',v)/('var',name)."""
    op = term[0]
    if op.startswith("const:"):
        return ("const", int(op.split(":", 1)[1]))
    if op.startswith("var:"):
        return ("var", op.split(":", 1)[1])
    return (op,) + tuple(_to_eg_input(c) for c in term[1:])


# ───────────────────────────── §3.2 cache normalization: fold-equivalent terms → same canonical key
def _canon_str(term: tuple) -> str:
    if term[0].startswith("var:"):
        return "VAR"                                # bound/free index abstracted (α): same kernel ⇒ same key
    if term[0].startswith("const:"):
        return term[0]
    return term[0] + "(" + ",".join(_canon_str(c) for c in term[1:]) + ")"


def fold_key(fe: FoldEGraph, term: tuple) -> str:
    """A semantic key that FOLDS first: saturate with the certified fold rules, extract the cheapest form,
    then canonicalize. A summation and (after the rule fires) its closed form share one e-class ⇒ one key —
    so fold-equivalent expressions get the SAME hash (participates in the STAGE-2 cache normalization)."""
    eg, root = fe.saturate(_to_eg_input(term))
    return _canon_str(fe.extract_best(eg, root))


# ───────────────────────────── §3.4 HARAN-first cross-validation: confirm Faulhaber via the C-finite engine
def _powersum_recurrence(p: int) -> Tuple[List[int], List[int]]:
    """Σk^p is a degree-(p+1) polynomial ⇒ it satisfies the constant-coefficient recurrence (E−1)^(p+2)=0:
    S(n)=Σ_{i=1}^{p+2} (−1)^(i+1) C(p+2,i) S(n−i). Coefficients + the first p+2 values (an INDEPENDENT kernel)."""
    from math import comb
    order = p + 2
    c = [((-1) ** (i + 1)) * comb(order, i) for i in range(1, order + 1)]
    init = [powersum_naive(p, n) for n in range(order)]      # S(0..p+1)
    return c, init


def cross_validate_powersum(p: int, ns=(7, 15, 31, 50)) -> bool:
    """HARAN-first / dogfood: the Faulhaber closed form must AGREE with the INDEPENDENT C-finite
    companion-matrix engine (cfinite.companion_nth) for several n — two different kernels, same answer."""
    c, init = _powersum_recurrence(p)
    ok, _ = cfinite.verify_cfinite(c, init)                  # companion ≡ naive recurrence (exact int)
    return ok and all(cfinite.companion_nth(c, init, n) == faulhaber(p, n) for n in ns)
