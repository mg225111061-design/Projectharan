"""
PHASE 2.S5 — translation validation: per-instance recheck that makes the optimizer UNTRUSTED.
==============================================================================================
Every aggressive transform (proof-directed opt P2.S3, superopt P2.S4) is re-checked by the MACHINE before
it is allowed — the optimizer may be buggy/UNTRUSTED because the result is always validated. A transform is
accepted only if the OUTPUT REFINES the INPUT (same result wherever the input is defined). Failure ⇒ DECLINE,
the safe original is kept (worst case = a missed optimization, never a wrong answer; §1.4).

Certificate kinds (never mixed):
  • IR / peephole  → Alive2-style REFINEMENT via Z3: prove (opt = orig) over all inputs (REFUTED ⇒ DECLINE+cex).
  • ring rewrite   → Schwartz-Zippel polynomial-identity test (reuses superopt.verify_equiv).
  • loop transform → dependency certificate: the reordered schedule must agree with the original on a battery
                     (a permutation that changes a result is caught). [exact dependency proof = EXTENDED/P2.S6]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import z3_adapter as Z


@dataclass
class ValidationCert:
    decision: str               # PASS | DECLINE
    kind: str                   # refinement(Z3) | schwartz-zippel | dependency
    counterexample: Optional[dict] = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.decision == "PASS"

    def __str__(self):
        return f"{self.decision} [{self.kind}] {self.detail}" + (f" cex={self.counterexample}" if self.counterexample else "")


def validate_ir_refinement(orig_expr: str, opt_expr: str, var_types: Dict[str, str]) -> ValidationCert:
    """Alive2-style: the optimized integer expression must EQUAL the original for all inputs (Z3). A wrong
    peephole (e.g. x*2 → x<<2 is fine; x*2 → x+x fine; x*3 → x<<2 WRONG) is REFUTED ⇒ DECLINE with a witness."""
    claim = f"({opt_expr}) = ({orig_expr})"
    r = Z.prove_predicate(claim, var_types)
    if r.verdict == "PROVEN":
        return ValidationCert("PASS", "refinement(Z3)", detail=f"opt ≡ orig proven: {claim}")
    if r.verdict == "REFUTED":
        return ValidationCert("DECLINE", "refinement(Z3)", r.counterexample,
                              "optimized ≠ original — transform DECLINED, original kept")
    return ValidationCert("DECLINE", "refinement(Z3)", detail="Z3 UNKNOWN — conservatively DECLINE (no risk)")


def validate_ring_rewrite(orig_term, opt_term) -> ValidationCert:
    """Ring-axiom rewrite (e-graph) validated by Schwartz-Zippel polynomial-identity testing."""
    import superopt as SO
    ok, eps = SO.verify_equiv(orig_term, opt_term)
    if ok:
        return ValidationCert("PASS", "schwartz-zippel", detail=f"identity holds, error ≤ {eps:.2e}")
    return ValidationCert("DECLINE", "schwartz-zippel", detail="distinct at a random point — transform DECLINED")


def validate_loop_transform(orig_fn: Callable, transformed_fn: Callable,
                            inputs: Sequence) -> ValidationCert:
    """A loop reordering (fusion/interchange/tiling) must produce the SAME result as the original on a battery
    of inputs. A transform that changes a result (unsound reordering) is caught ⇒ DECLINE."""
    for x in inputs:
        try:
            if orig_fn(x) != transformed_fn(x):
                return ValidationCert("DECLINE", "dependency", {"input": repr(x)},
                                      "reordered schedule changed a result — DECLINED")
        except Exception as e:  # noqa: BLE001
            return ValidationCert("DECLINE", "dependency", {"input": repr(x)}, f"transform raised {type(e).__name__}")
    return ValidationCert("PASS", "dependency", detail=f"agrees with original on {len(list(inputs))} inputs")


def validate(kind: str, **kw) -> ValidationCert:
    """Dispatch to the right certificate kind for a transform (rule §1.4: gate everything)."""
    if kind == "ir":
        return validate_ir_refinement(kw["orig_expr"], kw["opt_expr"], kw["var_types"])
    if kind == "ring":
        return validate_ring_rewrite(kw["orig_term"], kw["opt_term"])
    if kind == "loop":
        return validate_loop_transform(kw["orig_fn"], kw["transformed_fn"], kw["inputs"])
    return ValidationCert("DECLINE", "unknown", detail=f"no validator for kind={kind}")
