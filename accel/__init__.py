"""
VERIFIED PRODUCT-ACCELERATION ENGINE (A/B/C/D to the measured limit). §L.
=========================================================================
The fold engine collapses the ~1–3% of code with asymptotic structure. THIS engine goes after the other ~95% — the
code whose wall-clock is I/O wait, serialization, data-structure work, and allocation — through ONE disciplined
pipeline: PROFILE first (Amdahl), the LLM/detector PROPOSES an acceleration, z3 or an exact oracle PROVES it
semantics-preserving, only the PROVED change is APPLIED, and the WHOLE-PROGRAM wall-clock is MEASURED. Precision = 1.0
means zero unsafe accelerations are ever applied — proved on an adversarial battery where the "fast" version is
deliberately wrong. Three clocks never mix: A (proposal), B (verification), C (achieved runtime). The headline is
always a measured X× on named hot paths with an Amdahl breakdown and an irreducible-I/O floor — never "10–20× on
everything"; the limit is the measured limit, never infinity.

Modules: pipeline (orchestrator) · verified_io (A) · verified_parallel (B) · verified_algo (C) · verified_serde (D)
· limit_pass · acceleration_report · maximal (A/B/C/D to the limit: transitive purity, nested batching, prefetch/
overlap, compose-to-fixpoint with an end-to-end equivalence proof) · stress_550 (the 550-case precision stress test:
500 mixed + 50 impossible-core, every unstructured case MUST decline, precision is the build gate, never 550/550).
Zero external deps (z3 + stdlib + numpy + grandfathered sympy). Never imported by test_build.
"""
