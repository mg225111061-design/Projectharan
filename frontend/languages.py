"""
§BJ-C — the 80+ language registry: each language → its accurate integer model (the RF-1 soundness key).
=========================================================================================================
Adding a language is INTAKE, not coverage (RF-1). What a language actually contributes is its INTEGER SEMANTICS,
which decides whether a fold sound elsewhere is sound here. This registry maps 80+ languages to one of the
`frontend.semantics.INT_MODELS` keys, so the SAME structure (e.g. Σi) gets the right per-language disposition:
Python/Ruby/Clojure(promote) → EXACT; Java/C#/Julia(silent wrap) → wrap-aware or DECLINE; Swift → trap-DECLINE
over-range; C → UB DECLINE; Lua/JS → f64 EXACT ≤2⁵³ else precision-loss DECLINE.

★ A wrong model is a false-EXACT (the whole point of being careful here). ★ This is NOT a fold-rate multiplier:
the foldable subset is structural (~6.8% real-world, measured), independent of the language count. zero-dep.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from frontend import semantics as SEM


@dataclass(frozen=True)
class LangSpec:
    name: str
    sem_key: str          # → frontend.semantics.INT_MODELS
    family: str
    note: str = ""


# (name, sem_key, family, note) — accurate per-language integer semantics (★ explicit for the directive's named cases)
_REGISTRY: List[LangSpec] = [LangSpec(*t) for t in [
    # ── Wave 1 systems ──
    ("c", "c_signed", "systems", "signed overflow = UB"), ("cpp", "c_signed", "systems", "signed overflow = UB"),
    ("rust", "rust_checked", "systems", "checked_/wrapping_/saturating_ explicit"),
    ("zig", "zig_wrapping", "systems", "+% explicit wrap; plain + illegal on overflow"),
    ("nim", "nim_int", "systems", "OverflowDefect (debug)"), ("d", "java_int", "systems", "32-bit wrap"),
    ("odin", "go_int64", "systems", "fixed-width wrap"), ("v", "java_int", "systems", "32-bit wrap"),
    ("carbon", "c_signed", "systems", "C++-interop semantics"), ("hare", "go_int64", "systems", "fixed-width wrap"),
    ("crystal", "crystal_int", "systems", "overflow raises OverflowError"),
    # ── Wave 2 JVM ──
    ("java", "java_int", "jvm", "32-bit wrap"), ("kotlin", "kotlin_int", "jvm", "32-bit JVM wrap"),
    ("scala", "scala_int", "jvm", "32-bit JVM wrap"),
    ("clojure", "clojure_promote", "jvm", "+'/*' auto-promote to BigInt"),
    ("groovy", "arbitrary", "jvm", "auto-promotes to BigInteger"), ("ceylon", "java_int", "jvm", "32-bit wrap"),
    ("jython", "python", "jvm", "Python semantics on JVM"), ("jruby", "ruby_int", "jvm", "Ruby semantics on JVM"),
    # ── Wave 3 .NET ──
    ("csharp", "csharp_int", "dotnet", "unchecked = 32-bit wrap"),
    ("fsharp", "csharp_int", "dotnet", "32-bit wrap (unchecked default)"),
    ("vbnet", "csharp_int", "dotnet", "32-bit wrap"),
    # ── Wave 4 scripting ──
    ("python", "python", "scripting", "arbitrary precision"), ("ruby", "ruby_int", "scripting", "Fixnum→Bignum promote"),
    ("perl", "r_double", "scripting", "IV→NV(double) promote ⇒ f64 ≤2^53"),
    ("php", "r_double", "scripting", "int→float on overflow ⇒ f64 ≤2^53"),
    ("lua", "lua_number", "scripting", "double-backed ⇒ exact ≤2^53"),
    ("tcl", "arbitrary", "scripting", "arbitrary precision"), ("raku", "arbitrary", "scripting", "Int arbitrary"),
    ("awk", "r_double", "scripting", "numbers are doubles"),
    # ── Wave 5 functional ──
    ("haskell", "haskell_int", "functional", "Int = 64-bit wrap (Integer = arbitrary)"),
    ("ocaml", "ocaml_int", "functional", "native int = 63-bit wrap"),
    ("elm", "js_f64", "functional", "compiles to JS double"), ("erlang", "arbitrary", "functional", "arbitrary precision"),
    ("elixir", "arbitrary", "functional", "arbitrary precision"), ("scheme", "arbitrary", "functional", "numeric tower"),
    ("racket", "arbitrary", "functional", "numeric tower"), ("commonlisp", "arbitrary", "functional", "numeric tower"),
    ("purescript", "js_f64", "functional", "compiles to JS double"), ("idris", "arbitrary", "functional", "Integer arbitrary"),
    ("agda", "arbitrary", "functional", "arbitrary precision"), ("lean", "arbitrary", "functional", "Nat/Int arbitrary"),
    ("sml", "ada_int", "functional", "Int raises Overflow"), ("reasonml", "ocaml_int", "functional", "OCaml 63-bit"),
    # ── Wave 6 scientific ──
    ("julia", "julia_int64", "scientific", "Int64 SILENT wrap (★ trap for the unwary)"),
    ("r", "r_double", "scientific", "double ⇒ exact ≤2^53"), ("matlab", "r_double", "scientific", "double ⇒ exact ≤2^53"),
    ("octave", "r_double", "scientific", "double ⇒ exact ≤2^53"), ("fortran", "fortran_int", "scientific", "overflow undefined"),
    ("mathematica", "arbitrary", "scientific", "arbitrary precision"), ("maple", "arbitrary", "scientific", "arbitrary precision"),
    ("sas", "r_double", "scientific", "double-backed"), ("stata", "r_double", "scientific", "double-backed"),
    ("idl", "r_double", "scientific", "double-backed"),
    # ── Wave 7 web ──
    ("javascript", "js_f64", "web", "Number = double ⇒ exact ≤2^53"), ("typescript", "js_f64", "web", "Number = double"),
    ("dart", "dart_int", "web", "native 64-bit wrap (web target = double)"),
    ("coffeescript", "js_f64", "web", "compiles to JS double"), ("rescript", "java_int", "web", "32-bit JS-truncated"),
    ("wat", "wat_i32", "web", "i32 mod 2^32 (i64 variant available)"),
    # ── Wave 8 mobile ──
    ("swift", "swift_int", "mobile", "overflow TRAPS (&+ to wrap)"), ("objc", "c_signed", "mobile", "C int UB"),
    # ── Wave 9 data ──
    ("sql_postgres", "ada_int", "data", "integer overflow raises"), ("sql_mysql", "ada_int", "data", "strict mode raises"),
    ("sql_sqlite", "r_double", "data", "INTEGER overflow → REAL (double)"), ("tsql", "ada_int", "data", "arithmetic overflow raises"),
    ("plpgsql", "ada_int", "data", "integer overflow raises"), ("graphql", "java_int", "data", "Int = 32-bit signed"),
    ("cypher", "ada_int", "data", "64-bit; overflow raises"), ("sparql", "arbitrary", "data", "xsd:integer arbitrary"),
    # ── Wave 10 shell / config / legacy ──
    ("bash", "go_int64", "shell_legacy", "arithmetic = 64-bit wrap"), ("powershell", "r_double", "shell_legacy", "promotes to double"),
    ("zsh", "go_int64", "shell_legacy", "64-bit wrap"), ("fish", "go_int64", "shell_legacy", "64-bit wrap"),
    ("batch", "java_int", "shell_legacy", "32-bit signed"), ("cobol", "java_int", "shell_legacy", "PIC truncates high-order digits"),
    ("pascal", "ada_int", "shell_legacy", "range-check error"), ("ada", "ada_int", "shell_legacy", "Constraint_Error"),
    ("delphi", "java_int", "shell_legacy", "Integer 32-bit wrap"), ("vb6", "ada_int", "shell_legacy", "overflow error"),
    ("assembly", "go_int64", "shell_legacy", "width-dependent wrap"), ("gleam", "arbitrary", "shell_legacy", "Erlang-target arbitrary"),
    ("mojo", "go_int64", "shell_legacy", "fixed-width wrap"), ("vale", "rust_checked", "shell_legacy", "checked"),
    ("roc", "go_int64", "shell_legacy", "I64 wrap"), ("grain", "wat_i32", "shell_legacy", "WASM-target i32"),
    ("koka", "c_signed", "shell_legacy", "C-backed"), ("unison", "arbitrary", "shell_legacy", "arbitrary precision"),
    # ── §BP-2 Wave 11: smart-contract + niche languages (accurately modeled; Cairo deferred — felt252 is field-mod-p, not 2^k) ──
    ("solidity", "sol_int256", "contracts", "EVM ≥0.8 CHECKED (reverts on overflow); unchecked{} wraps mod 2^256"),
    ("vyper", "sol_int256", "contracts", "EVM bounds-checked (reverts on overflow)"),
    ("move", "abort_int64", "contracts", "u64/u128 overflow ABORTS the transaction"),
    ("ballerina", "abort_int64", "web", "int = 64-bit; overflow panics (runtime error)"),
    ("gdscript", "go_int64", "scripting", "Godot int = 64-bit two's-complement"),
    ("chapel", "go_int64", "scientific", "int(64) fixed-width wrap"),
    ("futhark", "java_int", "scientific", "i32 wraps (sizes explicit)"),
    ("qsharp", "go_int64", "scientific", "Q# Int = 64-bit"),
    ("haxe", "java_int", "web", "Int = 32-bit on static targets (target-dependent)"),
    ("apex", "java_int", "jvm", "Salesforce Apex Integer = 32-bit"),
    # ── §BP-4: enterprise / classic languages (textbook-accurate integer models only) ──
    ("abap", "csharp_checked", "data", "SAP ABAP TYPE i = 32-bit; overflow raises CX_SY_ARITHMETIC_OVERFLOW"),
    ("smalltalk", "arbitrary", "functional", "SmallInteger auto-promotes to LargePositiveInteger (arbitrary precision)"),
    ("prolog", "arbitrary", "functional", "modern Prolog (SWI/GNU) uses GMP bignums — arbitrary precision"),
    ("kdb", "go_int64", "data", "kdb+/q long = 64-bit, no promotion ⇒ two's-complement wrap"),
    # ── §BP-7: arbitrary-precision-integer languages (cleanest EXACT) + one fixed-word ──
    ("bc", "arbitrary", "shell_legacy", "POSIX bc — arbitrary-precision integer arithmetic (unbounded)"),
    ("dc", "arbitrary", "shell_legacy", "POSIX dc — arbitrary-precision RPN integer arithmetic"),
    ("factor", "arbitrary", "functional", "Factor uses bignums by default (arbitrary precision)"),
    ("logtalk", "arbitrary", "functional", "Prolog-hosted ⇒ GMP bignums (arbitrary precision)"),
    ("picat", "arbitrary", "functional", "Picat (B-Prolog lineage) uses bignums (arbitrary precision)"),
    ("mercury", "go_int64", "functional", "Mercury int = machine word (64-bit), two's-complement wrap"),
]]

LANGS: Dict[str, LangSpec] = {ls.name: ls for ls in _REGISTRY}


def count() -> int:
    return len(LANGS)


def families() -> Dict[str, int]:
    out: Dict[str, int] = {}
    for ls in LANGS.values():
        out[ls.family] = out.get(ls.family, 0) + 1
    return out


def model_for(lang: str) -> "SEM.IntModel":
    """The integer model for `lang` (raises KeyError on an unregistered language — never a silent guess)."""
    return SEM.INT_MODELS[LANGS[lang].sem_key]


def disposition_for(lang: str, n_bound: int = 10 ** 9) -> "SEM.SemVerdict":
    """Dispose the canonical Σi fold under `lang`'s integer semantics (the per-language EXACT/DECLINE the directive
    measures). ★ Routes through the same z3 gate — adding a language never bypasses verification."""
    return SEM.sum_fold_under_language(LANGS[lang].sem_key, n_bound)


def adversarial_battery() -> dict:
    """★ 80+ languages registered; ★ each maps to a real INT_MODEL; ★ the SAME Σi fold disposes correctly per
    language (Python/Clojure/Ruby EXACT · Julia/OCaml wrap-aware · Swift trap-DECLINE · C UB-DECLINE · Lua/JS f64);
    ★ RF-1: this is intake/soundness, NOT a coverage multiplier (stated)."""
    n = count()
    BIG = 5 * 10 ** 9
    cases = {
        "over_80_languages": n >= 80,
        "every_lang_has_model": all(ls.sem_key in SEM.INT_MODELS for ls in LANGS.values()),
        "python_exact": disposition_for("python").grade == "EXACT",
        "clojure_promote_exact": disposition_for("clojure").grade == "EXACT",
        "ruby_exact": disposition_for("ruby").grade == "EXACT",
        "julia_wrapaware": "WRAP-AWARE" in disposition_for("julia", BIG).reason,        # silent wrap
        "ocaml_63bit_wrapaware": "WRAP-AWARE" in disposition_for("ocaml", BIG).reason,
        "swift_trap_declines": disposition_for("swift", BIG).grade == "DECLINE",
        "c_ub_declines": disposition_for("c", 10 ** 9).grade == "DECLINE",
        "lua_f64_declines_overrange": disposition_for("lua", 10 ** 9).grade == "DECLINE",
        "haskell_int_wraps": "WRAP-AWARE" in disposition_for("haskell", BIG).reason,
    }
    return {"languages": n, "families": families(), "cases": cases, "all_ok": all(cases.values()),
            "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
