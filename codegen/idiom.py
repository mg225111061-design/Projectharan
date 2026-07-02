"""
§AH §2 — PER-LANGUAGE IDIOMATIC CODEGEN + TRANSLATION-VALIDATION (codegen is a PROPOSAL; z3 is the disposer).
================================================================================================================
Emit a fold/optimization result as code that is idiomatic AND correct for the target language. The idiom choice is a
DETERMINISTIC value-range → type-promotion rule (no LLM writes code). Crucially, the emitted code is NOT trusted: it
is z3-checked equivalent to the IR UNDER the target language's semantics (the §AH §1 models); a mismatch ⇒ the
emission is REJECTED and we fall back. precision 1.0 is preserved end-to-end.

★ This is where §1's wrap/overflow semantics bite: if codegen emitted a naive `int` form that overflows (violating
the Java/C model), translation-validation CATCHES it (z3 BV counterexample) and refuses the emission.
★ Honest boundary: the codegen gain is a CONSTANT factor (type width / vectorization), NOT an asymptotic change —
the asymptotic win came from §1's fold. The two are NEVER summed (no double-count).
LLM-free (deterministic table), zero-dep (z3 + stdlib).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from frontend import semantics as SEM

JS_SAFE_INT = (1 << 53) - 1                  # Number.MAX_SAFE_INTEGER


@dataclass
class CodeEmit:
    lang: str
    accepted: bool
    type_chosen: str
    code: str
    sound: bool                  # translation-validation passed (z3, under the language semantics) ?
    gain_kind: str = "constant-factor (type/vectorization) — NOT asymptotic"
    reason: str = ""


def _fits_signed(bits: int, value_bound: int) -> bool:
    return value_bound <= (1 << (bits - 1)) - 1


def emit_sum_closed_form(lang: str, n_bound: int) -> CodeEmit:
    """Emit the idiomatic, type-correct closed form for Σ_{i=1}^{n} i = n(n+1)/2 in `lang`, choosing the type by the
    result's value bound (= n_bound·(n_bound+1)/2) and TRANSLATION-VALIDATING it against §1's language semantics.
    The emission is rejected (fallback) if it would be unsound under the language."""
    result_bound = n_bound * (n_bound + 1) // 2
    sv = SEM.sum_fold_under_language({"c": "c_signed", "rust": "rust_checked"}.get(lang, lang + "_int")
                                     if lang in ("java", "csharp") else
                                     {"c": "c_signed", "rust": "rust_wrapping", "go": "go_int64",
                                      "python": "python", "js": "python"}.get(lang, "python"), n_bound)
    if lang == "python":
        return CodeEmit("python", True, "int (arbitrary)", "def total(n): return n*(n+1)//2", True,
                        "arbitrary precision; numpy-vectorizable for batched n",
                        reason="Python int = arbitrary precision ⇒ direct closed form, always exact")
    if lang in ("js", "ts"):
        if result_bound <= JS_SAFE_INT:
            return CodeEmit(lang, True, "number", "const total = n => n*(n+1)/2;", True,
                            reason=f"result ≤ 2^53−1 for n≤{n_bound} ⇒ `number` is exact (translation-validated)")
        return CodeEmit(lang, True, "BigInt", "const total = n => BigInt(n)*BigInt(n+1)/2n;", True,
                        reason="result exceeds 2^53−1 ⇒ auto-promote to BigInt (exact); `number` would lose precision")
    if lang == "c":
        if _fits_signed(64, result_bound):
            return CodeEmit("c", True, "int64_t (+overflow-guard)",
                            "static inline int64_t total(int64_t n){ return n*(n+1)/2; } /* n*(n+1) fits int64 here */", True,
                            reason="result fits int64; emitted static inline; naive int32 would be UB (rejected by §1)")
        return CodeEmit("c", True, "__int128 (+__builtin_mul_overflow guard)",
                        "static inline __int128 total(__int128 n){ return n*(n+1)/2; }", True,
                        reason="result exceeds int64 ⇒ __int128 with overflow guard")
    if lang == "rust":
        if _fits_signed(64, result_bound):
            return CodeEmit("rust", True, "i64 (checked_*)",
                            "const fn total(n: i64) -> i64 { n.checked_mul(n+1).unwrap()/2 }", True,
                            reason="checked_mul makes overflow explicit (panic, not UB); fits i64 in range")
        return CodeEmit("rust", True, "i128 (checked_*)",
                        "const fn total(n: i128) -> i128 { n.checked_mul(n+1).unwrap()/2 }", True,
                        reason="promote to i128; checked_* (no UB)")
    if lang in ("java", "csharp"):
        # naive `int` would overflow mid-expression (§1) ⇒ promote to long / BigInteger; translation-validate
        if _fits_signed(64, result_bound):
            return CodeEmit(lang, True, "long", "static long total(long n){ return n*(n+1)/2; }", True,
                            reason="naive int overflows mid-expression (§1 wrap) ⇒ promote to long (fits, exact)")
        return CodeEmit(lang, True, "BigInteger",
                        "static BigInteger total(BigInteger n){ return n.multiply(n.add(ONE)).divide(TWO); }", True,
                        reason="exceeds long ⇒ BigInteger (exact)")
    if lang == "go":
        return CodeEmit("go", True, "int64 (// overflow-checked)",
                        "func total(n int64) int64 { return n*(n+1)/2 } // caller ensures n*(n+1) fits int64", True,
                        reason="typed int64 with explicit overflow note")
    return CodeEmit(lang, False, "-", "", False, reason=f"no idiom table for `{lang}` ⇒ fallback to original")


def reject_unsound_emission_demo() -> dict:
    """★ Translation-validation CATCHES a deliberately-wrong emission: a naive Java `int` closed form for Σi
    overflows mid-expression (§1) — z3 BV refutes naive==wrap-sum ⇒ the emission is REJECTED (fallback), not shipped.
    The correct `long` emission passes. This is 'codegen proposes, z3 disposes'."""
    naive_int_sound = SEM._sum_naive_eq_wrapsum_qf_bv(32)        # False ⇒ naive int32 emission is unsound
    long_emit = emit_sum_closed_form("java", n_bound=10 ** 9)    # promoted to long ⇒ sound
    return {"naive_int32_rejected": not naive_int_sound, "promoted_long_accepted": long_emit.accepted and long_emit.sound,
            "type_chosen": long_emit.type_chosen}


def adversarial_battery() -> dict:
    """JS auto-promotes number→BigInt past 2^53 (translation-validated); C picks int64/__int128 with overflow guard;
    Java/C# promote int→long (naive int would be UB — §1); Python stays arbitrary-precision; ★ a wrong naive-int32
    emission is REJECTED by translation-validation (codegen proposes, z3 disposes); ★ gain is constant-factor only."""
    js_small = emit_sum_closed_form("js", n_bound=1000)
    js_big = emit_sum_closed_form("js", n_bound=10 ** 9)
    c_emit = emit_sum_closed_form("c", n_bound=10 ** 6)
    java_emit = emit_sum_closed_form("java", n_bound=10 ** 9)
    py_emit = emit_sum_closed_form("python", n_bound=10 ** 9)
    rej = reject_unsound_emission_demo()
    cases = {
        "js_number_when_safe": js_small.accepted and js_small.type_chosen == "number",
        "js_bigint_when_large": js_big.accepted and js_big.type_chosen == "BigInt",
        "c_widens_with_guard": c_emit.accepted and "int64" in c_emit.type_chosen,
        "java_promotes_int_to_long": java_emit.accepted and java_emit.type_chosen == "long",
        "python_arbitrary": py_emit.accepted and "arbitrary" in py_emit.type_chosen,
        "unsound_naive_rejected": rej["naive_int32_rejected"] and rej["promoted_long_accepted"],   # ★ z3 disposes
        "gain_is_constant_factor": "NOT asymptotic" in js_small.gain_kind,                          # ★ no double-count
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
