"""
PHASE 1.S3 — independent recheck of SMT verdicts: checker A (Z3) ↔ checker B (bounded/RUP), disagree → DEFER.
=============================================================================================================
Z3 saying UNSAT/PROVEN is NOT trusted on its own (Gödel §3: no checker self-certifies; a single solver can be
buggy or fed a wrong translation). So an INDEPENDENT checker B re-checks Z3's verdict; disagreement ⇒ DEFER.
This EXTENDS proof_checker.py (which already provides the independent bounded search, the RUP/DRAT proof
recheck, and the metamorphic mapping battery) with a clean per-claim recheck certificate.

Three independent rechecks, none trusting Z3 alone:
  • SMT verdict   → robust_certify: Z3 ∀ AND an independent bounded search must AGREE (no cex). Z3-PROVEN with
                    a real counterexample ⇒ DEFER (soundness alarm — catches a buggy solver OR a mistranslation).
  • REFUTED cex   → re-evaluated CONCRETELY; a counterexample that does not actually violate ⇒ DEFER (bogus).
  • clause proof  → check_rup_proof re-derives the empty clause; a tampered RUP step ⇒ rejected.
  • mapping       → mapping_axioms_ok known-answer battery (a flipped operator flips one verdict ⇒ caught).

★ HARAN / dogfood: the recheck LOGIC is small and is itself a verification target — dogfood.py (S18) re-checks
the trusted core, and the mapping battery is a metamorphic CI test (a stated assumption turned into a test). ★
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import proof_checker as PC
import z3_adapter as Z


@dataclass
class RecheckCert:
    verdict: str                # PROVEN | REFUTED | DEFER
    agree: bool                 # did the independent checker B agree with Z3 (checker A)?
    method: str
    counterexample: Optional[dict] = None
    detail: str = ""

    def __str__(self):
        return f"{self.verdict} [recheck: {self.method}, agree={self.agree}] {self.detail}"


def recheck(expr: str, var_types: Dict[str, str], bound: int = 12) -> RecheckCert:
    """Cross-validate an SMT claim: Z3 (A) vs an independent bounded search (B). PROVEN only if BOTH agree;
    Z3-PROVEN contradicted by a real counterexample ⇒ DEFER (no false PASS)."""
    rv = PC.robust_certify(expr, var_types, bound=bound)
    if rv.status == "REFUTED" and rv.counterexample:
        # independently RE-EVALUATE the counterexample: it must actually violate the predicate
        val = PC._py_eval(expr, {k: int(v) for k, v in rv.counterexample.items()})
        if val is not False:
            return RecheckCert("DEFER", False, "concrete-cex-reeval",
                               rv.counterexample, "Z3 counterexample did NOT violate on re-eval — bogus, deferred")
    return RecheckCert(rv.status, rv.agree, "z3↔bounded cross-validation", rv.counterexample, str(rv))


def recheck_clause_proof(cnf: List, proof: List, nvars: int) -> Tuple[bool, str]:
    """Re-check a clause-level UNSAT proof: the RUP checker must derive ⊥, AND brute force must agree it's
    UNSAT. A tampered proof (a step not RUP-implied) ⇒ rejected."""
    res = PC.check_rup_proof(cnf, proof)
    rup_ok = (res.status == "UNSAT_VERIFIED")
    brute = PC.brute_unsat(cnf, nvars)
    agree = (rup_ok == brute)
    return (rup_ok and brute and agree), f"rup_ok={rup_ok}, brute_unsat={brute}, agree={agree}"


def mapping_sound() -> Tuple[bool, List[str]]:
    """Metamorphic recheck of the HARAN→Z3 mapping (a flipped operator flips a known-answer verdict)."""
    return PC.mapping_axioms_ok()
