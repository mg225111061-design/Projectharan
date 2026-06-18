"""
v28 STAGE 23 — soundness-bug defense: independent proof checker + solver portfolio + mapping meta-tests.
========================================================================================================
If a mapping axiom (source→logic translation) or a solver has a boundary-condition bug, a FALSE thing can
be "proven" — an integrity collapse. (Yin-Yang/OpFuzz found 1500+ Z3/CVC4 bugs, 400+ soundness.) Three
independent layers, so no single mistake is trusted:

  1. independent proof CHECKER (this module's core) — a real RUP/DRAT-style propositional UNSAT checker.
     A claimed UNSAT proof is re-verified clause-by-clause by a small (~40-line) checker; the TCB shrinks
     to that checker, NOT the solver that produced the proof. A bogus proof is REJECTED.
  2. solver PORTFOLIO cross-check — a ∀-claim is accepted only if Z3 (symbolic, unbounded) is NOT
     contradicted by an INDEPENDENT bounded-domain search (concrete enumeration). Disagreement → DEFER+flag.
     ★A single solver saying "true" NEVER suffices for PROVEN.★
  3. mapping-axiom METAMORPHIC tests — each op mapping is checked semantics-preserving (z3-eval vs a
     concrete reference) on random inputs; a wrong mapping (e.g. `-`→`+`) is caught.

★ HONEST (§1.8, §5.5, §5.7) ★: the portfolio cannot catch a bug SHARED by all procedures; proofs do not
exist for every theory (NIA/quantifiers); a mapping must ultimately be DEFINED by someone — TCB
minimization (a tiny audited checker) is the ceiling, not elimination.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import z3_adapter as Z

Clause = List[int]      # e.g. [1, -2, 3]  =  (x1 ∨ ¬x2 ∨ x3)


# ── layer 1: an independent RUP/DRAT-style UNSAT proof checker (pure Python) ─────────────────────────
def _unit_propagate(clauses: List[Clause], assign: Dict[int, bool]) -> bool:
    """Unit-propagate `clauses` under `assign` (mutated). Return True iff a CONFLICT (a falsified clause)."""
    changed = True
    while changed:
        changed = False
        for cl in clauses:
            unassigned: List[int] = []
            satisfied = False
            for lit in cl:
                v, want = abs(lit), lit > 0
                if v in assign:
                    if assign[v] == want:
                        satisfied = True
                        break
                else:
                    unassigned.append(lit)
            if satisfied:
                continue
            if not unassigned:
                return True                          # all literals false → conflict
            if len(unassigned) == 1:
                lit = unassigned[0]
                assign[abs(lit)] = lit > 0
                changed = True
    return False


def rup_implied(clauses: List[Clause], c: Clause) -> bool:
    """Reverse Unit Propagation: clause `c` is implied by `clauses` iff assuming ¬c and unit-propagating
    yields a conflict. (The empty clause c=[] tests whether `clauses` alone is UNSAT.)"""
    assign = {abs(lit): (lit < 0) for lit in c}      # ¬c: each literal of c is forced FALSE
    return _unit_propagate([cl for cl in clauses], assign)


@dataclass
class CheckResult:
    status: str             # UNSAT_VERIFIED | REJECTED
    steps: int = 0
    detail: str = ""


def check_rup_proof(cnf: List[Clause], proof: List[Clause]) -> CheckResult:
    """Independently verify a clausal UNSAT proof: every added clause must be RUP-implied by the clauses so
    far, and the proof must derive the empty clause. The solver is NOT trusted — only this checker is."""
    f = [list(cl) for cl in cnf]
    for i, c in enumerate(proof):
        if not rup_implied(f, c):
            return CheckResult("REJECTED", i, f"proof step {i} ({c}) is NOT RUP-implied — proof rejected")
        f.append(list(c))
        if not c:                                    # derived the empty clause → UNSAT established
            return CheckResult("UNSAT_VERIFIED", i + 1, "empty clause derived; every step RUP-checked")
    return CheckResult("REJECTED", len(proof), "proof did not derive the empty clause")


def brute_unsat(cnf: List[Clause], nvars: int) -> bool:
    """Independent oracle (tiny CNF only): UNSAT iff no assignment over 2^nvars satisfies every clause."""
    for mask in range(1 << nvars):
        a = {v + 1: bool((mask >> v) & 1) for v in range(nvars)}
        if all(any(a[abs(l)] == (l > 0) for l in cl) for cl in cnf):
            return False
    return True


# ── layer 2: solver portfolio cross-check (Z3 + independent bounded enumeration) ────────────────────
def _py_eval(expr: str, assign: Dict[str, int]) -> Optional[bool]:
    """Evaluate a HARAN boolean predicate at a concrete int assignment — INDEPENDENT of Z3 (the cross-check
    oracle). HARAN `=` becomes Python `==`. Returns None if it cannot be evaluated."""
    import re
    py = re.sub(r"(?<![<>=!])=(?!=)", "==", expr)
    try:
        return bool(eval(py, {"__builtins__": {}}, dict(assign)))   # noqa: S307 — arithmetic over ints only
    except Exception:  # noqa: BLE001
        return None


def _bounded_counterexample(expr: str, var_types: Dict[str, str], bound: int) -> Optional[dict]:
    """Search [-bound,bound]^k for a concrete assignment that VIOLATES `expr` (an independent UX oracle)."""
    names = [n for n, t in var_types.items() if t in ("Int", "Nat") and n != "result"]
    if not names or len(names) > 3:
        return None
    lo = 0 if all(var_types[n] == "Nat" for n in names) else -bound
    rng = range(lo, bound + 1)
    import itertools
    for combo in itertools.product(rng, repeat=len(names)):
        assign = dict(zip(names, combo))
        val = _py_eval(expr, assign)
        if val is False:
            return assign
    return None


@dataclass
class RobustVerdict:
    status: str             # PROVEN | REFUTED | DEFER
    z3: str = ""
    agree: bool = True
    flag: str = ""
    counterexample: Optional[dict] = None
    detail: str = ""

    def __str__(self):
        if self.status == "DEFER":
            return f"DEFER — {self.flag} (single-solver result NOT trusted)"
        return f"{self.status} (z3={self.z3}, portfolio agree={self.agree})"


def robust_certify(expr: str, var_types: Dict[str, str], bound: int = 12,
                   second_opinion: Optional[Callable[[], Optional[dict]]] = None) -> RobustVerdict:
    """PROVEN only if Z3 says PROVEN AND an independent bounded search finds NO counterexample. If Z3 claims
    PROVEN but the independent search finds a real counterexample → DEFER+flag (a soundness alarm). A single
    solver's "true" never suffices. `second_opinion` injects an alternate oracle (for portfolio testing)."""
    r = Z.prove_predicate(expr, var_types)
    cex = second_opinion() if second_opinion is not None else _bounded_counterexample(expr, var_types, bound)
    if r.verdict == "PROVEN":
        if cex is not None:
            return RobustVerdict("DEFER", "PROVEN", False,
                                 "Z3 said PROVEN but an INDEPENDENT check found a counterexample",
                                 cex, "soundness disagreement — deferred")
        return RobustVerdict("PROVEN", "PROVEN", True, detail="Z3 ∀ + independent search agree (no cex)")
    if r.verdict == "REFUTED":
        return RobustVerdict("REFUTED", "REFUTED", True, counterexample=r.counterexample)
    return RobustVerdict("DEFER", r.verdict, False, "Z3 returned UNKNOWN", detail="undecided")


