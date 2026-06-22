"""
Pillar 3 · ROUND 1 #22 — redundant guard / bounds-check elimination via a Z3 in-range proof (EXACT, SOUND).
============================================================================================================
A hot loop often re-checks a guard that is ALWAYS true (a defensive bound, a non-negativity test, a redundant
range check). If Z3 PROVES the guard holds for every input in the domain, the guard is dead and can be removed
— the unguarded loop is EXACTLY equivalent and faster. This is the soundness-critical direction (Constitution:
"a wrong 'safe' is a correctness bug"): we remove a check ONLY when Z3 proves it redundant (UNSAT of its
negation). If Z3 finds a counterexample (the guard can fail), we KEEP the check ⇒ DECLINE — never an unsound
removal. Graded EXACT (Z3 proof + differential + measured whole-program win); not-provably-redundant ⇒ DECLINE.
"""
from __future__ import annotations

from typing import Callable, Optional, Tuple

import z3

import kernel_verdict as KV
from pillar3 import lifting as LF


def prove_guard_redundant(guard_z3: Callable, var: str = "x",
                          domain: Callable = None) -> Tuple[bool, Optional[str]]:
    """Z3: is `guard_z3(x)` true for EVERY x in the domain? Proven iff Not(guard) is UNSAT (optionally under a
    domain constraint). Returns (redundant, counterexample). A counterexample ⇒ the guard can fail ⇒ KEEP it."""
    x = z3.Int(var)
    s = z3.Solver()
    if domain is not None:
        s.add(domain(x))
    s.add(z3.Not(guard_z3(x)))
    r = s.check()
    if r == z3.unsat:
        return True, None
    if r == z3.sat:
        return False, str(s.model())
    return False, "z3 unknown (not proven) — conservatively KEEP the guard"


def guard_grade(make_input: Callable[[], tuple], naive: Callable, optimized: Callable, guard_z3: Callable, *,
                n: int, samples: int = 5, residual_iters: int = 0, floor: float = 1.10,
                var: str = "x", domain: Callable = None) -> Tuple[KV.Verdict, Optional[object]]:
    """EXACT iff Z3 PROVES the guard redundant AND the unguarded form matches the guarded one differentially AND
    a whole-program win is measured. Guard not provably redundant ⇒ DECLINE (keep the check — sound)."""
    redundant, cex = prove_guard_redundant(guard_z3, var, domain)
    if not redundant:                                        # the soundness gate: never remove a live check
        return KV.decline(f"guard NOT provably redundant (counterexample {cex}) — KEEP the check ⇒ DECLINE",
                          "bounds_check"), None
    a = make_input()[0]
    if naive(a) != optimized(a):                             # differential corroboration on the real input
        return KV.decline("guard proven redundant but guarded≠unguarded (a wrong 'optimized') ⇒ DECLINE",
                          "bounds_check"), None
    rep = LF.measure_lift(lambda x: naive(x), lambda x: optimized(x), make_input, residual_iters, n=n, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"redundant guard removed but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE",
                       "bounds_check")
        v.report = rep
        return v, rep
    cert = KV.Cert(KV.EXACT, "z3_guard_redundant", passed=True, check_cost="Z3 ∀-domain (UNSAT of ¬guard)",
                   detail="Z3 proved the guard holds for every input ⇒ removal is behavior-preserving (EXACT)")
    v = KV.exact(optimized, "bounds_check", str(rep), cert)
    v.report = rep
    return v, rep


# ── a hot loop with a provably-redundant guard (y = x·x ≥ 0 always), and an UNSOUND-to-remove guard ────
def guarded_nonneg(a):
    out = []
    for x in a:
        y = x * x
        out.append(y if y >= 0 else 0)                       # guard y≥0 is ALWAYS true ⇒ redundant
    return out


def unguarded(a):
    return [x * x for x in a]


def guarded_positive(a):                                     # guard y>0 is NOT always true (x=0) ⇒ must KEEP
    out = []
    for x in a:
        y = x * x
        out.append(y if y > 0 else 99)                       # at x=0 this is 99, not 0 ⇒ removal would change it
    return out


_GUARD_CACHE: dict = {}


def make_guard_input(n: int = 80000):
    if n not in _GUARD_CACHE:
        import random as _rnd
        rng = _rnd.Random(67)
        _GUARD_CACHE[n] = ([rng.randrange(-1000, 1000) for _ in range(n)],)
    return _GUARD_CACHE[n]
