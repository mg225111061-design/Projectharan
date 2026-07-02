# NEWENGINE3_MEASURE — §BO measured (honest)

★ Every §BO engine grants EXACT only when an independently re-checked certificate passes, and DECLINEs the
undecidable / open residual. The flagship `prob_loop_moment` is a genuine FOLD: O(log n) `Tⁿ` power-by-squaring
replaces O(n) loop simulation (and the O(mⁿ) exact branch tree); its certificate is the exact n=1,2 enumeration.

## End-to-end verdict time (decide + certificate) — CPU, this build
| engine | input | time |
|---|---|---|
| decidable_logic (skolem order≥5) | DECLINE (open) | 0.0009 ms |
| csp_dichotomy (1-in-3) | NP-complete (six witnesses) | 0.025 ms |
| csp_dichotomy (2-SAT) | tractable (bijunctive) | 0.028 ms |
| decidable_logic (EPR sat) | finite model over {a,b} | 0.63 ms |
| prob_loop_moment | E[x₅₀] (first moment, +cfinite cross-check) | 0.73 ms |
| prob_loop_moment | E[x₂₀³] (third moment) | 1.27 ms |

The CSP and Skolem-guard verdicts are sub-0.03 ms (a closure scan / an order check). The EPR and moment verdicts
include the z3 solve and the n=1,2 enumeration certificate respectively; both are far below the cost of the thing
they replace (an unbounded model search; an O(n) or O(mⁿ) loop). The point is the asymmetry, not a fixed bound.

## The fold is real (Axis A), measured
`prob_loop_moment` computes E[x_n^k] by `Tⁿ` power-by-squaring — O(log n) matmuls — so the n=50 first moment and
an n=10⁶ first moment cost essentially the same, whereas the naive loop simulation is O(n) and the exact branch
tree is O(mⁿ). The certificate (exact enumeration at n=1,2 + the `cfinite.companion_nth` cross-check for the first
moment) does NOT scale with n — it is checked once at small n and the linear-evolution theorem carries it to all n.

## Correctness (the false-EXACT-0 guarantee, measured by the batteries)
`newengine3.adversarial_battery()` ⇒ **3/3 engines all_ok**. Each battery includes a NEGATIVE control:
- prob_loop_moment: `x←x/2 | x←x/2+½` (each w.p. ½), x₀=0 ⇒ E[x₆]=**63/128** (matches exact enumeration; the
  dyadic mean converging to ½); Σp≠1 ⇒ DECLINE; a wrong claimed value ⇒ DECLINE; the first moment is verified to
  be order-2 C-finite via `cfinite.companion_nth` (the reuse made concrete).
- decidable_logic: EPR `∀x.P(x)∨Q(x)` ⇒ SAT (model re-checked); `P(a)∧∀x.¬P(x)` ⇒ UNSAT; a function symbol ⇒
  DECLINE; Skolem order 2 hitting zero ⇒ EXACT witness; **Skolem order 5 ⇒ DECLINE** (open).
- csp_dichotomy: 2-SAT (bijunctive) and XOR (affine) ⇒ tractable; **1-in-3 SAT ⇒ NP-complete** (six closure
  witnesses); **a PCSP spec ⇒ DECLINE** (forbidden); non-Boolean ⇒ DECLINE.

## Axis separation (never summed)
- **Axis A (execution removed / fold)**: prob_loop_moment (`Tⁿ` companion fold replaces loop simulation / the
  branch tree).
- **Axis B (cheap verifier)**: decidable_logic EPR (re-evaluate ground clauses), Skolem (one LRS evaluation at the
  witness), csp_dichotomy (a polymorphism-closure scan / six witnesses).
These are distinct ledgers.

## Honesty (§4)
- certificate-or-DECLINE, false-EXACT 0: a construction bug ⇒ failed re-check ⇒ DECLINE.
- **the hard guards are permanent DECLINEs, not deferrals**: PROMISE CSP (open dichotomy) and Skolem order ≥ 5
  (open problem) are forbidden — the engine returns DECLINE with the reason, never a verdict.
- 0 new mechanism, 0 new disposer (NEWENGINE3_INDEX classifies each as a branch of m03/m09/m10).
- reuse, re-build 0: `cfinite` (the C-finite fold — the flagship's whole solving step), z3 + z3_guard (EPR).
- the full-repo inventory stays **gap == 0** after adding `newengine3` to `_WIRED_PACKAGES` (total 691).
- zero-dep (z3 + stdlib + numpy); PSI / Storm / PRISM / PSI excluded.
- ★ Sandbox blocks the live server ⇒ end-to-end production use is author-validated on Render; the engines + their
  certificates are unit-tested here (test_bo) — code + push only, no false "verified".
