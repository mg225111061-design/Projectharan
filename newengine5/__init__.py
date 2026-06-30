"""
§BN newengine5/ — 5-domain new ENGINE recognition branches (certificate-or-DECLINE; decidable-fragment guards).
==================================================================================================================
The §BN tranche across five domains — program-verification decision theory, advanced automata, graph
polynomial-exact islands, computable topology/geometry, deep number theory.  Like §BM, every module is a new
*recognition branch* of one of the 14 mechanisms (NO 15th), and every EXACT rides an INDEPENDENTLY re-checked
certificate ⇒ a construction bug ⇒ failed cert ⇒ DECLINE, never a false-EXACT.

★ The directive's spine — DECIDABLE-FRAGMENT GUARDS FIRST: each engine checks it is inside its decidable fragment
before answering, and DECLINEs the undecidable / not-known-poly residual:
  • tree_automata    — equality/DISEQUALITY-constrained tree automata are UNDECIDABLE ⇒ DECLINE.
  • wl_refine        — general graph isomorphism is not known poly; WL-equal w/o explicit π ⇒ DECLINE (iso is
                       claimed only with a re-checked permutation; non-iso via WL is always sound).
  • smith_homology   — ∂∂=0 verified (else not a complex ⇒ DECLINE); ranks cross-checked (Smith vs ℚ).
  • morse_inequalities — verifier; a violated Morse inequality ⇒ DECLINE.
  • alexander_poly   — Δ(1)=±1 normalization enforced (else not a knot Seifert matrix ⇒ DECLINE).
  • hasse_minkowski  — outside the squarefree/pairwise-coprime/small-solution fragment ⇒ DECLINE.
  • parikh_image     — ε-transitions break length-boundedness ⇒ DECLINE.

Amplifies the partial engines named by the directive: mech_persistence/mech_sheaf (→ smith_homology + morse),
mech_knot (→ alexander_poly), native_lattice.smith_normal_form (reused by smith_homology), presburger_qe
(semilinear backing for parikh_image), catalog/mech_sfa (automata family).  zero-dep (z3 + stdlib + numpy);
every output rides the verdict ADT.
"""
from __future__ import annotations

from newengine5 import (alexander_poly, hasse_minkowski, morse_inequalities, parikh_image, smith_homology,
                        tree_automata, wl_refine)

_MODULES = {
    "tree_automata": tree_automata, "wl_refine": wl_refine, "smith_homology": smith_homology,
    "morse_inequalities": morse_inequalities, "alexander_poly": alexander_poly,
    "hasse_minkowski": hasse_minkowski, "parikh_image": parikh_image,
}


def adversarial_battery() -> dict:
    """Run every §BN engine's battery — the whole tranche green in one call."""
    subs = {name: mod.adversarial_battery() for name, mod in _MODULES.items()}
    return {"engines": len(subs), "all_ok": all(s["all_ok"] for s in subs.values()),
            "failed": {k: s["failed"] for k, s in subs.items() if not s["all_ok"]}}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
