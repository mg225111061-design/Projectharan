"""
§X PARADIGM 1 — AXIOMATIC / GUARD-SYNTHESIS FOLD (the strongest; both research models converged here).
================================================================================================================
Most production loops DECLINE not for lack of structure but because one final parameter (a stride, a modulus, an
offset, a length) is dynamic. Synthesize a guard Φ under which the loop folds, ISSUE a guarded fold proved equivalent
under Φ, and APPLY it (with a safe fallback) only at callsites where Φ provably holds.

★ Two-stage z3 gate (precision 1.0): (a) prove ∀inputs. Φ ⟹ folded==original — issue the guarded certificate only if
valid; (b) at each callsite, prove the caller's context ⟹ Φ — apply only where implied, else keep the original.
★ Issued-vs-applied (the trap): a guarded fold whose guard NO real callsite satisfies issues a certificate but
contributes ZERO to the fold rate. We MEASURE both; the fold rate is the APPLIED count.
★ NO new certificate kind — the existing EXACT verdict gains a `guard` field; the fold still routes to an existing
mechanism (here the polynomial/linear closed-form fold).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class GuardedFold:
    issued: bool                        # the guarded certificate was z3-validated (Φ ⟹ folded==original)
    paradigm: str = "axiomatic_guard"
    mechanism: str = "linear_recurrence"   # an EXISTING certificate kind — no 23rd
    guard: Optional[str] = None         # the synthesized precondition Φ (None ⇒ not issued)
    applied_callsites: List[str] = field(default_factory=list)   # callsites where Φ provably holds (the fold rate)
    skipped_callsites: List[str] = field(default_factory=list)   # callsites where Φ not implied ⇒ original kept
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def _prove_under(folded: Callable, original: Callable, var_names: List[str], guard: Callable) -> bool:
    """z3: prove ∀vars. guard(vars) ⟹ folded(vars) == original(vars). True ⇒ the guarded fold is sound."""
    from catalog.equiv_check import prove_equiv_z3
    r = prove_equiv_z3(folded, original, var_names, assumptions=guard)
    return r.proved


# guard template library — each maps a constant to a (env→z3 bool) precondition Φ
def _eq_const(var, c):
    return lambda e: e[var] == c


def synthesize_guard(folded: Callable, original: Callable, var_names: List[str], dyn_var: str,
                     candidates: List[int]) -> GuardedFold:
    """CEGAR-lite guard synthesis: the loop DECLINEs while `dyn_var` is free; try pinning it to each candidate
    constant and prove the fold sound under that guard. The first guard that makes `Φ ⟹ folded==original` z3-valid is
    issued. None ⇒ DECLINE (no sound guard found)."""
    for c in candidates:
        g = _eq_const(dyn_var, c)
        if _prove_under(folded, original, var_names, g):
            return GuardedFold(True, guard=f"{dyn_var} == {c}",
                               detail=f"folded ≡ original under {dyn_var}=={c} (z3 ∀-proved); guarded fold issued")
    return GuardedFold(False, detail=f"no guard over {dyn_var}∈{candidates} makes the fold sound — DECLINE")


def apply_at_callsite(gf: GuardedFold, callsite: str, var_names: List[str], dyn_var: str,
                      callsite_value: Optional[int]) -> bool:
    """Apply the guarded fold at a callsite ONLY if the callsite's context provably implies Φ. Here the context binds
    `dyn_var` to a known value (or leaves it dynamic ⇒ None). Proven ⇒ applied (counts toward the fold rate); else
    the original is kept (NOT counted)."""
    if not gf.issued or gf.guard is None:
        return False
    # Φ is `dyn_var == c`; the callsite implies it iff its bound value equals c
    try:
        c = int(gf.guard.split("==")[1].strip())
    except Exception:  # noqa: BLE001
        return False
    if callsite_value is not None and callsite_value == c:
        gf.applied_callsites.append(callsite)
        return True
    gf.skipped_callsites.append(callsite)
    return False


def adversarial_battery() -> dict:
    """Every unsound case MUST be rejected: (1) a guard that does NOT make the fold sound is never issued; (2) a
    callsite where Φ does not hold gets the original, not the fold."""
    import z3
    # original f(x,k) = x*k ; folded g(x) = x*4 (a constant-folded scaling). Sound ONLY under k==4.
    folded = lambda e: e["x"] * 4
    original = lambda e: e["x"] * e["k"]
    # (1a) the correct guard k==4 IS issued
    good = synthesize_guard(folded, original, ["x", "k"], "k", [2, 3, 4, 5])
    # (1b) a folded form with NO sound constant guard (x*4 vs x*k+1) is never issued
    bad_fold = synthesize_guard(lambda e: e["x"] * 4, lambda e: e["x"] * e["k"] + 1, ["x", "k"], "k", [2, 3, 4, 5])
    # (2) a callsite where k=7 (≠4) does NOT get the fold; a callsite where k=4 does
    g2 = synthesize_guard(folded, original, ["x", "k"], "k", [4])
    applied_at_4 = apply_at_callsite(g2, "callsite_k4", ["x", "k"], "k", 4)
    applied_at_7 = apply_at_callsite(g2, "callsite_k7", ["x", "k"], "k", 7)
    cases = {
        "correct_guard_issued": good.issued and good.guard == "k == 4",
        "unsound_fold_not_issued": not bad_fold.issued,
        "callsite_holds_applied": applied_at_4,
        "callsite_unmet_not_applied": not applied_at_7,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
