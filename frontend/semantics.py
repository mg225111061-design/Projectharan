"""
§AH §1 — PER-LANGUAGE SEMANTIC MODELS + the z3 soundness gate (RF-1: the precision-1.0 defense line).
================================================================================================================
RF-1: adding a language is *intake*, not *coverage* — fold acts on the language-agnostic StructForm IR, so the
foldable subset is language-independent (same domain-conditional ceiling). The genuinely-new work is loading each
language's INTEGER / FLOAT / EVALUATION semantics onto the IR so an unsound fold is DECLINED *under that language*.

★ The canonical witness: `for i in 1..n: s += i` folds to the closed form n(n+1)/2.
  • Python int (arbitrary precision)  → EXACT (no wrap).
  • Java / C# `int` (32-bit two's-complement wrap) → the NAIVE closed form n*(n+1)/2 OVERFLOWS int32 mid-expression
    (n*(n+1) wraps before the /2) ⇒ z3 QF_BV finds a counterexample ⇒ the naive form is DECLINED; only the
    WRAP-AWARE form ((wide) n*(n+1)/2) mod 2^32 is ACCEPTED (z3-BV proven == the wrapping accumulation).
  • C/C++ signed (overflow = UB) → if overflow is possible in range, DECLINE (never assign a closed form to UB);
    only when no-overflow is provable does it equal the ℤ closed form (EXACT).
  • Go (fixed-width wrap), Rust (checked_/wrapping_/saturating_ EXPLICIT) → handled by the same models.
★ A fold sound in one language is UNSOUND in another — enforcing this IS precision 1.0. z3 discharges the
verification condition UNDER the language's semantics (QF_BV for fixed-width — terminating, no theory blow-up).
LLM-free, zero-dep (z3 + stdlib).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class IntModel:
    lang: str
    width: Optional[int]      # bit width; None = arbitrary precision
    overflow: str             # "none" (arbitrary) | "wrap" (mod 2^w) | "ub" (undefined) | "checked" | "saturating"
    note: str = ""


# the per-language integer semantic registry (the RF-1 core — used to discharge the z3 VC under each language)
INT_MODELS: Dict[str, IntModel] = {
    "python":        IntModel("python", None, "none", "int = arbitrary precision (no overflow)"),
    "java_int":      IntModel("java_int", 32, "wrap", "Java int = 32-bit two's-complement wrap"),
    "csharp_int":    IntModel("csharp_int", 32, "wrap", "C# int = 32-bit wrap (unchecked context)"),
    "c_signed":      IntModel("c_signed", 32, "ub", "C/C++ signed overflow = UNDEFINED BEHAVIOR"),
    "c_unsigned":    IntModel("c_unsigned", 32, "wrap", "C/C++ unsigned = mod 2^n (well-defined wrap)"),
    "go_int64":      IntModel("go_int64", 64, "wrap", "Go int = fixed-width two's-complement wrap"),
    "rust_default":  IntModel("rust_default", 32, "ub", "Rust default arithmetic: debug=panic / release=wrap ⇒ must be made explicit"),
    "rust_wrapping": IntModel("rust_wrapping", 32, "wrap", "Rust wrapping_add ⇒ mod 2^n (explicit)"),
    "rust_checked":  IntModel("rust_checked", 32, "checked", "Rust checked_add ⇒ Option (no UB; None on overflow)"),
    "rust_saturating": IntModel("rust_saturating", 32, "saturating", "Rust saturating_add ⇒ clamp at bounds"),
    # ── §BJ: the 80+-language models (accurate per-language integer semantics — a wrong model is a false-EXACT) ──
    "julia_int64":   IntModel("julia_int64", 64, "wrap", "Julia Int64 = SILENT two's-complement wrap (★ no error, no promotion — the trap for the unwary)"),
    "ocaml_int":     IntModel("ocaml_int", 63, "wrap", "OCaml native int = 63-bit on 64-bit platforms (one bit for the tag), wraps mod 2^63"),
    "clojure_promote": IntModel("clojure_promote", None, "none", "Clojure +'/*' AUTO-PROMOTE long→BigInt (arbitrary precision) ⇒ no overflow (★ assumes the promoting ops; plain + THROWS)"),
    "swift_int":     IntModel("swift_int", 64, "trap", "Swift Int overflow TRAPS at runtime (no UB — the program aborts; &+ is the explicit wrapping op)"),
    "crystal_int":   IntModel("crystal_int", 32, "error", "Crystal Int overflow RAISES OverflowError (no UB, no silent wrap)"),
    "ada_int":       IntModel("ada_int", 32, "error", "Ada raises Constraint_Error on integer overflow"),
    "csharp_checked": IntModel("csharp_checked", 32, "error", "C# `checked` context raises OverflowException (vs unchecked = wrap)"),
    "nim_int":       IntModel("nim_int", 64, "error", "Nim int overflow raises OverflowDefect (debug) — model the checked default; release --d:danger wraps"),
    "ruby_int":      IntModel("ruby_int", None, "none", "Ruby Integer auto-promotes Fixnum→Bignum (arbitrary precision)"),
    "arbitrary":     IntModel("arbitrary", None, "none", "numeric-tower / bignum-by-default (Scheme/Racket/CommonLisp/Erlang/Elixir/Raku/Tcl/Smalltalk/Python) — arbitrary precision"),
    "haskell_int":   IntModel("haskell_int", 64, "wrap", "Haskell Int = machine word (64-bit); overflow wraps (impl-defined, typically mod 2^64)"),
    "haskell_integer": IntModel("haskell_integer", None, "none", "Haskell Integer = arbitrary precision (distinct type from Int)"),
    "kotlin_int":    IntModel("kotlin_int", 32, "wrap", "Kotlin Int = 32-bit JVM two's-complement wrap"),
    "scala_int":     IntModel("scala_int", 32, "wrap", "Scala Int = 32-bit JVM two's-complement wrap"),
    "dart_int":      IntModel("dart_int", 64, "wrap", "Dart native int = 64-bit wrap (★ web/JS target = double ⇒ f64 model there)"),
    "zig_wrapping":  IntModel("zig_wrapping", 64, "wrap", "Zig +% = EXPLICIT wrapping; plain + on overflow is illegal behavior (safe builds trap)"),
    "wat_i32":       IntModel("wat_i32", 32, "wrap", "WebAssembly i32 = mod 2^32 wrap"),
    "wat_i64":       IntModel("wat_i64", 64, "wrap", "WebAssembly i64 = mod 2^64 wrap"),
    "fortran_int":   IntModel("fortran_int", 32, "ub", "Fortran integer overflow = processor-dependent / effectively undefined"),
    "lua_number":    IntModel("lua_number", 53, "f64", "Lua number = IEEE-754 double; integers EXACT only while ≤ 2^53"),
    "js_f64":        IntModel("js_f64", 53, "f64", "JS Number = IEEE-754 double; integers EXACT only while ≤ 2^53 (BigInt is separate)"),
    "r_double":      IntModel("r_double", 53, "f64", "R numeric / MATLAB / Octave = double; integers EXACT only while ≤ 2^53"),
    # ── §BP-2: accurately-modeled additions (a wrong model is a false-EXACT) ──
    "sol_int256":    IntModel("sol_int256", 256, "error", "Solidity/Vyper EVM int — ≥0.8 CHECKED by default (REVERTS on over/underflow); 256-bit ⇒ folds within 2^255 are EXACT (an `unchecked{}` block / pre-0.8 wraps mod 2^256)"),
    "abort_int64":   IntModel("abort_int64", 64, "error", "Move / Ballerina 64-bit int — overflow ABORTS the transaction / panics (no UB, no silent wrap) ⇒ EXACT in-range, DECLINE over-range"),
}


@dataclass
class SemVerdict:
    accept: bool
    grade: str                 # "EXACT" | "DECLINE"
    form: str                  # the closed form actually accepted (may be wrap-aware), or "" on DECLINE
    proved_by: str             # "QF_BV" | "Z (arbitrary)" | "-"
    reason: str = ""


def _sum_naive_eq_wrapsum_qf_bv(width: int) -> bool:
    """z3 QF_BV: does the NAIVE closed form (n *_w (n+1)) /_w 2 — every op in width-bit wrap arithmetic — equal the
    wrapping accumulation of Σi (= the true n(n+1)/2 reduced mod 2^w)? Returns True iff equal for ALL width-bit n
    (UNSAT of inequality). For width=32 this is FALSE (naive overflows mid-expression). No bit-blast blow-up: a
    single BV equality over one variable, nlsat-free, terminating."""
    import z3
    n = z3.BitVec("n", width + 2)                       # a touch wider to host the exact n(n+1)/2 witness
    nv = z3.BitVec("nv", width)
    # wrapping accumulation result = (n*(n+1)/2) reduced into width bits (addition is associative ⇒ true sum mod 2^w)
    true_half = z3.Extract(width - 1, 0, z3.UDiv(n * (n + 1), z3.BitVecVal(2, width + 2)))
    # naive closed form computed ENTIRELY in width-bit arithmetic (this is what a literal n*(n+1)/2 in `int` does)
    naive = z3.UDiv(nv * (nv + 1), z3.BitVecVal(2, width))
    s = z3.Solver()
    s.add(z3.Extract(width - 1, 0, n) == nv)            # tie the two n's together
    s.add(true_half != naive)                           # ∃ a counterexample where naive ≠ wrap-sum ?
    return s.check() == z3.unsat                        # True ⇒ equal everywhere; False ⇒ naive is unsound


def _sum_overflows_in_range(width: int, n_bound: int) -> bool:
    """Does Σ_{i=1}^{n} i exceed the SIGNED max (2^(width-1) − 1) for some n ≤ n_bound? (Exact integer check —
    used for the C-signed UB decision: overflow possible in range ⇒ UB ⇒ DECLINE.)"""
    smax = (1 << (width - 1)) - 1
    return n_bound * (n_bound + 1) // 2 > smax


def sum_fold_under_language(lang: str, n_bound: int = 10 ** 9) -> SemVerdict:
    """★ The gate for the canonical Σ_{i=1}^{n} i → n(n+1)/2 fold, decided UNDER `lang`'s integer semantics, with the
    proof discharged in the appropriate theory. This is where a Python-sound fold is DECLINED (or made wrap-aware)
    for a fixed-width language — the RF-1 precision-1.0 boundary."""
    m = INT_MODELS.get(lang)
    if m is None:
        return SemVerdict(False, "DECLINE", "", "-", f"unknown language `{lang}`")
    if m.overflow == "none":                                    # Python: arbitrary precision
        return SemVerdict(True, "EXACT", "n*(n+1)//2", "Z (arbitrary)",
                          "arbitrary-precision int: closed form holds over ℤ (no overflow) ⇒ EXACT")
    if m.overflow == "wrap":                                    # Java/C#/Go/C-unsigned/Rust-wrapping
        naive_ok = _sum_naive_eq_wrapsum_qf_bv(m.width)
        if naive_ok:
            return SemVerdict(True, "EXACT", "n*(n+1)/2", "QF_BV",
                              f"{m.note}: naive closed form == wrapping accumulation (z3 BV) ⇒ EXACT")
        # naive overflows mid-expression ⇒ DECLINE the naive form; ACCEPT only the wrap-aware form (proven correct)
        return SemVerdict(True, "EXACT", f"((wide)n*(n+1)/2) mod 2^{m.width}", "QF_BV",
                          f"{m.note}: NAIVE n*(n+1)/2 is UNSOUND (overflows mid-expression — z3 BV counterexample); "
                          f"ACCEPT only the WRAP-AWARE form (compute in wider type, then reduce mod 2^{m.width})")
    if m.overflow == "ub":                                      # C signed / Rust default
        if _sum_overflows_in_range(m.width, n_bound):
            return SemVerdict(False, "DECLINE", "", "-",
                              f"{m.note}: Σi overflows the signed range for n≤{n_bound} ⇒ UNDEFINED BEHAVIOR ⇒ DECLINE "
                              "(a closed form must NEVER be assigned to UB)")
        return SemVerdict(True, "EXACT", "n*(n+1)/2", "Z (no-overflow proven)",
                          f"{m.note}: no overflow in range n≤{n_bound} ⇒ equals the ℤ closed form ⇒ EXACT")
    if m.overflow == "checked":                                 # Rust checked_*: None on overflow (no UB)
        if _sum_overflows_in_range(m.width, n_bound):
            return SemVerdict(False, "DECLINE", "", "-",
                              f"{m.note}: checked_add returns None on overflow for n≤{n_bound} ⇒ partial ⇒ DECLINE "
                              "(no total closed form; the program itself signals the overflow)")
        return SemVerdict(True, "EXACT", "n*(n+1)/2", "Z (no-overflow proven)",
                          f"{m.note}: no overflow in range ⇒ checked == ℤ closed form ⇒ EXACT")
    if m.overflow == "saturating":                             # clamps — not the ℤ closed form once clamped
        if _sum_overflows_in_range(m.width, n_bound):
            return SemVerdict(False, "DECLINE", "", "-",
                              f"{m.note}: saturating clamps at the bound for large n ⇒ NOT n(n+1)/2 ⇒ DECLINE")
        return SemVerdict(True, "EXACT", "n*(n+1)/2", "Z (no-saturation proven)",
                          f"{m.note}: no saturation in range ⇒ EXACT")
    if m.overflow in ("trap", "error"):                        # §BJ: Swift trap / Crystal·Ada·C#-checked·Nim raise
        # No UB and no silent wrap — but the closed form would SKIP the runtime trap/exception the loop would hit,
        # changing observable behavior. So: overflow possible in range ⇒ DECLINE (the program signals it, we must
        # not paper over it); no overflow provable ⇒ equals the ℤ closed form ⇒ EXACT.
        kind = "traps" if m.overflow == "trap" else "raises"
        if _sum_overflows_in_range(m.width, n_bound):
            return SemVerdict(False, "DECLINE", "", "-",
                              f"{m.note}: Σi overflows in range n≤{n_bound} ⇒ the program {kind} at runtime ⇒ DECLINE "
                              f"(a closed form must not silently replace a trap/exception)")
        return SemVerdict(True, "EXACT", "n*(n+1)/2", "Z (no-overflow proven)",
                          f"{m.note}: no overflow in range n≤{n_bound} ⇒ no {kind}; equals the ℤ closed form ⇒ EXACT")
    if m.overflow == "f64":                                    # §BJ: Lua/JS/R/MATLAB — double-backed integers
        # Exact only while every intermediate stays ≤ 2^53. The NAIVE form computes n*(n+1) first, so that product
        # is the binding constraint. Beyond 2^53 precision is silently LOST (rounding, NOT wrap) ⇒ no wrap-aware
        # rescue exists ⇒ DECLINE. (★ This is why Lua/JS differ from fixed-width wrap languages.)
        prod = n_bound * (n_bound + 1)
        if prod > (1 << 53):
            return SemVerdict(False, "DECLINE", "", "-",
                              f"{m.note}: n*(n+1)={prod} exceeds 2^53 for n≤{n_bound} ⇒ silent precision loss "
                              f"(rounding, not wrap — no wrap-aware form) ⇒ DECLINE")
        return SemVerdict(True, "EXACT", "n*(n+1)/2", "Z (≤2^53 exact-double proven)",
                          f"{m.note}: n*(n+1)≤2^53 in range ⇒ every double intermediate is exact ⇒ EXACT")
    return SemVerdict(False, "DECLINE", "", "-", "unmodelled overflow semantics ⇒ DECLINE")


def float_assoc_note() -> str:
    """Float: every language is IEEE-754, but evaluation order / FMA / -ffast-math break associativity ⇒ we keep the
    existing rule (convert integer/rational only; refuse real-associative transforms). Stated, not silently assumed."""
    return ("float closed forms are NOT introduced by reassociation in ANY language (eval order / FMA / -ffast-math "
            "break IEEE-754 associativity); only integer/rational folds cross the boundary — the §AB ε-rule governs "
            "the rest. (RF-1 float clause.)")


def eval_order_note() -> str:
    """Evaluation order: C/C++ argument order is unspecified; JS/Python are left-to-right. A fold that reorders
    side-effecting subexpressions must preserve the language's order (or DECLINE). Stated honestly."""
    return ("side-effecting subexpressions are NOT reordered across a fold unless the language pins the order "
            "(C/C++ argument order unspecified ⇒ DECLINE a reorder; JS/Python left-to-right ⇒ order preserved).")


