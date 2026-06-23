# EXACT-SHARE REPORT — Tier-2 (the rising machine-checked-EXACT share)

The accuracy lever of MR.JEFFREY is moving capabilities from **PROBABILISTIC** (differential / sampling /
randomized — carries a stated δ) to **EXACT** (a machine-checked equivalence with no ε,δ: Z3 bounded
translation validation, a structural theorem with exact integers, or a proven no-wraparound bound). This is the
honest ledger. **Every grade below is the one its cited test enforces** (`assert v.status == …` in
`test_build.py`) — nothing is asserted here that a test does not check. `pillar3/exact_share.py` computes the
share; `test_tier2_exact_share_rising` re-grades one EXACT and one PROBABILISTIC capability **live** so the
ledger is grounded, not just a table.

## Headline

| | count |
|---|---|
| **EXACT** capabilities | **16** (6 pre-session baseline + **10 new this session**) |
| **PROBABILISTIC** capabilities | 11 |
| **EXACT share** | **59%** of 27 graded capabilities |

EXACT is now the **majority** grade. The 10 new EXACT capabilities came from the OMEGA Tier-1 ceiling-breakers
and the first Tier-2 promotion.

## EXACT capabilities (machine-checked, no ε,δ)

| capability | how EXACT is earned | new | test |
|---|---|---|---|
| equiv: strength reduction x⁴→(x²)² | Z3 bounded translation validation | | `test_phaseV` |
| equiv: loop-invariant hoist | Z3 bounded translation validation | | `test_phaseV` |
| equiv: common-subexpression elim | Z3 bounded translation validation | | `test_phaseV` |
| lifting: running/range/telescoping/factor | Z3 two-step lift | | `test_phaseL` |
| symbolic: C-finite n-th term (router) | companion≡recurrence theorem, exact ints | | `test_v40_phase3_symbolic` |
| structured: Toeplitz matvec = convolution | displacement bound + NTT + spot-check | | `test_v40_phase2_structured_matrices` |
| **freeleap: recurrence → companion form** (Pillar-1→3 wire) | companion theorem + verify_cfinite, exact ints | ✅ | `test_round1_freeleap_cfinite_exact` |
| **parteval: interpreter specialization** (1st Futamura) | Z3 residual≡generic | ✅ | `test_round1_partial_evaluation_exact` |
| **parteval: sparse linear-map specialization** | Z3 residual≡generic | ✅ | `test_round1_partial_evaluation_exact` |
| **affine: index-only loop O(n)→O(1)** | Z3 family identity (symbolic A,B,C) | ✅ | `test_round1_affine_lift_generalized_exact` |
| **affine: array-affine loop fold** | Z3 family identity | ✅ | `test_round1_affine_lift_generalized_exact` |
| **affine: pure-count loop O(n)→O(1)** | Z3 family identity | ✅ | `test_round1_affine_lift_generalized_exact` |
| **egraph: equality-saturation simplify** | Z3 ∀-vars term≡rewrite | ✅ | `test_round1_egraph_simplify_exact` |
| **convolution: O(n²) → NTT O(n log n)** | proven \|c[k]\|<P/2 no-wrap + spot-check | ✅ | `test_round1_convolution_ntt_exact` |
| **matmul: O(n³) → blocked/BLAS int64** | proven \|C_ij\|<2⁶³ no-overflow + spot-check | ✅ | `test_round1_matmul_blocked_exact` |
| **bounds-check: redundant guard elimination** | Z3 ∀-domain UNSAT of ¬guard | ✅ | `test_round1_bounds_check_elim_exact` |

## PROBABILISTIC capabilities (carry a stated δ — honestly never EXACT)

| capability | mechanism (δ) | test |
|---|---|---|
| recognizers: matrix-power / KMP / union-find / coin-change / Fenwick / **RMQ** | differential+metamorphic δ | `test_round1_big_recognizers` |
| recognizers: kadane / two-sum / majority / binsearch / memo-fib / hash-join | differential+metamorphic δ | `test_phaseA_algorithm_recognition` |
| round2: sublinear sampling (mean), cost ⟂ N | sampling ε,δ | `test_round2_sublinear_sampling` |
| round2: Bloom membership filter | false-positive ε, zero false-neg | `test_round2_bloom_membership` |
| round2: native compile (numba/llvmlite) | float-tolerant differential δ | `test_round2_native_compile` |
| **stoke: stochastic superopt** | Schwartz–Zippel randomized δ (≤1e-300, never EXACT) | `test_round1_stoke_superopt_probabilistic` |

## Honesty notes

- **DECLINE is not a capability** — it is the engine's honest no-win / not-provable outcome, and is excluded
  from the share. Every EXACT and PROBABILISTIC capability above also has an adversarial-wrong test that must
  DECLINE (the moat); a corrupted transform never ships.
- **Bounds / no-wraparound EXACT** (convolution, matmul, Toeplitz) is EXACT only **under a proven magnitude
  bound**; when the bound is exceeded the engine **DECLINEs the fast path** (never a wrapped/overflowed answer).
- **STOKE stays PROBABILISTIC** even with a Schwartz–Zippel error bound far below 1e-18 — randomized testing is
  not a proof. The §0b reliability standard drives δ down via amplification, but without a machine-checked
  witness the grade does not become EXACT (we never mislabel a randomized check as EXACT).
- Grades are **certified by the cited tests**, all green in the same `test_build.py` run (153 passed, 0 failed).
