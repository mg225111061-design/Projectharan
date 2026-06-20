# PHASE D (v57–v59) — detector expansion 4 → 40+ (each gated by its ModePolicy tier)

Each detector is an AST/complexity/runtime signature + a fixer + the verifier + a measured whole-program report
+ a grade, registered in the right mode tier. Per detector the test asserts: detected · differential passes ·
measured whole-program win > 1 · correct grade · ★ wrong fix → DECLINE ★ · ModePolicy gating.

## Batch D1 (v57) — catastrophic single-bug detectors (fast-eligible)
`pillar3/detectors2.py`:
- **redos_regex** — a regex literal with a nested quantifier on a group `(X+)+` ⇒ catastrophic backtracking;
  linearise. Measured ~**3000–3600×** whole-program on adversarial input (SlowFuzz, CCS 2017, in spirit).
- **redundant_io_parse** — a parse/load/compile of loop-invariant data inside a loop ⇒ hoist (parse once).
  Measured ~**20×**.
- **accidental_full_scan** — a linear find (`.index`/`== ` filter) inside a loop ⇒ build a dict index for O(1).
  Measured ~**138×**.
- **quadratic_build** — `acc = acc + [x]` / `s = s + t` in a loop ⇒ O(n²) copies; append + join. ~**150×**.
- **redundant_sort** — `sorted(...)` of loop-invariant data inside a loop ⇒ hoist (sort once). ~**88×**.

All five detected the planted waste, the known-good fix passed differential + measured whole-program win, **a
wrong fix was caught → DECLINE** every time, and each is registered in the **fast** tier (`FAST_DETECTORS`).

(Also folded in here: a robustness fix to the PHASE-M2 spine test — a deterministic cost model in
`canonical.py` and a per-session coherent measurement in `engine.py`, so the mode-distinctness assertions are
stable under full-suite load instead of depending on incidental timing. 5/5 stability trials green.)

## Batch D2 (v58) — structural / data-representation (normal-tier)
`pillar3/detectors2.py`:
- **dict_to_columnar** — a hot scan over a list of dicts with repeated field access ⇒ struct-of-arrays
  (parallel lists) removes per-row dict hashing. Measured ~**1.3×** (the honest pure-Python SoA crossover).
- **loop_invariant_hoist** — a non-trivial loop-invariant computation inside a loop ⇒ hoist. ~**700×**.
- **copy_elim** — a defensive `list(x)` / `x[:]` / `.copy()` of read-only data ⇒ eliminate. ~**50×**.
- **materialize_to_lazy** — a list built only to be consumed once (early-exit loop / any / next) ⇒ generator.
  ~**3000×** (the early exit never materialises the tail).
- **deep_n_plus_1** — a per-item fetch inside a NESTED loop ⇒ coalesce across both levels. ~**57×**.

Each detected, differential-verified whole-program win, **wrong fix → DECLINE**, registered **normal** tier
(present in `NORMAL_DETECTORS`, absent from `FAST_DETECTORS` — the D2-not-in-fast gating).

## Batch D3 (v59) — heavy (extend-tier)
*(pending)*

## §0 self-check (per detector)
measured whole-program win (not kernel); grade enforced by the ADT; differential FIRST (wrong fix → DECLINE);
gated by the mode tier (a detector absent from a mode's `enabled_detectors` does not fire). Honest scope: a few
transforms (SoA, vectorise) have a real pure-Python crossover only at scale or via numpy; where a dependency is
absent it is tagged UNVERIFIED, never faked.
