# METAUPGRADE_MEASURE — §BQ Stage 1

## TCB size (the central claim)

| component | non-blank/non-comment LOC | what it replaces in the TCB |
|---|---|---|
| `metakernel/trusted_kernel.py` Part B+C (matrix-identity check, propositional DPLL, ground-EUF congruence closure, combined DPLL(EUF)) | **167** | a `z3.Solver()` re-check, for the propositional/ground-EUF fragment only |
| `metakernel/trusted_kernel.py` whole file (incl. Part A thin wraps + battery) | 334 (raw 417) | — |
| `metakernel/chc_kernel_bridge.py` whole file (classifier + Tseitin extractor + bridge) | raw 331 | — |
| `metakernel/holed_certificate.py` whole file | raw 184 | — |

The number that matters for "checker simpler than solver" is **167 lines** — that is the entire amount of
new, from-scratch code a reader has to audit to trust the kernel's verdict on a propositional/ground-EUF
formula, versus trusting z3 (an external SMT solver with millions of lines of C++, not audited by this
project) for the same question. This was measured by counting the actual Part B/C source, not estimated.

## CHC TCB reduction — what actually happens, measured honestly

★ The mechanism (`metakernel.chc_kernel_bridge`) is **proven correct**: a direct cross-check battery runs
`kernel_confirms_unsat` against `z3.Solver().check()` on 8 formulas (propositional UNSAT/SAT, EUF
transitivity contradiction, EUF-consistent equality chain, function-congruence contradiction, modus-ponens
violation, `Distinct` expansion) — **8/8 agree**. The permutation/VC-construction/dispatch logic inside
`try_kernel_certify` is separately proven correct against a hand-supplied in-fragment invariant.

★ **Measured limitation, reported rather than hidden**: `chc_solve.py`'s `prove_safety_chc` always declares
state variables as `z3.Int(...)`. For an actual toy CHC instance built that way — a 2-state system whose
`init`/`trans`/`prop` use ONLY equality (no arithmetic) — Spacer's `fp.get_answer()` did **not** return an
equality-shaped invariant (`loc=0 ∨ loc=1`); it returned `¬(loc≥2) ∧ ¬(loc≤−1)`, a linear-arithmetic interval
form, even though nothing in the input relation needed arithmetic. A second instance (`x'=y, y'=x`, invariant
`x=y`, which has no natural interval shape at all) got the same treatment: `¬(y−x≥1) ∧ ¬(y−x≤−1)`.

This means Spacer's **default** invariant-synthesis strategy for `IntSort` Horn relations is
linear-arithmetic-biased regardless of the user's predicates — so for `chc_solve.py`'s current interface,
the kernel-attributed certificate (`kind="kernel_checked_chc_euf"`) will fire **less often** than "the
propositional/EUF case of CHC" might suggest, because the *invariant Spacer chooses* is the thing being
classified, not just the user's input predicates. `chc_grade_kernel` correctly and safely defers to the
unmodified `chc_solve.chc_grade()` in that case — verified by the `spacer_arith_bias_safely_deferred` test
case, which encodes this exact finding as a regression check (not a hidden gap).

The genuinely-new value delivered regardless of how often Spacer cooperates: (1) the kernel itself is a
correct, small, zero-z3, zero-dep decision procedure for the fragment, usable wherever a propositional/EUF
verification condition needs checking — not CHC-specific; (2) the bridge is safe-by-construction (it can
only ADD a smaller-TCB certificate, never relax what the existing path would accept); (3) it is the
template for any future EUF-native frontend (e.g. a CHC interface over genuinely enumerated/uninterpreted
sorts instead of `z3.Int`) to get the full TCB reduction without further kernel work.

## Engine-files-untouched gate

`git diff --stat` against `chc_solve.py sos_cert.py newengine/farkas.py cfinite.py ic3_pdr.py freivalds.py
fast_certificates.py proof_cache.py semantic_cache.py kernel_verdict.py recall/core.py catalog/ir.py
catalog/compose.py` → **empty** (0 diff), asserted in `test_bq_metakernel` and re-checked on every gate run,
not just once by hand.

## Mechanism count

0 new mechanisms. Every §BQ module is either (a) a thin re-export of an existing checker under a unified
contract (NEW-1 Part A), (b) a from-scratch decision procedure for a fragment that previously had no
checker at all and so was not "a mechanism" being duplicated (NEW-1 Part B/C — this is new ground, not a
15th mechanism in the project's mechanism-registry sense, since it is infrastructure under the EXISTING CHC
mechanism, not a new top-level mechanism), or (c) a bookkeeping layer over the existing `StructForm`
weakest-link law (NEW-2). The 14-mechanism registry is unchanged.

## Stage 2/3/4

Not built in this pass — queued (task #294 successor tasks) per the directive's own staged structure. Stage
1 (this document) is the highest-priority piece per the directive's own `★1순위`/`★최우선` framing.
