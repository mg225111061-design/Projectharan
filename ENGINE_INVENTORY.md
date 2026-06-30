# ENGINE_INVENTORY — §BJ §0/§3 index: every engine we built + its input interface

★ The diagnosed bottleneck (from reading the code): the engines are **not missing** — `frontend/lang_intake.py`
recognizes exactly ONE structure (`_SUM_LOOP`, `acc += i`), so every powerful fold/verify engine below sits
**unreachable behind that narrow door**. §BJ widens the door (A: more recognizers) and adds a **dispatcher**
(B: route each structure to the engine that already handles it), keeping disposition through the z3 gate +
`recall/core` (false-EXACT 0). NOT a new mechanism, NOT a new disposer — intake/wiring on top of existing power.

## Engines + their input interface (what the dispatcher must pass)
| engine | module · entry point | input | output | dispatch from |
|---|---|---|---|---|
| **fold / Faulhaber** | `loop_decision.decide_sum_collapse(summand_src, var, lo)` | summand source string | `LoopDecision(status, verdict, complexity)` | sum loop, polynomial sum |
| **C-finite** | `cfinite.companion_nth(c, init, n)` + `verify_cfinite(c, init, ns)` | recurrence coeffs + init | O(log n) value + lossless cert | linear recurrence (Fibonacci) |
| **NTT** | `rust_accel` NTT / `gapfold/divide_conquer` | two integer sequences | exact convolution | convolution loop |
| **extract: checksum** | `extract.checksum.recognize(src)` / `fold(src)` | source string | `ChecksumResult` (z3-reverified) | CRC/Adler/Luhn pattern |
| **extract: parse/Horner** | `extract.parse_arith.fold(src)` | source string | `ParseResult` | atoi/base/varint/IPv4/float parse |
| **extract: periodic FSM** | `extract.periodic_fsm.fold(src, oracle)` | source string | `FSMResult` | periodic state machine |
| **extract: I/O count** | `extract.io_count.fold(src)` | source string | `IOCountResult` (EXACT call count) | buffered I/O call pattern |
| **extract: classify** | `extract.classify.classify(src)` | source string | effect/shape tags | the pre-router |
| **egraph simplify** | `egraph` equality-saturation + z3 | expression | normal form | algebraic redundancy |
| **pillar3/equiv** | bit-identical translation validation | two programs | EXACT-equiv / DECLINE | equivalence question |
| **sep_alias** | separation-logic disjointness | index expressions | independent / DECLINE | aliasing/independence |
| **backend_llvm** | verified native lowering | IR | native + compile cert | native codegen |
| **detect_interproc_memoize** | `pillar3.detectors2.detect_interproc_memoize(call_args)` | repeated call args | memoize finding | repeated pure calls |
| **§BD checker** | `checker.grade_and_fix.check(src)` | Python source | grades (EXACT/CHECKED/FLAGGED/DEFER) | bug / structure check |
| **z3 QF_BV gate** | `frontend.semantics.sum_fold_under_language(sem_key, n)` | sem key + bound | EXACT/DECLINE under lang | EVERY disposition (the gate) |
| **recall/core** | `recall.core.fold_via_ai` | fn + disguise | single disposer | EVERY fold rides it |

## net-new this build (§4) — the door + the dispatcher + accurate semantics (re-build 0)
- **A `frontend/structures.py`** — `_STRUCT_RECOGNIZERS` (sum / product / poly-sum Σk^d / linear-recurrence /
  convolution / checksum / horner), language-agnostic deterministic fallbacks → one `StructMatch`. Replaces the
  single `_SUM_LOOP`.
- **B `frontend/dispatch.py`** — routing table `struct kind → engine` that ACTUALLY invokes the engine (fold,
  C-finite, extract demonstrated live here), with disposition STILL through the semantics z3 gate + `recall/core`.
- **C `frontend/languages.py`** + `frontend/semantics.py` (extended) — 80+ language registry → accurate integer
  model (Julia silent wrap · OCaml 63-bit · Clojure promotion · Swift trap · Crystal error · Ruby/Scheme/Erlang
  arbitrary · Lua/JS/R f64 · Zig +% · Haskell Int/Integer). New overflow classes: `trap` / `error` / `f64`.

## Honesty
- RF-1: A widens recognition + C adds languages = **intake improvement** (engines reach more real code — real
  value). NOT "N languages = N× coverage": the foldable ceiling is **structural** (~6.8% real-world, measured),
  set by the code's structure, not the language count.
- The dispatcher reaches existing mechanisms; **0 new mechanism, 0 new disposer**; engine output is **never** a
  bypass of verification (z3 gate + `recall/core`). A fold sound in one language and unsound in another ⇒ DECLINE.
- ★ Sandbox blocks tree-sitter grammars + most language test files ⇒ the live multi-language parse + per-language
  disposition are **author-validated on Render**; code + push only here, no false "verified".
