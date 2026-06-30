# IMPL_FULL_INDEX — §BH two-axes-one-weapon, 5-stage pre-build index (§2)

★ The flagship (research's strongest finding): **the two axes are one weapon.** By the recurrence→closed-form
bridge (Tiwari CAV'04 linear-loop termination decidable; Braverman CAV'06 integer extension), **the loop axis-1
*folds* to a closed form is exactly the loop axis-2 *proves* terminating** — same companion matrix, same math.
Build the fold engine stronger ⇒ the verifier gets stronger, and vice-versa.

★ Honest ceilings (and they are *good news*): axis-1 "beat native" = remove (fold) / reduce (complexity) / verify
cheaply — "same computation, free speedup" is a Landauer/Margolus–Levitin/Bremermann/Bekenstein mirage. axis-2:
Rice's theorem ⇒ no checker proves every non-trivial semantic property → sound verification = **PROVE (provable) /
CHECK (checkable) / HONEST_DEFER (neither)** — which is *exactly* our three grades. "quantum/ultra-speed" banned.

## Already built — gem→engine map (reuse; re-build 0)
| stage | gem | already-built | net-new this build |
|---|---|---|---|
| **0** | Freivalds + Schwartz–Zippel universal verifier | `freivalds.py` (k param), SZ scattered (`equiv_check`, `mobius_fold`, `holonomic_sum`) | **unified lane k=128 + deterministic-integer Freivalds + SZ poly-identity** |
| **0** | WZ certificate fold (Gosper/Zeilberger) | `mathmode/telescoping.py`, `loop_decision.decide_sum_collapse` | — (built; proposer-verifier itself) |
| **1** | C-finite → matrix power O(log n) | `cfinite.py` (`_matpow`), `loop_recurrence.py` | — (built; §BG measured ≈11×) |
| **1** | Faulhaber / finite-difference | `loop_decision`, `foldaxes` | — (built) |
| **1** | NTT exact convolution (float-0) | `rust_accel.py` (NTT), `gapfold/divide_conquer.py` | — (built) |
| **1** | complexity reduction (Strassen/rSVD/sparse-FFT) | `kernels_structured.py`, `gapfold` | — (measured-crossover only; galactic CW/HvdH doc-only) |
| **2** | CHC / Spacer | ★ **z3 4.16 `Fixedpoint`/Spacer BUILT IN** (zero-marginal-dep, confirmed) | recognition branch (decidable linear class) |
| **2** | k-induction / bounded + inductive | `equiv_check.py` | — (built) |
| **2** | invariant synthesis (Karr/Farkas/Gröbner) | `barrierfold/invariant_synth.py` (§AE island 5) | — (built) |
| **2** | termination (ranking / SCT) | §AE island 6 termination | **★the bridge: ranking fn from the SAME companion matrix** |
| **2** | Daikon-style likely invariants | — (absent) | net-new *deferred* (proposer→z3-certify; risk-bounded, documented) |
| **3** | structure-indexed pattern scan | `checker/*` (§BD) | — (built; CHECK foundation) |
| **3** | abstract-interpretation domains | `pillar3/interval.py`, `polyhedral_opt.py`, `accel/xform/polyhedral.py` | — (interval built; octagon/polyhedra escalation doc-only) |
| **3** | CWE catalog / separation-logic patterns | `checker/bug_patterns.py` (§BD) | — (built; conservative FLAG) |
| **4** | proposer-verifier autofix (translation validation) | `pillar3/equiv.py`, `pillar3/stoke.py`, §BF `diagnostics.py` | — (equiv + diagnosis built; fix-instruction loop) |
| **prod** | grade UI + RUN flow + DEFER-only highlight | **§BG (mrjeffrey.html: 점검 button, grade labels, defer-box)** | — (DONE in §BG) |
| — | single disposer (false-EXACT 0) | `recall/core.fold_via_ai` | — (every fold + PROVE rides it) |

## net-new this build (§3) — small, surgical, on-spine
1. **STAGE 0** `verify_universal.py` — one universal cheap-verifier lane: Freivalds **k=128** (δ=2⁻¹²⁸) + a
   **deterministic-integer** Freivalds (true EXACT, no δ) + **Schwartz–Zippel** polynomial-identity (degree d,
   random point, δ ≤ d/|S|). The common engine behind Freivalds/sum-check/Kaltofen. Graded via the ADT
   (PROBABILISTIC with stated δ, or EXACT for the deterministic variant — never EXACT+δ).
2. **★the spine** `bridge.py` — recurrence→closed-form bridge: for a linear-update loop, axis-1 returns the closed
   form (companion matrix power, reuse `cfinite`) AND axis-2 returns a **z3-certified termination verdict** (ranking
   function for the increasing-to-bound class; non-termination when there is no progress) — both from the SAME
   (coeffs, bound). Demonstrates "the loop that folds is the loop that proves," fold ⟺ prove, on one object.

## Honesty (§4)
- two axes = one weapon (the bridge); build once, both gain. axis-1 ceiling = remove/reduce/verify (Landauer);
  axis-2 ceiling = Rice ⇒ PROVE/CHECK/DEFER (our 3 grades). "quantum/ultra-speed" absent.
- false-EXACT 0: every fold + PROVE rides `recall/core`; Freivalds k=128 or deterministic; SZ states δ; Daikon
  (if/when built) is z3-certified, never trusted directly; CHECK is conservative (unsure→FLAG).
- measurement-premise: every speed claim carries a measured crossover (IMPL_FULL_MEASURE.md); no galactic switch
  (CW/HvdH doc-only); approximations state bounds.
- zero-dep (z3 incl. Spacer + stdlib + numpy); industrial tools (Astrée/Infer) reused as *theory*, not the system
  (zero-dep subset); needs-hw (analog/optical) out of scope.
- ★ Sandbox blocks the WASM CDN + COOP/COEP + the open web ⇒ the live browser path + per-language numbers are
  author-validated on Render; code + push only here, no false "verified" claim.
