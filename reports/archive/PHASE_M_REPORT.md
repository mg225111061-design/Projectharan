# PHASE M (v54–v55) — MODE SEPARATION: fast / normal / extend (the spine)

The #1 deliverable. The three modes are now **enforced contracts**, not speed presets — and the engine
*proves* they are observably, measurably distinct.

## Delivered
- `pillar3/verifier.py` — the verifier-tier ladder `MICRO < CHEAP_CERT < FULL_CERT` (IntEnum, ordered) + the
  **Z3 invocation counter** that makes separation checkable. `equiv.prove_equiv` reports every `solver.check()`
  here, so `z3_check_count()` reflects real SMT work no matter which path reached it. `attempt_certificate` is
  the single gate to Z3: MICRO never invokes it, CHEAP_CERT only on a small region, FULL_CERT always.
- `pillar3/mode.py` — `Mode{FAST,NORMAL,EXTEND}` + `ModePolicy` encoding **every row** of the M.2 contract
  (`enabled_detectors`, `verifier_tier`, `runs_complexity_sweep`, `max_hotspots`, `max_iterations`,
  `acceptable_grades`, `stop_condition`, `marginal_floor`, `latency_budget_s`, `risk_posture`, …). The M.1
  philosophy of each mode lives here as the module docstring. Detector sets are strictly monotone
  `fast ⊂ normal ⊂ extend` (10 ⊂ 18 ⊂ 27 names).
- `pillar3/engine.py` — the mode-aware loop controller every stage routes through. It does NOT hard-code
  behaviour: it fires only detectors in `enabled_detectors`, reaches Z3 only via the verifier at/below
  `verifier_tier`, ships only grades in `acceptable_grades` (the grade floor), attacks `max_hotspots`,
  iterates `max_iterations`, and stops per the mode's rule. Whole-program ratio AND Amdahl ceiling come from
  **one measurement session** (a "floor pipeline" with active stages passed through), so **ratio ≤ ceiling by
  construction** regardless of measurement noise.
- `pillar3/canonical.py` — the canonical multi-waste fixture: five stacked, independent wastes (list-as-set,
  N+1, accidental-O(n²), naive-poly→Horner algorithmic, SIMD-offloadable numeric) with **measured** fractions.

## The contract, made executable (M.2)
| dimension | fast | normal | extend |
|---|---|---|---|
| verifier tier | MICRO (never Z3) | ≤ CHEAP_CERT | FULL_CERT |
| detectors | cheap structural (10) | + structural/data (18) | + heavy/algorithmic (27) |
| complexity sweep | none | optional | always (multi-size) |
| hotspots | top ≤3 | flame graph | entire profile |
| acceptable grades | EXACT or PROBABILISTIC | EXACT or PROBABILISTIC | **EXACT only** |
| iteration | first accepted win | until <10% marginal | every enabled detector |
| latency | sub-second target | moderate | unbounded |

## Measured — the seven distinctness proofs (one canonical program, three modes)
1. **fast** — attacks ≤3 hotspots; **z3_calls == 0** (NEVER invokes Z3); one accepted win; ships a
   PROBABILISTIC; ~0.5 s.
2. **normal** — 3 rounds; ships **EXACT and PROBABILISTIC**; compounds a measured fresh cumulative ~1.9×.
3. **extend** — runs the multi-size sweep (O(n²) recovered, 3 sizes); **z3_calls > 0** (full Z3 on the swap);
   ships **only EXACT** (~2.0×); higher than fast.
4. **cross-mode monotonicity** — speedup `extend ≥ normal ≥ fast` AND latency `fast < normal < extend`.
5. **detector gating** — `gpu_simd_offload` fires in extend, NOT in fast or normal.
6. **verifier-tier gating** — fast=MICRO (no Z3 reachable), normal≤CHEAP_CERT, extend=FULL_CERT.
7. **★ the key one ★** — the same PROBABILISTIC-only fix (accidental-quadratic) is **ACCEPTED in normal,
   DECLINEd in extend** — the EXACT-or-DECLINE proof, enforced by `ModePolicy.acceptable_grades`, not the fixer.

Plus: **every shipped row across all three modes has ratio ≤ its Amdahl ceiling** (by construction).

## §0 self-check
1. measured whole-program vs neutral baseline? yes — engine measures T_base once, ratio = T_base/T_cand.
2. hotspot fraction + ceiling, ratio ≤ ceiling? yes — coherent floor-pipeline measurement guarantees it.
3. graded, survives ADT raise-check? yes — grades from kernel_verdict ADT; extend rejects δ-carrying fixes.
4. verified at this step before the next? yes — differential FIRST every candidate; declines never chained.
5. unmeasurable/blocked → UNVERIFIED + excluded? yes — no live LLM ⇒ deterministic detectors (Rule 5).

## Honest scope
The canonical fixture is synthetic-but-real: each stage performs a genuine wasteful operation and its real fix;
fractions are measured, not declared. No live LLM ⇒ the proposer is deterministic detectors (Rule 5 — the
proposer was never the arbiter). Full suite re-run: **0 regression.**
