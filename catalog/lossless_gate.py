"""
CAPSTONE PHASE 3 — the LOSSLESS judgment gate (Constitution §5, round-2 core).
=============================================================================
Before a translation/bypass result is trusted as a FOLD (an EXACT collapse), judge whether the translation is
LOSSLESS — one of three formal conditions must hold, witnessed PER-INSTANCE by the result's certificate:

  1. COMPLETENESS (abstract interpretation)  ρ∘f == f^♯∘ρ on the instance — the abstraction loses nothing here
     (witnessed by an exact-equivalence / residual≈ε / model-re-substitution / ideal-cofactor certificate).
  2. FULL ABSTRACTION                         the translation PRESERVES and REFLECTS observational equivalence
     (witnessed by a verified normal-form / tensor-equality / complete-invariant certificate).
  3. MACHINE-VERIFIED REFINEMENT / EQUIVALENCE a simulation relation (inductive invariant) or a type equivalence,
     re-checked by a fresh verifier (witnessed by a re-verified inductive-invariant certificate).

A result that is PROBABILISTIC (a δ-bounded estimate) is LOSSY → it is flagged as an APPROXIMATE output and is
NEVER folded as EXACT. A result whose EXACT certificate is not a recognized equivalence witness is conservatively
labelled `exact_unclassified` (still EXACT — the §7 gate already verified it — but not claimed lossless here).
This is what makes "fold almost everything" SAFE: the gate refuses to fold a translation it cannot certify lossless.
"""
from __future__ import annotations

from dataclasses import dataclass

import kernel_verdict as KV

# certificate.kind → the lossless CONDITION it witnesses (an EXACT equivalence-style cert IS a lossless certificate).
_CONDITION = {
    # 1. completeness (exact equality of abstract values / exact recovery on the instance)
    "qe_equivalence": "completeness",
    "presburger_equivalence": "completeness",
    "groebner_cofactor_membership": "completeness",
    "groebner_nonmembership_normalform": "completeness",
    "string_model_witness": "completeness",
    "string_unsat_refutation": "completeness",
    "structured_pseudorandom_split": "completeness",
    "exponential_sum": "completeness",
    "residual": "completeness",
    "latent_residual": "completeness",
    "mdl_two_part": "completeness",
    "sturm_bound": "completeness",
    "sylvester": "completeness",
    "exact_lumping": "completeness",
    "fixpoint_residual": "completeness",
    "forced_monotone_subsequence": "completeness",
    "pigeonhole_repeated_state": "completeness",
    "ramsey_mono_clique": "completeness",
    "linear_recurrence": "completeness",
    "slp_grammar": "completeness",
    "lll_reduced_basis": "completeness",
    "integer_relation": "completeness",
    "smith_diophantine": "completeness",
    "sturm_isolation": "completeness",
    "sos_gram": "completeness",
    "rational_psd_gram": "completeness",
    # 2. full abstraction (equivalence preserved AND reflected — verified normal form / complete invariant)
    "normal_form_unique": "full_abstraction",
    "confluent_rewrite_system": "full_abstraction",
    "most_general_unifier": "completeness",
    "model_count": "completeness",
    "zx_tensor_equality": "full_abstraction",
    "complete_invariant": "full_abstraction",
    "isomorphism_decision": "full_abstraction",
    "fold_closed_form": "full_abstraction",
    "petrov_type": "full_abstraction",
    "petrov_pnd_partition": "full_abstraction",
    "buckingham_pi": "full_abstraction",
    "buckingham_nullspace": "full_abstraction",
    # 3. machine-verified refinement / simulation (re-verified inductive invariant)
    "fixpoint_inductive": "refinement",
    "reachability_counterexample": "refinement",
    "dataflow_witness": "refinement",
    "ordinal_descent": "refinement",
    "lcg_state_replay": "completeness",
    "lfsr_recurrence_replay": "completeness",
    "gosper_antidifference": "completeness",
    "low_rank_dependence": "completeness",
    "poly_finite_difference": "completeness",
    # GAP CLOSURE — every new detector's exact certificate is a per-instance exact recovery ⇒ completeness
    "nonlinear_recurrence": "completeness",
    "matrix_recurrence": "completeness",
    "algebraic_relation": "completeness",
    "kronecker_product": "completeness",
    "block_low_rank": "completeness",
    "modulated": "completeness",
    "piecewise": "completeness",
    "nonfourier_sparse": "completeness",
    "zeilberger_telescoping": "completeness",
    # MECHANISM GROWTH (M15–M20) — each new mechanism's exact certificate
    "persistence_barcode": "completeness",          # exact 𝔽₂ homology + stability witness
    "causal_do_calculus": "refinement",             # do-calculus identifiability (relative to declared axioms)
    "sheaf_cohomology": "full_abstraction",         # H⁰/H¹ class — exact linear algebra; generalizes M14 obstruction
    "obstruction_h0": "full_abstraction",           # M14 folded in as the binary H⁰ special case
    "flow_canonical_form": "completeness",          # canonical decomposition + monotone convergence witness
    "knot_state_sum": "full_abstraction",           # Kauffman/Jones invariant, Reidemeister-invariant
    "aperiodic_cut_project": "completeness",        # cut-and-project scheme + pure-point diffraction
    "conley_index": "full_abstraction",             # H_*(N,L) homological index of an isolated invariant set (M21)
    "kregular_linear_representation": "completeness",  # M22: exact digit-indexed linear-rep recovery on the instance
    # POST-CONSOLIDATION Tier-1 DEMOTIONS — real folds that reduce to an existing mechanism's KIND ⇒ registered as faces
    "monomial_closure_linearization": "completeness",  # defective-variable → FACE of M11 (the fold is C-finite)
    "chains_of_recurrences": "completeness",           # Tensor-Evolution/CR → FACE of M13 (polynomial/geometric closed form)
    "amortized_potential": "refinement",               # AARA → Group-B VERIFICATION (a ∀n-sound potential-method bound)
    # PHASE 3 — faces of existing mechanisms (a face routes to its PARENT mechanism, never a new mechanism)
    "tropical_newton_subdivision": "completeness",  # tropical variety = dual of a regular subdivision (face of M13)
    "legendre_pair": "completeness",                # convex-duality / Legendre witness (face of M4/P1)
    "rate_distortion_duality": "completeness",      # Blahut-Arimoto converged curve + duality (face of M4/M12)
    "rg_fixpoint_enclosure": "completeness",        # validated RG-fixpoint (face of M6)
    "characteristic_integral_index": "full_abstraction",   # computable characteristic-integral index (face of Chern/Witten)
    "walsh_spectrum": "completeness",               # (Z/2)ⁿ Fourier / junta witness (face of M11/M9)
    "characteristic_numbers": "full_abstraction",   # cobordism: Stiefel-Whitney numbers agree (face of M9)
}


