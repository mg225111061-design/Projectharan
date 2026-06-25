"""Mechanism 9 — COMPLETE INVARIANT for classification (univalence = the *definition* of this mechanism;
Cartan–Karlhede, Petrov, operator-algebra type I/II/III, syntactic monoid, modular decomposition, Big-Five
reversal, proof-theoretic ordinal, arithmetic-hierarchy position, stability/U-rank, Hohenberg–Kohn, topological
invariants Chern/Z₂). Output: a complete invariant that decides isomorphism/equivalence (⟂ M14 turbulence when
NO complete invariant exists)."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "classify" in f.tags:
        s += 0.6
    if "physics" in f.tags:
        s += 0.2
    if "size_class" in f.tags:
        s += 0.1
    return min(1.0, s)


def _apply(x, **kw):
    """Mechanism 9: a complete invariant. Buckingham-Π (dimensionless-group normal form), Petrov (Weyl algebraic
    type), and — NEW (capstone) — the minimal DFA of a regular black-box behaviour via Angluin's L* (the canonical
    invariant of a regular language: equal languages ⟺ isomorphic minimal DFAs). Other instances are deferred."""
    if isinstance(x, dict) and "lstar" in x:
        import kernel_verdict as KV
        import lstar
        v = lstar.learn(x["lstar"], x.get("alphabet", ("a", "b")), max_states=x.get("max_states", 12),
                        equiv_depth=x.get("equiv_depth"))
        if v.status == "EXACT":
            cert = KV.Cert(KV.EXACT, "complete_invariant", passed=True,
                           check_cost=f"exhaustive bounded equivalence ≤ length {v.verified_depth}",
                           bound=v.verified_depth, detail=v.detail)
            return KV.exact({"n_states": v.n_states, "minimal_dfa": True, "complete": v.complete},
                            "m9_lstar", "Angluin L*", cert)
        return KV.decline(f"M9.lstar: {v.reason} (not regular within budget ⇒ honest DECLINE)", "m9_lstar")
    if isinstance(x, dict) and x and all(isinstance(v, dict) and all(isinstance(e, int) for e in v.values()) for v in x.values()):
        import mathmode.buckingham as B
        return B.buckingham_pi(x)
    if isinstance(x, (list, tuple)) and len(x) == 5:                 # the 5 Weyl scalars [Ψ0..Ψ4] → Petrov type
        import mathmode.petrov as P
        return P.classify(list(x))
    return honest_defer("M9.complete_invariant", "non-(Buckingham/Petrov) complete-invariant instances gated in a later cycle")


MECHANISM = Mechanism(
    num=9, name="complete_invariant", probe=_probe, apply=_apply,
    cert_kinds=("complete_invariant", "isomorphism_decision", "ordinal_rank"),
    contract="requires a classification problem admitting a complete invariant; ensures the invariant DECIDES "
            "equivalence (machine-checked: equal invariant ⟺ equivalent on a battery); grade EXACT/DECISION; "
            "if no complete invariant (turbulence/E₀) → defer to M14 DECLINE",
    composable_with=(2, 14),
)
