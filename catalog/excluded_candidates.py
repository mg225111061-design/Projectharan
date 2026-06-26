"""
POST-CONSOLIDATION PHASE 3 — TIER-3 (constant-factor → region-3 acceleration) + TIER-4 (excluded, with reasons).
================================================================================================================
The honest tail of the candidate ledger. After the admitted mechanism (k-regular M22) and the faces (Tier-1/2
demotions), the rest are recorded TRUTHFULLY, never silently dropped:

  • TIER-3 — CONSTANT-FACTOR: real speedups whose ASYMPTOTICS ARE UNCHANGED. They are NOT folds; they route to the
    region-3 acceleration stack (catalog/accel.py) and are tagged constant-factor. Reporting them as folds would be a
    lie (the two speeds are never mixed: asymptotic fold vs constant-factor region-3).
  • TIER-4 — EXCLUDED: candidates that do NOT clear the gates, each with the EXACT reason (already a face of an
    existing mechanism / not a per-instance fold / inherently probabilistic / an impossible-core hardness assumption
    / reducible-but-deferred). Recording the reason is the honesty: "we looked, here is why it is not in."
"""
from __future__ import annotations

from typing import Dict

# the region-3 acceleration layers (catalog/accel.py) a constant-factor candidate maps onto.
TIER3_CONSTANT_FACTOR: Dict[str, Dict[str, str]] = {
    "polyhedral_affine": {
        "accel_layer": "relayout_aos_soa / parallelize_elementwise / superoptimize",
        "reason": "polyhedral/affine loop transforms (tiling, skewing, fusion, interchange) improve locality and "
                  "parallelism by a CONSTANT FACTOR; the loop nest's asymptotic complexity is UNCHANGED. Region-3.",
    },
    "mtbdd": {
        "accel_layer": "relayout_aos_soa (compact decision-diagram representation)",
        "reason": "multi-terminal BDDs give a compact, constant-factor-faster representation of a function/matrix; "
                  "the represented computation's asymptotics are unchanged (and the BDD can blow up). Region-3.",
    },
    "deforestation_optics": {
        "accel_layer": "superoptimize / vectorize (intermediate-structure elimination, pass fusion)",
        "reason": "deforestation / profunctor-optics fusion removes intermediate data structures and traversal passes "
                  "— a constant-factor win (fewer allocations/passes); the asymptotic work is UNCHANGED. Region-3.",
    },
}

# excluded candidates, each with the EXACT reason it does not enter the fold set.
TIER4_EXCLUDED: Dict[str, str] = {
    "zx_calculus": "already a FACE of M8 (confluent normal form / e-graph): the engine routes zx_equiv/zx_simplify to "
                   "M8 — no new certificate kind.",
    "crypto_accumulator": "an IMPOSSIBLE-CORE hardness assumption (one-way / collision-resistant): 'folding' it would "
                          "mean breaking the primitive. Not structure — a security assumption. DECLINE-by-design.",
    "graph_delta": "incremental/dynamic-graph maintenance is a CONSTANT-FACTOR-per-update speedup, not an asymptotic "
                   "fold; its fixpoint maintenance reduces to M13. Not a new mechanism.",
    "smt_grammar": "grammar-constrained SMT / syntax-guided synthesis is already covered by M2 (SMT decision) + the "
                   "lift/CEGIS front-end — no new certificate kind.",
    "chc_lattice": "Constrained Horn Clauses over an abstract lattice is already M13 (CHC-Spacer least-fixpoint is "
                   "wired in compose.plan) — same fixpoint kind.",
    "linearizability": "a concurrent-correctness VERIFICATION property (Group B), proved via a refinement/simulation "
                       "witness (M13 safety lineage, the MPST face); not a chaos→structure fold.",
    "game_semantics": "the full-abstraction content is M9's kind (complete invariant / full abstraction); the model "
                      "itself is denotational, not a per-instance constructive fold.",
    "parametricity": "free theorems are a META-theorem over polymorphic types (a logical-relations argument), not a "
                     "per-instance fold of a concrete input.",
    "light_linear_logic": "a polynomial-time-bounded proof system — a complexity-VERIFICATION discipline (the AARA "
                          "Group-B lineage), not a fold.",
    "guarded_recursion": "a productivity/termination discipline for coinduction; its content reduces to M13 + "
                         "ordinal-descent termination — no new kind.",
    "nominal_sets": "a foundational framework for names/binding (Fraenkel–Mostowski); infrastructure, not a "
                    "per-instance fold mechanism.",
    "forest_algebra": "regular tree/forest languages = TREE AUTOMATA, a complete-invariant canonical form — a FACE of "
                      "M9 (same kind as the SFA face), not a new mechanism.",
    "graded_effects": "graded monads / effect systems are a TYPE-SYSTEM structure; not a per-instance constructive "
                      "fold.",
    "markov_cutoff": "the mixing-time cutoff phenomenon is an inherently ASYMPTOTIC-PROBABILISTIC statement; at best "
                     "PROBABILISTIC (never EXACT), and it reduces to M6 (renormalize) spectral-gap analysis.",
    "point_process": "spatial point-process statistics are inherently PROBABILISTIC (δ-bounded estimates), never an "
                     "EXACT fold — the EXACT ledger stays residual-0-only.",
    "cluster_algebras": "the Laurent phenomenon is a deep algebraic structure; a clean per-instance certificate kind "
                        "is not yet isolated — recorded as reducible-to-M2/M13-DEFERRED, not declared.",
    "q_holonomic": "q-holonomic sequences are the q-analogue of holonomic — a FACE of M13 (q-Zeilberger creative "
                   "telescoping); the implementation is DEFERRED, the kind is M13's.",
    "somos": "Somos / bilinear (Laurent-phenomenon) recurrences are a NONLINEAR recurrence — covered by gap_recur "
             "(P1 nonlinear-recurrence detection); a FACE of M11/gap_recur, not a new mechanism.",
    "umbral_calculus": "Sheffer/umbral sequences are polynomial sequences with a closed form — a FACE of M13 "
                       "(polynomial closed form), not a new kind.",
}


def disposition(name: str) -> Dict[str, str]:
    if name in TIER3_CONSTANT_FACTOR:
        return {"tier": "3", "disposition": "constant-factor → region-3 acceleration", **TIER3_CONSTANT_FACTOR[name]}
    if name in TIER4_EXCLUDED:
        return {"tier": "4", "disposition": "excluded", "reason": TIER4_EXCLUDED[name]}
    return {"tier": "?", "disposition": "unknown — not on the ledger"}


def report() -> dict:
    return {
        "tier3_constant_factor": list(TIER3_CONSTANT_FACTOR),
        "tier3_count": len(TIER3_CONSTANT_FACTOR),
        "tier3_note": "asymptotics UNCHANGED — routed to the region-3 acceleration stack, tagged constant-factor; "
                      "NEVER reported as a fold (the two speeds are never mixed)",
        "tier4_excluded": list(TIER4_EXCLUDED),
        "tier4_count": len(TIER4_EXCLUDED),
        "tier4_note": "each excluded with an exact reason (already-a-face / not-a-fold / probabilistic / "
                      "impossible-core / reducible-deferred) — recorded, never silently dropped",
        "one_line": "the honest tail: constant-factor speedups routed to region-3 (not folds), and excluded "
                    "candidates each filed with the exact reason — coverage is widened only where a NEW kind appears",
    }
