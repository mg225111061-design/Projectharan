"""
§BO newengine3/ — 3-domain new ENGINE recognition branches (certificate-or-DECLINE; decidable-boundary guards).
==================================================================================================================
Three domains — probabilistic-program exact analysis, decidable first-order/temporal logic fragments, and CSP
dichotomy.  Like §BM/§BN, every module is a new *recognition branch* of one of the 14 mechanisms (NO 15th), and
every EXACT rides an INDEPENDENTLY re-checked certificate ⇒ a construction bug ⇒ failed cert ⇒ DECLINE.

★ The flagship — prob_loop_moment — is the research's max-ROI finding: the MOMENTS of a prob-solvable affine loop
are C-finite recurrences, so the engine REUSES the existing `cfinite` companion-matrix solver almost verbatim;
net-new is only the recognition + expectation semantics + building the moment-update matrix T.

★ HARD GUARDS (the directive's absolute boundaries):
  • PROMISE CSP (PCSP) is ABSOLUTELY FORBIDDEN — open dichotomy ⇒ DECLINE (csp_dichotomy).
  • Skolem-problem order ≥ 5 is OPEN ⇒ DECLINE (decidable_logic.skolem_decide).
  • non-affine / iteration-dependent probabilistic loops (moments don't close) ⇒ DECLINE (prob_loop_moment).
  • function symbols leave EPR (full FO undecidable) ⇒ DECLINE (decidable_logic.epr_decide).
  • non-Boolean CSP (domain>2) ⇒ DECLINE (Boolean Schaefer fragment only).

Reuses cfinite (C-finite fold), z3 + z3_guard (EPR), native linear algebra ideas (affine CSP).  zero-dep;
every output rides the verdict ADT.
"""
from __future__ import annotations

from newengine3 import csp_dichotomy, decidable_logic, prob_loop_moment

_MODULES = {
    "prob_loop_moment": prob_loop_moment, "decidable_logic": decidable_logic, "csp_dichotomy": csp_dichotomy,
}


def adversarial_battery() -> dict:
    """Run every §BO engine's battery — the whole tranche green in one call."""
    subs = {name: mod.adversarial_battery() for name, mod in _MODULES.items()}
    return {"engines": len(subs), "all_ok": all(s["all_ok"] for s in subs.values()),
            "failed": {k: s["failed"] for k, s in subs.items() if not s["all_ok"]}}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