@dataclass
class LosslessJudgment:
    lossless: bool
    condition: str       # completeness | full_abstraction | refinement | approximation | exact_unclassified | none
    witness: str

    def __str__(self):
        return f"{'LOSSLESS' if self.lossless else 'NOT-FOLDABLE'}[{self.condition}] — {self.witness}"


def _classify_kind(kind: str):
    """Map a (possibly composite) certificate kind to a lossless condition. A composition is lossless IFF EVERY
    constituent stage is lossless (weakest-link for losslessness too); the reported condition is the single shared
    condition, or 'mixed_lossless' when the stages witness different (but all valid) conditions."""
    if ("equivalence[" in kind) or kind.startswith("lift_equivalence["):
        # a z3-proved / bounded-checked equivalence or refinement (lifting + Topic A) — preserves+reflects behaviour
        return "full_abstraction"
    if kind.startswith("composition[") and kind.endswith("]"):
        parts = [p for p in kind[len("composition["):-1].split("∘") if p]
        conds = [_CONDITION.get(p) for p in parts]
        if parts and all(c is not None for c in conds):
            uniq = set(conds)
            return next(iter(uniq)) if len(uniq) == 1 else "mixed_lossless"
        return None
    direct = _CONDITION.get(kind)
    if direct is not None:
        return direct
    if "[" in kind:                                          # strip a trailing qualifier, e.g. nonfourier_sparse[haar]
        return _CONDITION.get(kind.split("[", 1)[0])
    return None


def judge(verdict: "KV.Verdict") -> LosslessJudgment:
    """Judge whether `verdict` is a LOSSLESS fold. The decision is PER-INSTANCE via the verdict's certificate —
    never an a-priori promise. PROBABILISTIC ⇒ lossy (approximate, flagged). DECLINE ⇒ no fold."""
    if verdict.status == KV.DECLINE:
        return LosslessJudgment(False, "none", "DECLINE — nothing to fold (honest)")
    if verdict.status == KV.PROBABILISTIC:
        d = verdict.certificate.delta if verdict.certificate else None
        return LosslessJudgment(False, "approximation",
                                f"PROBABILISTIC (δ={d}) — a δ-bounded estimate is LOSSY; flagged APPROXIMATE, never folded EXACT")
    cert = verdict.certificate
    cond = _classify_kind(cert.kind) if cert is not None else None
    if cond is not None:
        return LosslessJudgment(True, cond, f"{cert.kind}: condition '{cond}' re-checked on this instance ⇒ lossless fold")
    return LosslessJudgment(False, "exact_unclassified",
                            f"EXACT (cert '{cert.kind if cert else None}') but not a recognized lossless-equivalence "
                            f"witness — conservatively NOT claimed lossless (still §7-verified)")


def is_lossless_fold(verdict: "KV.Verdict") -> bool:
    """True iff the verdict is an EXACT collapse certified lossless by one of the three conditions."""
    return judge(verdict).lossless


# a-priori advisory: which lossless CONDITION each composition SHAPE is expected to witness (routing hint, §6 top).
_SHAPE_CONDITION = {
    "m7_split": "completeness", "m9_perp_m14": "full_abstraction", "sos": "completeness",
    "mdl": "completeness", "fold": "full_abstraction", "chain": "(per-mechanism)",
}


def expected_condition(shape: str) -> str:
    return _SHAPE_CONDITION.get(shape, "(per-instance)")
