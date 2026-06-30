"""
§BM newengine/ — 10-field new ENGINE recognition branches (certificate-or-DECLINE; NO 15th mechanism).
========================================================================================================
Every module here is a new *recognition branch* of one of the 14 mechanisms (the research confirmed none needs a
15th mechanism), and every EXACT verdict is gated on an INDEPENDENTLY re-checked certificate — so a construction
bug yields a failed cert ⇒ DECLINE, NEVER a false-EXACT. Approximations carry a stated bound; undecidable/general
problems DECLINE (Petri general reachability, NP-hard submodular maximization, …). The most under-mined axis —
Axis B (cheap verifiers for expensive computations) — is mined hard: Farkas/KKT, place-invariants, sifting,
Pfaffian, resultants are all proposer-verifier certificates that reduce to a residual / matrix check.

STAGE 1 (now): farkas · petri_invariant · schreier_sims · markov_exact · thermo_identity.
STAGE 2/3 amplifiers: kalman (→C-finite) · orbit_count (→Gröbner) · resultant (ring) · kasteleyn (→free-fermion) ·
riccati (residual-enforced). zero-dep (z3 + stdlib + numpy); every output rides `recall/core` / the verdict ADT.
"""
from __future__ import annotations

from newengine import (farkas, kalman, kasteleyn, markov_exact, orbit_count, petri_invariant, resultant,
                       riccati, schreier_sims, thermo_identity)

_MODULES = {
    "farkas": farkas, "petri_invariant": petri_invariant, "schreier_sims": schreier_sims,
    "markov_exact": markov_exact, "thermo_identity": thermo_identity, "kalman": kalman,
    "orbit_count": orbit_count, "resultant": resultant, "kasteleyn": kasteleyn, "riccati": riccati,
}


def adversarial_battery() -> dict:
    """Run every new engine's battery — the whole §BM tranche green in one call."""
    subs = {name: mod.adversarial_battery() for name, mod in _MODULES.items()}
    return {"engines": len(subs), "all_ok": all(s["all_ok"] for s in subs.values()),
            "failed": {k: s["failed"] for k, s in subs.items() if not s["all_ok"]}}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