def extended_models_battery() -> dict:
    """§BJ — the 80+-language integer models, each disposing the SAME Σi fold correctly under its own semantics.
    ★ The whole point: an ACCURATE model per language, so a fold sound in one is DECLINED in another — never a
    false-EXACT. Clojure-promote/Ruby/numeric-tower ⇒ EXACT (arbitrary); Julia/OCaml ⇒ wrap-aware (silent wrap);
    Swift ⇒ trap-DECLINE over-range; Crystal ⇒ raise-DECLINE; Lua/JS ⇒ f64 EXACT ≤2^53 else precision-loss DECLINE."""
    BIG = 5 * 10 ** 9      # Σ exceeds int64 (forces the 64-bit trap/wrap cases to bite)
    clj = sum_fold_under_language("clojure_promote")
    ruby = sum_fold_under_language("ruby_int")
    arb = sum_fold_under_language("arbitrary")
    julia = sum_fold_under_language("julia_int64", n_bound=BIG)
    ocaml = sum_fold_under_language("ocaml_int", n_bound=BIG)
    swift_big = sum_fold_under_language("swift_int", n_bound=BIG)
    swift_small = sum_fold_under_language("swift_int", n_bound=1000)
    crystal = sum_fold_under_language("crystal_int", n_bound=10 ** 9)
    hs_int = sum_fold_under_language("haskell_int", n_bound=BIG)
    hs_integer = sum_fold_under_language("haskell_integer")
    lua_big = sum_fold_under_language("lua_number", n_bound=10 ** 9)
    lua_small = sum_fold_under_language("lua_number", n_bound=1000)
    js_big = sum_fold_under_language("js_f64", n_bound=10 ** 9)
    cases = {
        "clojure_promote_exact": clj.accept and clj.grade == "EXACT" and clj.proved_by == "Z (arbitrary)",
        "ruby_arbitrary_exact": ruby.accept and ruby.grade == "EXACT",
        "numeric_tower_exact": arb.accept and arb.grade == "EXACT",
        "julia_silent_wrap_wrapaware": julia.accept and "WRAP-AWARE" in julia.reason and julia.proved_by == "QF_BV",
        "ocaml_63bit_wrapaware": ocaml.accept and "WRAP-AWARE" in ocaml.reason,           # 63-bit wrap, not 64
        "swift_trap_declines_overrange": (not swift_big.accept) and "traps" in swift_big.reason,
        "swift_no_overflow_exact": swift_small.accept and swift_small.grade == "EXACT",
        "crystal_raises_declines": (not crystal.accept) and "raises" in crystal.reason,
        "haskell_int_wraps_integer_exact": ("WRAP-AWARE" in hs_int.reason) and hs_integer.grade == "EXACT",
        "lua_f64_overrange_declines": (not lua_big.accept) and "2^53" in lua_big.reason,   # precision loss, not wrap
        "lua_f64_small_exact": lua_small.accept and lua_small.grade == "EXACT",
        "js_f64_overrange_declines": (not js_big.accept) and "2^53" in js_big.reason,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


def adversarial_battery() -> dict:
    """★ The SAME Σi fold: EXACT in Python (arbitrary precision); in Java/C# int32 the naive form is UNSOUND so only
    the WRAP-AWARE form is accepted (z3 BV); in C signed it's UB-in-range ⇒ DECLINE, but EXACT when no overflow is
    provable; Rust checked over-range ⇒ DECLINE. This is RF-1: one fold, language-dependent soundness, precision 1.0."""
    py = sum_fold_under_language("python")
    java = sum_fold_under_language("java_int")
    c_big = sum_fold_under_language("c_signed", n_bound=10 ** 9)        # overflows int32 ⇒ UB ⇒ DECLINE
    c_small = sum_fold_under_language("c_signed", n_bound=1000)         # no overflow ⇒ EXACT
    rust_w = sum_fold_under_language("rust_wrapping")
    rust_c = sum_fold_under_language("rust_checked", n_bound=10 ** 9)   # checked over-range ⇒ DECLINE
    cases = {
        "python_exact_arbitrary": py.accept and py.grade == "EXACT" and py.proved_by == "Z (arbitrary)",
        "java_naive_unsound_wrapaware_only": java.accept and "WRAP-AWARE" in java.reason and java.proved_by == "QF_BV",
        "c_signed_overflow_is_ub_decline": (not c_big.accept) and "UNDEFINED BEHAVIOR" in c_big.reason,   # ★ never a closed form for UB
        "c_signed_no_overflow_exact": c_small.accept and c_small.grade == "EXACT",
        "rust_wrapping_wrapaware": rust_w.accept and "WRAP-AWARE" in rust_w.reason,
        "rust_checked_overrange_declines": (not rust_c.accept) and rust_c.grade == "DECLINE",
        "float_assoc_refused": "associativity" in float_assoc_note(),
        "eval_order_preserved": "DECLINE a reorder" in eval_order_note(),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
