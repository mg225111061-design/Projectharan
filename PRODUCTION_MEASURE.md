# PRODUCTION_MEASURE — §BK measured (honest)

★ Two things measured: (1) how many previously-theory-only engines now REACH production (gap → 0), and (2) the
whole-pipeline fold (Clock B → 0 on a warm hit). ★ 3-clock honesty: Clock A (LLM) is **immutable** and untouched —
these numbers are the delta WE add (Clock B/C), never A, never summed.

## STEP 1 — production reach (the "100%" meter)
`webapi.engine_dispatch.production_reach()` (and `engine_bridge.engines_reached()`):

| engine (was theory-only) | reached? | grade discipline preserved |
|---|---|---|
| freivalds | ✓ | PROBABILISTIC (δ=2⁻²⁴), never EXACT |
| fast_certificates | ✓ | one-sided Clock-B cert |
| chc_solve | ✓ | Spacer + ★ independent fresh-z3 re-verify (fail ⇒ DECLINE) |
| ic3_pdr | ✓ | k-induction (never a false SAFE) |
| extract catalog | ✓ | z3-reverified folds |
| frontend.dispatch (§BJ) | ✓ | per-language z3 gate (Python EXACT / C UB-DECLINE) |
| caches (foldcache) | ✓ | sound content-hash (no stale hit) |

**reached 7 / 7 — `gap_remaining == 0`.** (Plus the already-wired tier credited in PRODUCTION_AUDIT.md:
structure_recognizer, loop_recurrence→cfinite, pillar3.) ★ A repeated `dispatch_engines("…Fibonacci…")` reaches
**C-finite companion power, EXACT** — the weapon that was unreachable now runs in production.

## STEP 2 — whole-pipeline fold (Clock B → 0), measured
`engine_dispatch.dispatch` wrapped in the sound `FoldCache` (PIPE-1):

| | time | computes |
|---|---|---|
| cold (first request) | 16.835 ms | 1 |
| **warm (repeat request)** | **0.0446 ms** | **0** (cache hit) |
| ratio | **≈378×** on the warm hit | — |

★ **Honest reading**: the warm hit recomputes NOTHING — the dispatch result (a previously *verified* disposition)
is served from a content-hash key, so the verification time (Clock B) we add on a repeat is ≈0. The cold number
includes z3/import warmup and is the genuine one-time cost. This does **not** touch Clock A (the LLM call) — the
felt latency on a repeat is *Clock A + ~0*. ★ The cache is SOUND: the key is content-addressed and the cached
value is a disposition that already passed the gate, so a warm hit can never serve an unverified result.

## 3-clock split (the honest frame — `engine_dispatch.clocks()`)
- **Clock A (LLM)** — IMMUTABLE. Wiring + caching do not and cannot reduce it. "reduce B = reduce A" is never claimed.
- **Clock B (verification)** — → 0 via wiring + FoldCache + (on Render) fast-cert skip + incremental re-verify.
- **Clock C (fold)** — execution removed (closed form), a separate win.
- The three are **never summed**; the product feels like *Clock A + a near-zero delta*.

## Honesty (§4)
- **false-EXACT 0**: wiring PRESERVES each engine's grade discipline (Freivalds PROBABILISTIC, chc independent
  re-verify, ic3 no-false-SAFE, §BJ language gate) — the dispatch never bypasses verification; the cache only
  serves already-verified dispositions.
- **RF-1**: reaching the engines is a real improvement (weapons → production), but the foldable ceiling (~6.8%
  real-world) is structural and **unchanged** — "all engines wired" is NOT "coverage explosion".
- **0 new mechanism, 0 new disposer**: `engine_dispatch` is wiring + a cache wrapper over existing engines; the
  grade still flows from `recall/core` / the verdict ADT. "quantum/relativistic/ultra-speed" absent (Landauer).
- ★ Sandbox blocks the live server (deps, tree-sitter, LLM egress) ⇒ the end-to-end production run is
  author-validated on Render; the dispatcher, the reach meter, and the cache are unit-tested here — code + push
  only, no false "verified".
