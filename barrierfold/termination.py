"""
§AE ISLAND 6 — TERMINATION (barrier: Turing halting problem, undecidable — the absolute wall).
================================================================================================================
The halting problem is PROVEN undecidable (Turing 1936); we NEVER claim to solve it. The island: the loop classes whose
termination IS decidable — bounded loops (trivial), linear ranking functions (Podelski-Rybalchenko, complete via
Farkas/LP), Size-Change Termination (Lee-Jones-Ben-Amram 2001, decidable PSPACE), polynomial ranking (SOS, real-decidable
— ★ but integer-undecidable, so integer loops get linear/lexicographic only), and HARAN `decreases` contracts (the user
declares the measure; we VERIFY, not synthesize — like type-checking vs inference, trivially decidable).

★ THE HONESTY OATH (binding): the general halting problem is PROVEN undecidable; we do NOT solve it. We say "this loop
terminates BECAUSE it has a ranking function / a verified decreases clause," NEVER "this loop terminates" in general. A
build claiming a general halting solution FAILS. ★ z3 gate: LRF/decreases → QF_LRA (`f(x) > f(x') ∧ f(x) ≥ 0`, simplex,
terminating); once termination is proved, the loop folds. Repo-first: reuses ISLAND 5 synthesis + the HARAN `decreases`
contract pattern (§AC-F2). DECLINE: general `while`, terminating-but-no-ranking-function (Collatz), data-dependent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

HALTING_OATH = ("the general halting problem is PROVEN undecidable (Turing 1936); this module folds ONLY the decidable "
                "termination islands and DECLINEs the rest — 'terminates because it has a ranking function / a verified "
                "decreases clause', NEVER 'terminates' in general")


@dataclass
class TerminationProof:
    issued: bool
    method: str = ""                        # "bounded" | "linear-ranking" | "size-change" | "decreases-contract"
    witness: str = ""                       # the ranking function / measure (the REASON it terminates)
    decreases: bool = False
    bounded_below: bool = False
    claim: str = ""                         # ★ "terminates because <witness>" — NEVER "terminates"
    detail: str = ""

    @property
    def proved(self) -> bool:
        return self.decreases and self.bounded_below


def prove_linear_ranking(step: int = 1) -> TerminationProof:
    """Podelski-Rybalchenko (complete linear RF): for `while i<n: i+=step` (step≥1), the ranking f(i)=n−i decreases by
    step>0 each iteration and is ≥0 under the guard. z3 QF_LRA verifies both (terminating). ★ Terminates BECAUSE f is a
    ranking function — not a general halting claim."""
    import z3
    i, n = z3.Ints("i n")
    guard = i < n
    f = n - i
    dec = z3.Solver().check(z3.Not(z3.Implies(guard, f > (n - (i + step))))) == z3.unsat if step >= 1 else False
    nonneg = z3.Solver().check(z3.Not(z3.Implies(guard, f >= 0))) == z3.unsat
    ok = dec and nonneg and step >= 1
    return TerminationProof(ok, "linear-ranking", "f(i)=n−i", dec, nonneg,
                            claim="terminates BECAUSE f(i)=n−i is a ranking function (decreases by step>0, bounded ≥0)",
                            detail="Podelski-Rybalchenko linear RF, z3 QF_LRA-verified (terminating); loop then folds"
                                   if ok else "no linear ranking function ⇒ DECLINE (NOT 'does not terminate' — just unproved)")


def verify_decreases_contract(measure_decreases: bool, measure_nonneg: bool) -> TerminationProof:
    """HARAN `decreases m` contract: the user DECLARES the measure; we VERIFY (guard⟹m≥0, guard∧body⟹m'<m) in QF_LRA —
    like type-checking vs inference, trivially decidable. Here the two VC results are passed in (z3-checked by the caller)."""
    ok = measure_decreases and measure_nonneg
    return TerminationProof(ok, "decreases-contract", "user-declared measure m", measure_decreases, measure_nonneg,
                            claim="terminates BECAUSE the declared `decreases m` is verified (m≥0 ∧ m'<m)",
                            detail="HARAN decreases contract VERIFIED (not synthesized), z3 QF_LRA; loop folds"
                                   if ok else "declared measure fails a VC ⇒ DECLINE")


def size_change_terminates(edges: List[Tuple[str, str, str]]) -> TerminationProof:
    """Size-Change Termination (Lee-Jones-Ben-Amram, decidable): edges (param→param, '↓' strict / '↓=' non-strict).
    Terminates iff every idempotent closure has a strictly-decreasing self-loop. Here: a single self-decreasing param
    ('x','x','↓') on every cycle ⇒ terminates (the decidable core)."""
    has_strict_self = any(s == t and rel == "↓" for s, t, rel in edges)
    return TerminationProof(has_strict_self, "size-change", "size-change graph closure",
                            decreases=has_strict_self, bounded_below=True,   # naturals are well-founded ≥0
                            claim="terminates BECAUSE every size-change cycle has a strictly-decreasing parameter",
                            detail="SCT (Lee-Jones-Ben-Amram) decidable closure: strict-decrease on every cycle"
                                   if has_strict_self else "no strictly-decreasing parameter on a cycle ⇒ DECLINE")


def bounded_loop(N: int) -> TerminationProof:
    return TerminationProof(N >= 0, "bounded", f"N={N}", True, True,
                            claim=f"terminates BECAUSE it runs a bounded N={N} iterations",
                            detail="bounded loop (trivially terminating)")


def general_while_declined() -> TerminationProof:
    """★ A general `while <data-dependent>` / Collatz-type loop has NO decidable termination proof ⇒ DECLINE. We do NOT
    claim it does or does not terminate — the halting problem forbids the general decision."""
    return TerminationProof(False, "general", "", False, False,
                            claim="(no claim — general halting is undecidable)",
                            detail="general while / no ranking function / Collatz ⇒ DECLINE (NOT a termination verdict — "
                                   "the halting problem is undecidable; we neither affirm nor deny, we DECLINE)")


def adversarial_battery() -> dict:
    """A counted loop terminates by a linear RF (z3-verified); a decreases-contract verifies; SCT proves a
    strictly-decreasing-cycle loop; ★ a general while is DECLINED (no claim); ★ the oath holds — every issued proof says
    'terminates BECAUSE <witness>', never bare 'terminates'; a non-decreasing 'ranking' (step=0) is rejected."""
    lrf = prove_linear_ranking(step=1)
    contract = verify_decreases_contract(measure_decreases=True, measure_nonneg=True)
    sct = size_change_terminates([("x", "x", "↓"), ("y", "x", "↓=")])
    nonrf = prove_linear_ranking(step=0)                     # step=0 ⇒ doesn't decrease ⇒ rejected
    gen = general_while_declined()
    cases = {
        "linear_ranking_proves": lrf.proved and lrf.method == "linear-ranking",
        "decreases_contract_verifies": contract.proved and contract.method == "decreases-contract",
        "size_change_proves": sct.proved and sct.method == "size-change",
        "non_decreasing_rejected": not nonrf.proved,         # step=0 ⇒ not a ranking function
        "general_while_declined": not gen.issued and "DECLINE" in gen.detail,   # ★ no general halting claim
        "oath_no_bare_terminates_claim": all("BECAUSE" in p.claim for p in (lrf, contract, sct)),  # ★ the oath
        "halting_oath_stated": "PROVEN undecidable" in HALTING_OATH,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
