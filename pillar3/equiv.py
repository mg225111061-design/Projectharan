"""
Pillar 3 · Stage 4 — the equivalence certificate (the moat; Alive2-spirit bounded translation validation).
==========================================================================================================
The bigger the algorithm swap, the more the proof is worth. For a recognized replacement we attempt a Z3
proof that it is equivalent to the original over the input domain by running BOTH implementations on SYMBOLIC
inputs (Z3 Int matrices) for bounded dimensions and proving the output expressions are identical for ALL
inputs. No Lean/Coq/Isabelle — Z3 only.
  • Z3 proves equivalence (bounded)  → EXACT, auto-applicable.
  • only differential testing passes → PROBABILISTIC(ε,δ).
  • Z3 finds a counterexample / differential fails → DECLINE.  ★ This is what catches a wrong 1000× swap. ★
"""
from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

import z3

import kernel_verdict as KV
from pillar3 import measure as M
from pillar3 import record as RC


def _sym_matrix(prefix: str, n: int) -> List[List[Any]]:
    return [[z3.Int(f"{prefix}{i}_{j}") for j in range(n)] for i in range(n)]


def _flatten(x) -> List[Any]:
    if isinstance(x, (list, tuple)):
        out = []
        for e in x:
            out += _flatten(e)
        return out
    return [x]


def prove_equiv(naive_fn: Callable, cand_fn: Callable, sym_factory: Callable[[int], tuple],
                sizes: Tuple[int, ...]) -> "tuple[bool, Optional[str]]":
    """Generic bounded translation validation: for each size, run BOTH implementations on the symbolic inputs
    produced by sym_factory(size) and prove every (flattened) output entry is identical for ALL inputs (Z3).
    Returns (proven, counterexample_or_None)."""
    for sz in sizes:
        inputs = sym_factory(sz)
        try:
            RA, RB = _flatten(naive_fn(*inputs)), _flatten(cand_fn(*inputs))
        except Exception as e:  # noqa: BLE001 — a candidate that can't run symbolically is not provable here
            return False, f"symbolic execution failed (size={sz}): {type(e).__name__}: {e}"
        if len(RA) != len(RB):
            return False, f"output shape mismatch at size={sz}"
        s = z3.Solver()
        s.add(z3.Or(*[RA[i] != RB[i] for i in range(len(RA))]))   # negation: ∃ input where some entry differs
        r = s.check()
        if r == z3.sat:
            return False, f"Z3 counterexample at size={sz}: {s.model()}"
        if r != z3.unsat:
            return False, f"Z3 unknown at size={sz}"
    return True, None


def prove_equiv_matmul(naive_fn: Callable, cand_fn: Callable, dims: Tuple[int, ...] = (2, 3)):
    return prove_equiv(naive_fn, cand_fn, lambda n: (_sym_matrix("a", n), _sym_matrix("b", n)), dims)


def sym_poly_inputs(degree: int) -> tuple:
    """Symbolic inputs for a polynomial evaluator: (coeffs[0..degree], x)."""
    return ([z3.Int(f"c{i}") for i in range(degree + 1)], z3.Int("x"))


def grade_replacement(naive_fn: Callable, cand_fn: Callable, make_args: Callable[[], tuple], *,
                      n: int, hotspot_fraction: float, oracle: List[Tuple[tuple, Any]],
                      prove: Callable[[], "tuple[bool, Optional[str]]"] = None, floor: float = 1.10,
                      eq: Callable[[Any, Any], bool] = None, samples: int = 5) -> KV.Verdict:
    """The moat in action: differential FIRST (Rule 4); then if a Z3 proof is supplied and verifies → EXACT,
    else differential-only → PROBABILISTIC; a failed proof OR a failed differential → DECLINE. Then measure
    whole-program and require a win ≥ floor (else DECLINE — no 'EXACT 1.0×')."""
    diff = RC.differential_test(cand_fn, oracle, eq)
    if not diff.passed:
        return KV.decline(f"differential FAILED ({diff.mismatches}/{diff.n}; first {diff.first_mismatch}) — "
                          f"a wrong replacement, even if faster ⇒ DECLINE", "algo_replace")
    proven, cex = (prove() if prove else (False, "no proof attempted"))
    if prove and not proven and cex and "counterexample" in str(cex):
        # Z3 actively refuted equivalence (the differential just didn't happen to hit it) ⇒ DECLINE
        return KV.decline(f"Z3 REFUTED equivalence ({cex}) ⇒ DECLINE (the moat caught a wrong swap)", "algo_replace")
    rep = M.measure_whole_program(naive_fn, cand_fn, make_args, n=n, hotspot_fraction=hotspot_fraction, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"no whole-program win ≥ {floor:.2f}× (measured {rep.whole_program_ratio:.2f}×) ⇒ DECLINE",
                       "algo_replace")
        v.report = rep
        return v
    if proven:
        cert = KV.Cert(KV.EXACT, "z3_bounded_translation_validation", passed=True, check_cost="Z3 bounded",
                       detail="Z3 proved output equivalence on symbolic inputs for all bounded dims (Alive2-spirit)")
        v = KV.exact(cand_fn, "algo_replace", str(rep), cert)
    else:
        cert = KV.Cert(KV.PROBABILISTIC, "differential", passed=True, check_cost=f"O(n)={diff.n} cases",
                       delta=diff.rule_of_three_delta,
                       detail=f"differential PASS on {diff.n} cases; Z3 not conclusive ⇒ PROBABILISTIC δ=3/n")
        v = KV.probabilistic(cand_fn, "algo_replace", str(rep), cert)
    v.report = rep
    return v
