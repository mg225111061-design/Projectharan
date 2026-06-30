# NEWENGINE3_INDEX — §BO 3-domain new engine branches (certificate-or-DECLINE; decidable-boundary guards)

★ Three domains — **probabilistic-program exact analysis**, **decidable first-order/temporal logic fragments**,
**CSP dichotomy**. Each is a new *recognition branch* of one of the 14 mechanisms (**0 new mechanism**, **0 new
disposer**); every EXACT rides an INDEPENDENTLY re-checked certificate ⇒ a construction bug ⇒ failed cert ⇒
DECLINE, never a false-EXACT. The undecidable / open residual DECLINEs by design.

## The flagship (max-ROI reuse): prob_loop_moment
The research's headline finding — **the moments of a prob-solvable affine loop are C-finite recurrences**, so the
engine **reuses the existing `cfinite` companion-matrix solver almost verbatim**. A loop applying one of finitely
many affine updates `x ← aᵢ·x + bᵢ` with rational probability `pᵢ` has a moment vector
`M_n = (E[x_n^0], …, E[x_n^k])` evolving as `M_n = Tⁿ·M₀` for a fixed lower-triangular `T` — the companion fold
(power-by-squaring ⇒ O(log n), not O(n) simulation, never the O(mⁿ) branch tree). Net-new is **only** the
recognition + expectation semantics + building `T`; the solving is the engine we already have.

## Reuse (re-build 0)
`cfinite` (companion_nth / verify_cfinite — the C-finite fold, reused for the first moment and generalized by `T`)
· `z3` + `z3_guard` (EPR decision) · the GF(2)/linear-algebra idiom (affine CSP) · `kernel_verdict` (grades every
output). zero-dep (z3 + stdlib + numpy).

## Delivered this build (3 engines) — each a branch of an existing mechanism, with its decidable-boundary guard
| engine (newengine3/) | domain | gem | → mechanism | Axis | certificate (re-checked) | ★ guard (DECLINE) |
|---|---|---|---|---|---|---|
| **prob_loop_moment** | prob programs | moments of a prob-solvable loop are C-finite (`Tⁿ` fold) | closed-form **m10** + C-finite fold | A | exact branch enumeration at n=1,2 == `Tⁿ M₀`; first moment via `cfinite.companion_nth` | non-affine / Σp≠1 ⇒ DECLINE ("unsolvable loop") |
| **decidable_logic** (epr) | decidable FO | EPR/Bernays–Schönfinkel finite-model decision | guess-and-certify **m03** | B | SAT: re-eval every ground clause; UNSAT: complete small-model grounding | function symbol (leaves EPR) ⇒ DECLINE |
| **decidable_logic** (skolem) | number theory | Skolem-problem low-order witness | structure-by-size **m10** | B | exact LRS evaluation at the witness n | ★ **order ≥ 5 OPEN ⇒ DECLINE**; "never zero" not overclaimed |
| **csp_dichotomy** | CSP | Schaefer polymorphism classification (P vs NP-complete) | complete-invariant **m09** / m10 | B | P: closure re-verified; NPC: six closure-failure witnesses | ★ **PCSP FORBIDDEN ⇒ DECLINE**; non-Boolean ⇒ DECLINE |

★ Wired into production via `webapi/engine_dispatch.newengine3_reach()`; adding `newengine3` to
`engine_inventory._WIRED_PACKAGES` keeps the full-repo audit at **gap == 0** (total 691).

## Decidable-boundary discipline (the directive's absolute requirements)
- **PROMISE CSP (PCSP)** — its dichotomy is OPEN in general; ABSOLUTELY FORBIDDEN ⇒ DECLINE on any promise/pcsp
  spec. We classify only the complete **Boolean Schaefer** fragment; non-Boolean (domain>2) ⇒ DECLINE.
- **Skolem problem order ≥ 5** — OPEN (not known decidable) ⇒ DECLINE; a positive answer is EXACT only with a
  re-checked zero witness, and "proven never zero" is never overclaimed (soundness over completeness).
- **non-affine / iteration-dependent probabilistic loops** — the moments don't close into a finite linear
  system ⇒ DECLINE (the honest "unsolvable loop" boundary).
- **function symbols** leave the EPR fragment (full FO is undecidable) ⇒ DECLINE.

## Deferred to the next tranche (documented, with mechanism branch + reason)
| engine | branch | why deferred (honest) |
|---|---|---|
| **FO² / C² / guarded fragment** | m03 | the finite-model bound and counting quantifiers need a heavier encoding; EPR is the in-scope island, staged |
| **EL description-logic subsumption** | m08 confluent-normal-form | the EL completion-rule saturation is a separate build, staged |
| **modal/temporal (LTL/CTL) satisfiability** | m09 | Büchi/tableau construction overlaps §BN's deferred ω-automata; staged together |
| **VCSP / valued-CSP & CSP algo-select** | m10 | the (G)MFA/BLP-AIP tractability tests are a larger build; Boolean Schaefer is the complete in-scope core |
| **probabilistic generating-function (PGF) Bayesian / SPPL** | m10 | needs the GF frontend; the moment engine is the in-scope C-finite reuse |

★ Deferral is honest scope, not a silent gap. **PCSP and Skolem order ≥ 5 are not deferrals — they are
permanent DECLINEs** (open/undecidable). PSI/Storm/PRISM/PSI excluded (zero-dep boundary).

## Honesty (§4)
- certificate-or-DECLINE, false-EXACT 0: a construction bug ⇒ failed re-check ⇒ DECLINE.
- Axis A (the `Tⁿ` moment fold) vs Axis B (cheap verifiers: EPR re-eval, Schaefer closure, Skolem witness) labeled
  per engine; never summed.
- approximations carry a bound — none of the 3 delivered is approximate (all EXACT-or-DECLINE over ℚ / finite
  models); the approximate probabilistic methods (gPCE, sampling) are excluded or would DECLINE.
- decidable-only: PCSP, Skolem≥5, non-Boolean CSP, full FO ⇒ never claimed EXACT.
- zero-dep (z3 + stdlib + numpy); "quantum/relativistic" speedup language absent.
- ★ Sandbox blocks the live server ⇒ end-to-end production use is author-validated on Render; the engines + their
  certificates are unit-tested here (test_bo) — code + push only, no false "verified".
