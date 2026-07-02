"""
§Y — ALTERNATIVE-LENS FOLD: see the structure the 22 mechanisms cannot, on axes orthogonal to standard-field linearity.
================================================================================================================
Three genuinely-new LENSES, each measuring code on an axis the 22 don't:
  • LENS 1 — Tropical / idempotent semiring (max-plus / min-plus): max/min/+ loops are NOT linear over a field but ARE
    linear over (ℝ∪{-∞}, ⊕=max, ⊗=+) — foldable by tropical matrix power / maximum-cycle-mean. A new ALGEBRA (a⊕a=a).
  • LENS 4 — Bounded lattice-height fixpoint (Knaster–Tarski): a monotone update over a finite-height lattice reaches
    its fixpoint in ≤ h steps, so n≫h folds O(n)→O(h). The ORDER-structure lens.
  • LENS 5 — Exact semantic quotient via Galois connection: a computation EXACTLY encoded by a small finite domain
    cycles within |D| states, folding O(n)→O(|D|)≈O(1). The semantic-EQUIVALENCE-CLASS lens.

★ None folds the truly random — the pigeonhole wall is absolute. Each finds structure that EXISTS but that our current
algebraic lenses miss. Every lens is z3-gated; precision stays exactly 1.0; a false fold FAILS the build.

★ INHERITED HONESTY SPINE (from §X): a fold counts toward the fold rate ONLY when actually APPLIED at a real callsite
(issued≠applied); the fold rate is reported SEPARATELY from the measured speedup (fold-rate≠speedup); the per-lens
contribution is measured on the SAME backend corpus the 5.7% came from — no inflated frequency. ★ Tropical's special
caveat: z3 proves over ℝ but code runs in IEEE-754 float — the sound fold is restricted to integer/rational (exact) or
FPSort-proved; a real-only float fold is DECLINED, the arithmetic model named in the certificate.

NO gratuitous new certificate kind — each lens issues the existing EXACT verdict (tropical's note records the semiring).
Modules: tropical_fold · lattice_fold · galois_fold · altlens_report. Engine zero-dep; never imported by test_build.
"""
