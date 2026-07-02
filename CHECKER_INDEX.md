# CHECKER_INDEX — §BD debugging-zero checker layer, pre-build index (§2)

★ The honest O(1): **reading is O(N)** (can't beat — an unread line's bug is unfindable; but parsing is fast, ms).
The slow part is **semantic analysis** (does this loop overflow? exceed a bound?) — naively O(N) per check by running
the loop; **fold closes the loop into a formula ⇒ O(1)** (jump, don't iterate). So total = O(N) read (already fast)
+ O(1) semantics (fold). NOT "knowing without looking" (impossible, false-EXACT-spirit) — "read fast + jump the
slow part".

★ Two faces, never mixed, different grades:
- **CHECK** (exhaustive pattern scan, ALL code) — hundreds of bug patterns on every relevant line, completeness like
  the security total-scan (miss nothing). Pass ⇒ **CHECKED** = "common bugs absent" (strong trust, NOT a guarantee).
- **PROVE** (z3 bit-exact, only verifiable code) — Pass ⇒ **EXACT** = "correct" (guarantee).

## Already built (reuse — re-write 0)
| part | location | role in the checker |
|---|---|---|
| effect classifier (pure/io/nondet) | `extract/classify/effect_gate.py :: classify_effect / is_pure` | CHK-1 structure-index input (purity, I/O, nondeterminism) |
| fold engine (loop → closed form) | `loop_decision.py`, `mathmode/fold.py`, `cfinite.py`, `closure_classifier.py` | CHK-4 O(1) loop semantics (overflow/bounds via closed form) |
| **PROVE single disposer** | `recall/core.fold_via_ai` (z3 ∀-proof + held-out=200), `pillar3/equiv` (bit-exact) | CHK-5 — the ONLY place a PROVE/EXACT is issued ⇒ false-EXACT structurally impossible |
| structure cache | `detect_interproc_memoize` / `accel/verified_io.verified_cache` | CHK-3 O(1) reuse of the same structure |
| independence | `sep_alias.py`, `accel/verified_parallel._conflicts` | concurrency/race pattern (shared-mutable) |
| AST infra | stdlib `ast` (used across pillar3/recall/extract) | parse + one-pass traversal |
| HONEST_DEFER discipline | `kernel_verdict` DECLINE + the repo-wide "DECLINE > wrong" spine | the DEFER grade |

## net-new (this build, `checker/` package) — NO new mechanism, NO new disposer
- `checker/structure_index.py` (CHK-1) — one-pass AST → pattern-possible-points map (nullable vars, division sites,
  loops, exception paths, resource handles, shared state). Reuses `effect_gate`.
- `checker/bug_patterns.py` (CHK-2) — data-driven catalog, one-pass simultaneous match, skips irrelevant lines via
  the CHK-1 index ⇒ O(relevant) ≪ O(N×P). CHK-3 conservative: unsure ⇒ FLAG (never false-clean — precision 1.0).
- `checker/loop_semantics.py` (CHK-4) — foldable accumulator ⇒ O(1) overflow/bound check (closed form, no iteration);
  not foldable ⇒ honest DEFER for that check.
- `checker/grade_and_fix.py` (CHK-6) — orchestrate ⇒ grade EXACT / CHECKED / FLAGGED(+fix instruction) / DEFER;
  PROVE routed to `recall/core`/`pillar3/equiv` (CHK-5). The write→check→fix→recheck loop (live LLM fix is
  egress-blocked here ⇒ the fix *instruction* is generated; the loop closes on Render).

## Honesty (§4)
- "all code debugging 0" is FALSE — only CHECK+PROVE passes; structureless logic ⇒ **HONEST_DEFER** ("can't verify
  this — review it"). No overclaim.
- precision 1.0: CHECK never marks a buggy line clean (unsure ⇒ FLAG); PROVE rides `recall/core` ⇒ false-EXACT impossible.
- O(1) is **semantic analysis only** — reading stays O(N) (fast, not beaten). No "know without looking".
- 14 mechanisms / single disposer invariant: the checker is a new *recognition/scan* branch over existing engines.
