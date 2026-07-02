# LANG_INDEX — §BJ §0/§3: language intake + semantics, before/after

## Already built (re-build 0)
- `frontend/lang_intake.py` — **8 languages** (python/js/ts/java/csharp/c/go/rust), `_SUM_LOOP` recognizer (sum
  loop ONLY), `IntakeResult`, `measure_per_language`. ★ Left UNTOUCHED by §BJ (no regression) — the 80+ expansion
  is additive in new modules.
- `frontend/semantics.py` — **10 `INT_MODELS`** + the z3 QF_BV gate `sum_fold_under_language`. Overflow classes:
  `none` (arbitrary) / `wrap` (mod 2ʷ) / `ub` (C signed) / `checked` (Rust) / `saturating`.
- `catalog/ir.py` `StructForm` — the language-agnostic IR (the dispatch hub).

## net-new (§4-C) — 80+ languages + accurate semantics (additive)
`frontend/semantics.py` gains models + **3 new overflow classes**:
- `trap` — overflow aborts at runtime (Swift): no UB, but a closed form would skip the trap ⇒ DECLINE over-range,
  EXACT when no overflow provable (same shape as `checked`).
- `error` — overflow raises (Crystal, Ada `Constraint_Error`): same shape as `checked`.
- `f64` — IEEE-754 double-backed integers (Lua / JS / R / MATLAB / Octave): exact only while every intermediate
  ≤ 2⁵³; beyond that precision is silently lost ⇒ DECLINE (rounding, not wrap — never a wrap-aware rescue).

`frontend/languages.py` — registry of **80+ languages → (sem_key, family, note)**, grouped by the directive's waves:
systems (Zig `+%` / Crystal `error` / Nim / D / V / Hare / Odin / Carbon) · JVM (Kotlin / Scala / Clojure
*promotion* / Groovy promotion / Ceylon) · .NET (C# checked-vs-unchecked / F# / VB.NET) · scripting (Ruby/Tcl/Raku
arbitrary · Lua `f64` · PHP) · functional (OCaml **63-bit wrap** · Haskell Int(64-wrap)/Integer(arbitrary) ·
Erlang/Elixir/Scheme/Racket/CommonLisp arbitrary · Lean/Idris/Agda) · scientific (**Julia Int64 silent wrap** ·
R/MATLAB/Octave `f64` · Fortran `ub`) · web (Dart int64 vs web-double · WAT i32/i64 wrap · TS) · mobile (Swift
**trap** · ObjC) · data (SQL dialects per-int-type wrap/error) · shell/legacy (Bash/COBOL/Ada/Pascal/Assembly).

★ Each language maps to ONE integer model; the SAME Σi structure gets a language-dependent disposition (Python/Ruby/
Clojure → EXACT; Java/C#/Julia wrap → wrap-aware or DECLINE; Swift → trap-aware; C → UB DECLINE; Lua/JS → f64 ≤2⁵³).

## The RF-1 line (stated, tested)
"80 languages" is **intake**, not coverage. The foldable subset is **language-independent** (it lives on the IR);
adding a language lets the engines *reach* that language's code, and refines *soundness* per its integer model. It
does **not** multiply the fold rate — the ~6.8% real-world ceiling is structural and measured, not a function of
language count. ★ Banned: presenting the language count as a coverage/fold-rate multiplier.
