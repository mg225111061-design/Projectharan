# CHECK_CORPUS — §BD debugging-zero checker layer, measured (the directive's honesty)

★ Two faces, never mixed — and they are graded **separately** (the directive's first invariant):
- **CHECK** (CHK-2 bug-pattern catalog, exhaustive over relevant sites) → a clean pass is **CHECKED** = "common bugs
  absent" (strong trust, **NOT** a guarantee).
- **PROVE** (CHK-5 routed through the existing fold engine's kernel_verdict EXACT cert) → **EXACT** = a guarantee.

★ The honest O(1): **reading is O(N)** (parse — fast, never beaten). Only the SLOW semantic question ("what total does
this accumulator reach / can it overflow") jumps to O(1), by folding the loop into a closed form (CHK-4) instead of
running it. NOT "knowing without looking".

## Measured — clean §AK corpus (precision direction: a clean line is never false-flagged)
`python -c "from corpus.build_corpus import build_corpus; from checker.grade_and_fix import check; ..."` over **N = 400**
generated codes (synthetic + realworld-style, 5 domains):

| grade | count | meaning |
|---|---:|---|
| EXACT | 69 | pure; every loop folded to a closed form carrying a **passed** kernel_verdict EXACT cert |
| CHECKED | 331 | no catalogued bug found, no proof available (honest middle) |
| FLAGGED | **0** | the corpus is clean generated code ⇒ **zero false positives** (the precision claim, measured) |
| DEFER | 0 | the corpus has no eval/exec/reflection |

Bug-pattern hits on the clean corpus: **{} (none)** — the catalog does **not** fire on clean code. This is the precision
half of the spine: a clean line is never reported buggy.

**Foldable-loop ratio** (CHK-4, the O(1) core): foldable **69** / deferred **117** / total **186** ⇒ **0.371**. Honest
reading: ~37% of corpus loops are closed-range accumulators the fold engine collapses to O(1); the other ~63% are
data-dependent (`s += a[i]`), `while`, or outside the decided class ⇒ **honest DEFER for that loop's semantics** (no false
O(1) claim). This ratio is a property of the corpus (lots of array/data loops), not a ceiling on the checker.

## Measured — planted-bug minicorpus (recall + the precision SPINE)
A 10-case set, one per catalogued shape (+ 2 unanalyzable):

| input | grade | located | spine: clean? |
|---|---|---|---|
| mutable default arg `def f(x=[])` | FLAGGED | L1 | not clean ✓ |
| bare `except: pass` | FLAGGED | L4 | not clean ✓ |
| `x == None` | FLAGGED | L2 | not clean ✓ |
| `open(p)` no `with` | FLAGGED | L2 | not clean ✓ |
| `while True: pass` | FLAGGED | L2 | not clean ✓ |
| `assert (x>0, 'pos')` (always-true tuple) | FLAGGED | L2 | not clean ✓ |
| `a % 0` (literal-zero divisor) | FLAGGED | L2 | not clean ✓ |
| syntax error `def f(:` | FLAGGED | L1 | not clean ✓ |
| `eval(s)` | DEFER | — | — (honest "can't verify") |
| `exec(s)` | DEFER | — | — (honest "can't verify") |

Result: **8 FLAGGED + 2 DEFER, and planted-bugs-graded-clean = 0.** ★★ The spine holds: **no buggy input is ever graded
clean** (precision 1.0). When a shape is ambiguous the catalog FLAGs (CHK-3); EXACT only ever rides an already-passed
certificate, so a false-EXACT is structurally impossible.

## Conservative non-firing (precision, NOT a miss)
- `a / b` with a **variable** divisor is **not** flagged — it is correct whenever `b ≠ 0`, so it is not a "common bug".
  CHECKED means "the catalogued bugs are absent", explicitly **not** "no bug exists" (that is the separate PROVE face).
- `while True:` **with** a reachable `break`/`return`/`raise` is **not** flagged (it has an exit; unreachability is
  undecidable in general ⇒ no false bug claim).

## Honesty (§4 of the directive)
- **"all code debugging 0" is FALSE.** Only CHECK + PROVE pass; structureless / opaque logic (eval/exec/reflection) ⇒
  **HONEST_DEFER** ("can't verify this — review it"). Measured: eval/exec → DEFER, never a silent pass.
- **precision 1.0** — measured: 0 planted bugs graded clean; 0 false flags on 400 clean codes.
- **O(1) is semantic analysis only** — reading stays O(N) (parse). The 0.371 foldable ratio is exactly the fraction
  where the slow semantic check is jumped; the rest honestly DEFER.
- **No new mechanism / no new disposer.** The checker is a new *recognition/scan* branch: CHK-1/2/4 are AST scans;
  CHK-5 PROVE is issued **only** by the existing `loop_decision`/`recall/core` kernel_verdict path. 14/22 mechanism
  saturation and the single disposer are untouched.
- **Sandbox note.** The container's egress blocks the provider domains and the open web, so the live write→fix→recheck
  loop (LLM-authored fix) runs on **Render**; here the checker emits the **fix instruction** per finding
  (`CheckResult.fix_instructions()`), and the author closes the loop in deployment. No false "verified live" claim.

## Invariants held (gates)
- zero-dep (stdlib `ast` + the existing engine only); `test_build` 274/0; `test_catalog` + `test_bd_checker_layer`.
- fold-rate / false-EXACT / 660-EXACT invariant untouched: `checker/` is additive, not imported by the corpus-count
  or fold engines; EXACT rides an existing passed certificate (no new EXACT source).
