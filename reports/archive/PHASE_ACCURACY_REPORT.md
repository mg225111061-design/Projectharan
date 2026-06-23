# PHASE ACCURACY REPORT (§B)

The moat is **proven** acceleration. This campaign drove the EXACT fraction up by widening the Z3 prover and
keeping everything else honestly PROBABILISTIC/DECLINE. Grade = OUTPUT confidence (input + verifier), enforced
by the ADT (raises on a fake pass or an EXACT carrying δ).

## EXACT classes now machine-checked (Z3 bounded translation validation, no Lean/Coq)
**Verified lifting** (`lifting.py`, 7) — each two-step proven (spec≡original ∧ optimized≡spec), measured win,
ratio ≤ ceiling, wrong → Z3 counterexample → DECLINE:
running-sum, weighted-running-sum, range-sum-query, difference-array, telescoping, factor-constant, loop-fusion.
**Equivalence transforms** (`equiv_transforms.py`, 3): strength-reduction (x⁴→x·x·x·x), loop-invariant hoisting,
CSE — proven ⇒ EXACT **with a measured win** (a proven-but-speed-neutral transform DECLINEs — no "EXACT 1.0×").

Coverage vs the directive's list: **distributive/factoring** ✓ (factor-constant), **strength reduction** ✓,
**loop-invariant hoisting** ✓, **prefix-sum / difference-array** ✓, **telescoping/closed-form** ✓,
**bounded loop equivalences** ✓ (all lifts are bounded symbolic). **Reassociation**: provable by `equiv.prove_equiv`
but speed-neutral ⇒ would DECLINE on the win-floor (kept honest, not shipped as "EXACT 1.0×"). **Memoization of
provably-pure functions**: the memoised-DP path is graded PROBABILISTIC (control flow ⇒ Z3 *unknown*; a Z3
purity proof for arbitrary functions is **UNVERIFIED [tooling]** in this Python-Z3 harness — stated, not faked).
**Data-structure swap (set/dict ≡ list membership)**: shipped as a recognizer/detector graded PROBABILISTIC —
the refinement-relation EXACT proof is **UNVERIFIED [tooling]** here because `x in [z3-symbol…]` can't execute
symbolically; honest caveat, never mislabeled EXACT.

## Kept PROBABILISTIC (honest — Z3 returns *unknown* on the branching), never mislabeled EXACT
Recognizers with control flow (`algorithms.py`): two-sum (hash), majority (Boyer-Moore), binary-search,
Kadane, hash-join, memoized-DP. Each: differential over a strong evidence set + metamorphic + coherent
measurement ⇒ PROBABILISTIC with a stated δ; adversarial wrong ⇒ DECLINE. **Promotion to EXACT was attempted
and declined honestly**: the equivalence predicates are nonlinear/branching ⇒ Z3 `unknown` ⇒ they remain
PROBABILISTIC (Rule 3).

## Stronger input generation (`inputgen.py`)
Boundary/edge + property-based + **float specials (NaN/inf/−0.0/tiny/huge)** + Z3-guided branch coverage; δ
from real n (3/n), shrinks as n grows. Verified: the enlarged set catches an empty-list bug a 3-sample misses,
and a drop-non-finite bug a finite-only sample misses. [test_phaseI_input_generation]

## Metamorphic + cross-checking (`metamorphic.py`)
Relations per family (sort: output-sorted/idempotent/permutation-invariant/multiset; sum: order-invariant up to
FP tol) + cross-check two independent implementations. Verified: a dedup-sort PASSES differential on distinct
inputs but the multiset relation REFUTES it on duplicates ⇒ DECLINE. The gate only ever downgrades to DECLINE —
never manufactures a win. [test_phaseM_metamorphic_crosscheck]

## Moat battery (`moat.py`)
**15/15 adversarial wrong swaps REFUTED, zero false-accepts** — 11 by Z3 counterexample (arithmetic),
4 by differential (control flow): off-by-ones, sign-flips, dropped terms, same-index reuse, no-verify,
negative-only bugs. [test_moat_battery]

## EXACT : PROBABILISTIC : DECLINE distribution (winning-fix classes this campaign)
- **EXACT: 10** (7 lifts + 3 transforms) — all Z3 machine-checked.
- **PROBABILISTIC: 7** (6 control-flow recognizers + SIMD offload) — δ stated, honestly not EXACT.
- **DECLINE: every wrong swap** (15-strong moat) + non-dominant offload + GPU [UNVERIFIED] + proven-but-no-win.

**EXACT-share rise:** the pre-campaign engine machine-checked ~2 EXACT classes (canonical n_plus_1 + algo_replace
via Z3); it now machine-checks **10** EXACT classes (a 5× increase in proven-EXACT coverage), with the
control-flow wins kept honestly PROBABILISTIC rather than inflated. Nothing differential-only is labeled EXACT.
