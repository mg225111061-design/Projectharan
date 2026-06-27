"""
§AB — ALL FOLD-RATE AXES: widen what EARNS the right to be counted, and what we measure — honestly, by theorem.
================================================================================================================
Prior directives attacked recognition and extraction. §AB attacks the two never touched: what counts as a fold, and
what unit we measure. The headline is a DECOMPOSITION — four distinct categories, four numbers, NEVER one inflated total.

★ THE LINE THAT KEEPS US NOT AN LLM (the identity): an LLM also approximates. A plain "usually close" approximation would
make us the thing we replace. OURS carries a z3-/interval-PROVEN worst-case bound holding on EVERY input, on the first run
and the 10^16-th — `∀ inputs. |folded − original| ≤ ε`, a THEOREM, never a sample. Anything justified by sampling /
averaging / empirical testing / "usually" is REJECTED. Our ε is a theorem; the bound is universal.

  • AXIS 1 — CERTIFIED Approximate Fold (the largest, identity-critical): float code that DECLINEs under EXACT folds to a
    closed form within a UNIVERSALLY-PROVEN ε (sound interval/affine roundoff propagation over the whole input domain).
    ★ REUSES the existing APPROX_FOLD grade (`disposition.py` / `approx_cert.py`, never-exact per R3.5) and ADDS the new
    interval-certified-ε method (the existing kinds are asymptotic-with-error for series, and epsilon-delta which is
    SAMPLED ⇒ that is AXIS 2's probabilistic territory, never AXIS 1). The shared KV ADT is left UNTOUCHED (273 safe).
  • AXIS 2 — Probabilistic Fold in earnest: a fold correct w.p. ≥ 1−2⁻ᵏ via a DERIVED bound (Schwartz-Zippel deg/|field|,
    Freivalds 2⁻ᵏ). REUSES `fast_certificates.py` + KV.PROBABILISTIC. Distinct from AXIS 1 — the randomness is in the
    CHECK (over the algorithm's coins), not an assumption about the input; the bound is derived, never empirical.
  • AXIS 3 — Fold-Unit Redefinition: structure folds at the expression / function / call-graph-region unit, not only the
    loop. Changing the unit changes the DENOMINATOR — loop/expr/func/region fold rates reported as DISTINCT numbers, the
    unit always stated, never merged.
  • AXIS 4 — Fold Bypass: for a finite/small/deterministic input space, precompute the whole map once, O(1) lookup. NOT a
    fold — raises VALUE/throughput, reported entirely separately, cold-vs-warm + the input-space bound stated.

★ Each grade is its own number (four categories, never summed); every ε and every 2⁻ᵏ stated on its certificate; EXACT
stays integer/rational, precision 1.0, undiluted. LLM-free, zero-dep (`forbidden_present == []`), pigeonhole wall stands.
Never imported by test_build. Modules: approx_fold · probabilistic_fold · fold_units · bypass · foldaxes_report.
"""