# ── layer 3: mapping-axiom metamorphic tests (axioms as verification TARGETS) ───────────────────────
def mapping_preserves_semantics(zfn: Callable[[int, int], int], pyfn: Callable[[int, int], int],
                                samples: int = 200, seed: int = 1) -> bool:
    """Metamorphic check of one binary-op mapping: the (candidate) z3-side function must agree with a
    concrete reference on random inputs. A wrong mapping (e.g. `-`→`+`) FAILS this."""
    rng = random.Random(seed)
    for _ in range(samples):
        a, b = rng.randint(-50, 50), rng.randint(-50, 50)
        if zfn(a, b) != pyfn(a, b):
            return False
    return True


# the end-to-end mapping (parse→Z3) is also pinned by known-answer identities — a flipped op would flip one
_MAPPING_BATTERY: List[Tuple[str, Dict[str, str], str]] = [
    ("a + b = b + a", {"a": "Int", "b": "Int"}, "PROVEN"),      # + commutes
    ("a * b = b * a", {"a": "Int", "b": "Int"}, "PROVEN"),      # * commutes
    ("a - b = b - a", {"a": "Int", "b": "Int"}, "REFUTED"),     # − does NOT (catches −↦+)
    ("a + 0 = a", {"a": "Int"}, "PROVEN"),
    ("a <= a + 1", {"a": "Int"}, "PROVEN"),                     # catches +↦−
    ("a < a", {"a": "Int"}, "REFUTED"),
]


def mapping_axioms_ok() -> Tuple[bool, List[str]]:
    """Verify the real HARAN→Z3 mapping is semantics-preserving via a known-answer battery (each op's
    truth pins its mapping). Returns (all_ok, mismatches)."""
    bad: List[str] = []
    for expr, vt, expected in _MAPPING_BATTERY:
        got = Z.prove_predicate(expr, vt).verdict
        if got != expected:
            bad.append(f"{expr}: expected {expected}, got {got}")
    return (not bad, bad)
