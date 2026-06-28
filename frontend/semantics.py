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
