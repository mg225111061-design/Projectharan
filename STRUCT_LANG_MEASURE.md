# STRUCT_LANG_MEASURE — §BJ measured (honest)

★ The build's thesis: the engines were never missing — intake recognized ONE structure, so they sat unreachable.
The numbers below measure (A) how much wider the door is, (B) which engine each structure now reaches, (C) how
many languages dispose correctly. ★ RF-1: these are **intake / soundness** numbers, NOT a fold-rate multiplier —
the foldable ceiling is structural (~6.8% real-world, measured elsewhere), independent of all of these counts.

## A — structure recognition: the door, widened (was 1, now the engine-backed families)
`frontend.structures.measure_recognition()` — the SAME shape recognized per family:

| structure | recognized kind | → engine it now reaches |
|---|---|---|
| sum loop `acc += i` | `sum_loop` | fold / Faulhaber |
| polynomial sum `acc += i*i` | `poly_sum` (★ NOT mis-read as sum) | fold / Faulhaber (Σk^d) |
| product `acc *= i` | `product_loop` | fold engine (→ honest DECLINE: factorial, not Σ) |
| Fibonacci `a,b = b,a+b` | `linear_recurrence` | **C-finite companion-matrix power** |
| convolution `c[i+j]+=a[i]*b[j]` | `convolution` | NTT (exact) |
| Horner `acc = acc*x + d` | `horner` | extract.parse_arith |
| checksum (Luhn/CRC/Adler) | `checksum` | extract.checksum |

**families recognized: 7 / 7** (was **1** — sum only). A structureless blob ⇒ `raw` (no false positive ⇒ the
dispatcher DECLINEs, never guesses).

## B — dispatcher: the engines actually RUN (the core deliverable)
`frontend.dispatch.dispatch(src, lang)` — recognized → routed → **invoked** → gated:

| input | structure | engine reached | gated by | grade (python) |
|---|---|---|---|---|
| `fib(n): a,b=b,a+b` | linear_recurrence | **C-finite** `companion_nth` (O(log n)) | lossless companion≡naïve cert | **EXACT** |
| Luhn checksum | checksum | **extract.checksum** | z3-reverified fold | CHECKED/EXACT |
| `s += i` loop | sum_loop | **fold/Faulhaber** `decide_sum_collapse` | per-language z3 QF_BV gate | **EXACT** |
| Horner eval | horner | **extract.parse_arith** | extract cert | CHECKED |

★ **Every disposition is gated** (`all_gated == true`): the engine proposes, the z3 gate / verified cert decides.
Dispatching does **not** bypass verification — `sum_loop` is EXACT in Python but **DECLINE in C** (signed UB at
n≤10⁹), the SAME structure, language-dependent soundness. Fibonacci that *was unreachable* now reaches C-finite
and folds O(log n). (Convolution→NTT and bug-check→§BD checker are **routed**; their full live invocation is
author-validated on Render.)

## C — 80+ languages, each disposing correctly under its own integer model
`frontend.languages` — **88 languages** registered, by family:

| family | count | family | count |
|---|---|---|---|
| systems | 11 | scientific | 10 |
| jvm | 8 | web | 6 |
| dotnet | 3 | mobile | 2 |
| scripting | 8 | data | 8 |
| functional | 14 | shell/legacy | 18 |

`frontend.semantics` now carries **32 `INT_MODELS`** + 3 new overflow classes (`trap`/`error`/`f64`). The SAME Σi
fold, disposed under each language's real semantics:

| language | model | Σi disposition |
|---|---|---|
| Python / Ruby / Clojure(`+'`) / Scheme / Erlang | arbitrary precision | **EXACT** (over ℤ) |
| Java / C# / Kotlin / Scala | 32-bit wrap | **EXACT wrap-aware** (naive form z3-DECLINED) |
| **Julia** Int64 | **silent** 64-bit wrap | **EXACT wrap-aware** (the trap: naive math is wrong) |
| **OCaml** | **63-bit** wrap | EXACT wrap-aware (63, not 64) |
| **Swift** | trap on overflow | **DECLINE** over-range (program aborts) / EXACT when no overflow |
| **Crystal / Ada** | raise on overflow | **DECLINE** over-range |
| C / C++ signed | UB | **DECLINE** in range (never a closed form for UB) |
| **Lua / JS / R** | f64 (≤2⁵³) | **EXACT** ≤2⁵³, else **DECLINE** (precision loss, not wrap) |

★ A wrong model would be a false-EXACT — accuracy here IS precision 1.0. (`semantics.extended_models_battery()`
and `languages.adversarial_battery()` both green.)

## Honesty (§5)
- **RF-1**: A (more structures) + C (more languages) = **intake improvement** — the engines reach more real code
  (genuine value: the narrow door is widened). NOT "80 languages = 80× coverage"; the foldable ceiling is
  structural and measured, set by code structure, not language count. (Stated in code + docs; tested.)
- **Dispatching never bypasses verification**: every engine output rides the per-language z3 gate / a verified
  cert (`all_gated`); a fold sound in one language and unsound in another is DECLINED (precision 1.0).
- **0 new mechanism, 0 new disposer**: the dispatcher REACHES the 14 existing mechanisms via `recall/core`.
- zero-dep (z3 + stdlib + numpy); tree-sitter optional (pure-Python fallback recognizers, same soundness).
- ★ Sandbox blocks tree-sitter grammars + most language test files ⇒ the live multi-language parse + the full
  invocation of NTT/backend/§BD per language are **author-validated on Render**; code + push only here, no false
  "verified".
