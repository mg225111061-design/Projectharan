# PRODUCTION_AUDIT — §BK STEP 0: which engines actually reach production (verified by reading the code)

★ The directive's premise, checked against the real `server.py` + `webapi/engine_bridge.py` (not assumed):

## Already wired (the directive UNDER-states this — credit where due)
`webapi/engine_bridge._loop_collapse` already imports and runs, on every `/api/optimize`:
- **`structure_recognizer`** (63 KB) — `decide_loop` (Σ-loop → O(1), Gosper), `dispatch` (other fold-shaped
  loops), `_nested_acc`/`_offload_nested` (double-nested accumulation). **WIRED.**
- **`loop_recurrence`** → **`cfinite`** — `decide_recurrence_collapse` / `decide_modular_recurrence_collapse`
  (Fibonacci-style → O(log n) companion power). **WIRED.**
- **`pillar3`** — `engine`, `canonical`, `corpus_runner`, `mode`/`mode_budget` (the canonical-fix optimizer +
  budget contract). **WIRED.**

So sum / polynomial / nested / recurrence folds DO reach production today. The bottleneck is narrower than "nothing
is connected": a powerful TIER of engines is still theory-only.

## The gap (verified absent from `server.py` + `webapi/`)
`grep` over the production path finds **no** import/call of:
| engine | what it does | status |
|---|---|---|
| **freivalds** / **fast_certificates** | proposer-verifier: verify an expensive/untrusted matmul in O(kn²), δ=2⁻ᵏ | **GAP** |
| **chc_solve** | CHC/Spacer loop-safety + ★ independent re-verification (fresh z3, fail⇒DECLINE) | **GAP** |
| **ic3_pdr** | k-induction loop safety (never a false SAFE) | **GAP** |
| **extract catalog** (checksum/parse_arith/io_count) | CRC/Luhn/Horner/IPv4 folds (z3-reverified) | **GAP** |
| **frontend.dispatch** (§BJ) | structure→engine + 88-language semantics gate | **GAP** |
| **foldcache** / **semantic_cache** / **proof_cache** | sound content-hash caches (whole-pipeline fold) | **GAP** |

## The fix (STEP 1/2) — `webapi/engine_dispatch.py`, wired into `engine_bridge`
A single central dispatcher that **reaches the gap engines** and is exposed to the production module
(`engine_bridge.dispatch_engines(code)`), so gap → 0. ★ Every engine output still rides the grade discipline
(Freivalds PROBABILISTIC never EXACT; chc/ic3 keep independent re-verification; everything via the verdict ADT /
`recall/core` spirit). PIPE-1: the dispatch is wrapped in the sound `FoldCache` (content-hash), so a repeated
request recomputes nothing (Clock B → 0 on a warm hit).

★ **3-clock honesty**: Clock A (LLM latency) is **immutable** — wiring engines + caching reduces **Clock B**
(verification) and **Clock C** (fold accel), never A. "reduce B = reduce A" is never claimed; the three clocks are
never summed. The felt latency is *Clock A + a near-zero delta*.

★ **RF-1**: wiring is a real improvement (the weapons reach production), but the foldable ceiling (~6.8% real-world)
is structural and **unchanged** — "all engines wired" is NOT "coverage explosion".

★ Sandbox blocks the live server (external deps, tree-sitter, LLM egress) ⇒ the end-to-end production run is
author-validated on Render; the dispatcher + cache + each engine's reachability are unit-tested here, code + push
only, no false "verified".

## §BL — full-repo gap=0 (every engine, not just the §BK tier)
`engine_inventory.py` scans ALL 668 non-test `.py` and classifies reachability (see ENGINE_INVENTORY.md):
**gap = 0** — 521 engines reachable (136 wired_entry + 362 transitive-via-wired-package + 23 pipeline_infra); the
remaining files are honestly classified as `app_layer` (28, the caller), `dev_tooling` (20), `observability` (49),
`package_init` (50) — intentional non-targets, named not hidden. ★ The §BK pipeline caches are extended to the
full set (foldcache · semantic_cache · proof_cache · lemma_broth · enginespeed) — PIPE-1 reach-probed. RF-1 holds:
this is reach (weapons → production), the ~6.8% foldable ceiling is structural and unchanged.
