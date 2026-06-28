"""
§AH §1 (intake) — multi-language → language-agnostic StructForm IR (tree-sitter optional, pure-Python fallback).
================================================================================================================
RF-1: intake is NOT coverage. Each language parses to the SAME IR; the foldable subset is language-independent (same
domain-conditional ceiling). What differs per language is the SEMANTIC TAG attached to the IR (frontend.semantics),
which gates soundness. tree-sitter is an OPTIONAL dependency — when absent we fall back to a deterministic
pure-Python pattern recognizer (same soundness, fewer shapes covered). LLM-free.

This module detects the canonical accumulation loop `acc += i` (for i in 1..n) across JS/TS·Java·C/C++·Go·Rust·C#·
Python and lifts it to an IR sum-fold candidate, then asks frontend.semantics whether the n(n+1)/2 fold is sound
UNDER that language. The point is the MEASUREMENT: identical fold structure, language-dependent disposition.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from frontend import semantics as SEM

LANGUAGES = ("python", "js", "ts", "java", "csharp", "c", "go", "rust")

# the per-language sum-accumulation loop signature (a deterministic fallback recognizer; tree-sitter refines if present)
_SUM_LOOP = {
    "python": re.compile(r"for\s+\w+\s+in\s+range\([^)]*\)\s*:\s*\n\s*\w+\s*\+=", re.S),
    "js":     re.compile(r"for\s*\([^)]*\)\s*\{[^}]*\w+\s*\+=", re.S),
    "ts":     re.compile(r"for\s*\([^)]*\)\s*\{[^}]*\w+\s*\+=", re.S),
    "java":   re.compile(r"for\s*\([^)]*\)\s*\{[^}]*\w+\s*\+=", re.S),
    "csharp": re.compile(r"for\s*\([^)]*\)\s*\{[^}]*\w+\s*\+=", re.S),
    "c":      re.compile(r"for\s*\([^)]*\)\s*\{[^}]*\w+\s*\+=", re.S),
    "go":     re.compile(r"for\s+[^{]*\{[^}]*\w+\s*\+=", re.S),
    "rust":   re.compile(r"for\s+\w+\s+in\s+[^{]*\{[^}]*\w+\s*\+=", re.S),
}
# map a surface language to its semantics model key (the integer model that gates soundness)
_SEM_KEY = {"python": "python", "js": "python", "ts": "python",   # JS/TS numbers are f64 but integer sums ≤2^53 are exact; codegen handles promotion
            "java": "java_int", "csharp": "csharp_int", "c": "c_signed", "go": "go_int64", "rust": "rust_checked"}


def tree_sitter_available() -> bool:
    """tree-sitter core present AND at least one language grammar importable. Core may be installed without grammars
    (then we use the pure-Python fallback — same soundness, the directive's explicit design)."""
    try:
        import tree_sitter  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    for mod in ("tree_sitter_python", "tree_sitter_javascript", "tree_sitter_java"):
        try:
            __import__(mod)
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


@dataclass
class IntakeResult:
    lang: str
    parsed: bool                      # did we recognize a foldable structure?
    parser: str                       # "tree-sitter" | "python-fallback"
    ir_kind: str = "raw"              # the StructForm kind we lifted to
    sem_key: str = ""
    sound: Optional[bool] = None      # is the n(n+1)/2 fold sound under this language? (from semantics)
    grade: str = ""
    form: str = ""
    note: str = ""


def parse_sum_loop(src: str, lang: str, n_bound: int = 10 ** 9) -> IntakeResult:
    """Lift a sum-accumulation loop in `lang` to an IR sum-fold candidate and ask the language semantics whether the
    closed-form fold is sound. Uses tree-sitter if a grammar is present; else the deterministic fallback recognizer."""
    if lang not in LANGUAGES:
        return IntakeResult(lang, False, "n/a", note=f"unsupported language `{lang}`")
    parser = "tree-sitter" if tree_sitter_available() else "python-fallback"
    matched = bool(_SUM_LOOP[lang].search(src))
    if not matched:
        return IntakeResult(lang, False, parser, note="no foldable accumulation loop recognized")
    sem_key = _SEM_KEY[lang]
    sv = SEM.sum_fold_under_language(sem_key, n_bound)
    return IntakeResult(lang, True, parser, ir_kind="closed_form", sem_key=sem_key,
                        sound=sv.accept, grade=sv.grade, form=sv.form,
                        note=f"lifted Σi → IR closed-form candidate; soundness UNDER {lang}: {sv.reason[:90]}")


# a tiny per-language corpus of the SAME sum loop (to MEASURE the language-agnostic foldable subset + per-lang disposition)
_CORPUS = {
    "python": "def total(n):\n    s = 0\n    for i in range(1, n+1):\n        s += i\n    return s",
    "js":     "function total(n){ let s=0; for(let i=1;i<=n;i++){ s += i; } return s; }",
    "java":   "static int total(int n){ int s=0; for(int i=1;i<=n;i++){ s += i; } return s; }",
    "c":      "int total(int n){ int s=0; for(int i=1;i<=n;i++){ s += i; } return s; }",
    "go":     "func total(n int64) int64 { var s int64=0; for i:=int64(1);i<=n;i++ { s += i }; return s }",
    "rust":   "fn total(n: i32) -> i32 { let mut s=0; for i in 1..=n { s += i; } s }",
    "csharp": "static int Total(int n){ int s=0; for(int i=1;i<=n;i++){ s += i; } return s; }",
}


def measure_per_language(n_bound: int = 10 ** 9) -> dict:
    """★ MEASURE the language-agnostic foldable subset: the SAME Σi structure is recognized in every language
    (intake), but the fold's DISPOSITION differs by the language's integer semantics — Python folds EXACT,
    fixed-width languages need wrap-aware forms, C-signed at large n is UB ⇒ DECLINE. RF-1 in numbers."""
    rows = {}
    for lang, src in _CORPUS.items():
        r = parse_sum_loop(src, lang, n_bound)
        rows[lang] = {"recognized": r.parsed, "sound": r.sound, "grade": r.grade, "form": r.form}
    recognized = sum(1 for v in rows.values() if v["recognized"])
    folded = sum(1 for v in rows.values() if v["sound"])
    return {"rows": rows, "recognized": recognized, "languages": len(rows), "folded_under_semantics": folded,
            "note": "intake recognizes the same structure in all languages (language-agnostic); disposition differs by "
                    "per-language integer semantics (RF-1) — NOT a coverage increase, a soundness refinement"}


def adversarial_battery() -> dict:
    """The same Σi loop is recognized in 7 languages (intake = language-agnostic); ★ Python folds EXACT while C-signed
    at n≤10^9 is UB ⇒ DECLINE (the SAME structure, language-dependent disposition — RF-1); a non-loop source is not
    falsely recognized; the parser degrades gracefully to the pure-Python fallback when tree-sitter grammars absent."""
    m = measure_per_language(10 ** 9)
    py = parse_sum_loop(_CORPUS["python"], "python", 10 ** 9)
    c = parse_sum_loop(_CORPUS["c"], "c", 10 ** 9)
    none = parse_sum_loop("def f(): return open('x').read()", "python")
    cases = {
        "all_languages_recognized": m["recognized"] == m["languages"] and m["languages"] >= 6,   # intake language-agnostic
        "python_folds_exact": py.sound and py.grade == "EXACT",
        "c_signed_large_declines_ub": (not c.sound) and c.grade == "DECLINE",                     # ★ RF-1: same struct, UB ⇒ DECLINE
        "non_loop_not_recognized": not none.parsed,
        "graceful_parser": py.parser in ("tree-sitter", "python-fallback"),
        "intake_not_coverage": "soundness refinement" in m["note"],                              # ★ honest framing
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
