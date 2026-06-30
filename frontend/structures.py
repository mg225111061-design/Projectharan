"""
§BJ-A — `_STRUCT_RECOGNIZERS`: widen the intake door beyond the single `acc += i` summation loop.
====================================================================================================
The bottleneck was that intake matched ONE structure, so every engine sat unreachable. This module recognizes
the structure FAMILIES our engines already handle, language-agnostically (deterministic regex fallbacks; tree-
sitter refines on Render), and lifts each to a `StructMatch` whose `kind` the dispatcher (frontend.dispatch)
routes to the right engine:

  sum_loop          acc += i                      → fold / Faulhaber
  poly_sum          acc += i*i  /  i**d            → fold / Faulhaber (Σk^d)
  product_loop      acc *= i                       → fold engine (log-sum / factorial)
  linear_recurrence a, b = b, a+b  (Fibonacci)     → C-finite companion-matrix power
  convolution       c[i+j] += a[i]*b[j]            → NTT (exact)
  horner            acc = acc*base + d             → extract parse_arith
  checksum          CRC/Adler/Luhn pattern         → extract checksum (delegated recognizer)

★ Recognition is deterministic and conservative: a shape we don't recognize is `raw` (NOT a false match) — the
dispatcher then DECLINEs rather than guessing. Recognizing a structure does NOT assert foldability; it only opens
the door — the engine + the z3 gate decide soundness (precision 1.0). zero-dep (re + the extract recognizers).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StructMatch:
    kind: str                         # the StructForm-ish kind the dispatcher routes on
    matched: bool
    lang: str = "generic"
    params: Dict[str, object] = field(default_factory=dict)
    recognizer: str = "regex-fallback"
    note: str = ""


# ── language-agnostic shape patterns (C-family + Python surface) ───────────────────────────────────────
_POLY_SUM = re.compile(r"\w+\s*\+=\s*(\w+\s*\*\s*\w+|\w+\s*\*\*\s*\d+)")          # acc += i*i | i**2
_SUM_LOOP = re.compile(r"\w+\s*\+=\s*\w+\s*[\n;}]")                                # acc += i  (a bare variable)
# ★ §BP-5: the NON-augmented accumulation `acc = acc + …` (explicit form; common where += is absent / for beginners)
_POLY_ASSIGN = re.compile(r"(\w+)\s*=\s*\1\s*\+\s*(\w+\s*\*\s*\w+|\w+\s*\*\*\s*\d+)")  # acc = acc + i*i  (var reused ⇒ accumulation)
_SUM_ASSIGN = re.compile(r"(\w+)\s*=\s*\1\s*\+\s*\w+")                             # acc = acc + i   (var reused; NOT x=y+z)
# ★ §BP-6: the operand-REVERSED non-augmented accumulation `acc = … + acc` (addition commutes ⇒ same Σ)
_POLY_ASSIGN_R = re.compile(r"(\w+)\s*=\s*(\w+\s*\*\s*\w+|\w+\s*\*\*\s*\d+)\s*\+\s*\1")  # acc = i*i + acc
_SUM_ASSIGN_R = re.compile(r"(\w+)\s*=\s*\w+\s*\+\s*\1(?!\w)")                     # acc = i + acc  (var reused at the END)
_PRODUCT = re.compile(r"\w+\s*\*=\s*\w+")                                          # acc *= i
_RECURRENCE = re.compile(r"(\w+)\s*,\s*(\w+)\s*=\s*(\w+)\s*,\s*(\w+)\s*\+\s*(\w+)")  # a, b = b, a+b
# ★ §BP-8: coefficient-bearing 2-term linear recurrence as a tuple-swap — a, b = b, <expr containing a> (Pell/Lucas/…)
_RECURRENCE2 = re.compile(r"(\w+)\s*,\s*(\w+)\s*=\s*\2\s*,\s*[^=\n;]*\b\1\b")        # x, y = y, p*y+q*x
# ★ §BP-11: 3-term linear recurrence as a left-shift tuple-rotation — a, b, c = b, c, <expr> (Tribonacci/Padovan/Perrin)
_RECURRENCE3 = re.compile(r"(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*=\s*\2\s*,\s*\3\s*,\s*[^=\n;]+")  # a,b,c = b,c, p*c+q*b+r*a
_CONV = re.compile(r"\w+\[\s*\w+\s*\+\s*\w+\s*\]\s*\+=\s*\w+\[[^\]]+\]\s*\*\s*\w+\[[^\]]+\]")  # c[i+j]+=a[i]*b[j]
_HORNER = re.compile(r"(\w+)\s*=\s*\1\s*\*\s*\w+\s*\+\s*\w+")                      # acc = acc*base + d (var-first)
_HORNER2 = re.compile(r"(\w+)\s*=\s*\w+\s*\*\s*\1\s*\+\s*\w+")                     # acc = base*acc + d (const-first, e.g. 10*acc+d)
_HAS_LOOP = re.compile(r"\b(for|while)\b")

# ── functional / builtin summation (the loop IS the comprehension; no explicit `acc += i`) ─────────────
#   sum(i*i for i in range(...)) | sum(i**2 ...)  → poly_sum   (Σ k^d)
_POLY_SUM_FUNC = re.compile(r"sum\s*\(\s*[^)]*?(\w+\s*\*\s*\w+|\w+\s*\*\*\s*\d+)[^)]*?\bfor\b[^)]*?\brange\b", re.S)
#   sum(range(...)) | sum(i for i in range(...))  → sum_loop   (Σ k)  — REQUIRE range ⇒ a Faulhaber series,
#   never a bare sum(arbitrary_list) (that stays raw ⇒ the dispatcher DECLINEs — conservative, no false match)
_SUM_FUNC = re.compile(r"sum\s*\(\s*(?:range\s*\(|[^)]*?\bfor\b[^)]*?\brange\b)", re.S)
#   reduce(lambda a,b: a+b, range(...)) / functools.reduce additive over a range → sum_loop
_REDUCE_SUM = re.compile(r"reduce\s*\(\s*lambda\s+\w+\s*,\s*\w+\s*:\s*\w+\s*\+\s*\w+[^)]*?\brange\b", re.S)


def _functional_sum_kind(src: str) -> Optional[str]:
    """Recognize a Σ written as a builtin/functional comprehension over a range (sum()/reduce) — poly before
    plain. Conservative: REQUIRES `range`, so sum(arbitrary_list) does NOT fire (stays raw ⇒ honest DECLINE)."""
    if _POLY_SUM_FUNC.search(src):
        return "poly_sum"
    if _SUM_FUNC.search(src) or _REDUCE_SUM.search(src):
        return "sum_loop"
    return None


def _checksum_kind(src: str) -> Optional[str]:
    """Delegate checksum recognition to the extract catalog's own recognizer (CRC/Adler/Luhn/…)."""
    try:
        from extract.checksum import recognize as _recog
        k = _recog(src)
        return k if k and k != "none" else None
    except Exception:  # noqa: BLE001
        return None


# priority order: most specific first (convolution / recurrence / horner / checksum before the generic sums)
def recognize(src: str, lang: str = "generic") -> StructMatch:
    """Recognize the richest structure present and lift it to a StructMatch. Conservative: no recognizer fires ⇒
    `raw` (never a false positive — the dispatcher will DECLINE)."""
    cs = _checksum_kind(src)
    if cs:
        return StructMatch("checksum", True, lang, {"checksum": cs}, note=f"checksum pattern `{cs}`")
    if _CONV.search(src):
        return StructMatch("convolution", True, lang, note="c[i+j] += a[i]*b[j] convolution")
    m = _RECURRENCE.search(src)
    if m and m.group(1) == m.group(4):                                   # a,b = b,a+b  ⇒ b reused as next a
        return StructMatch("linear_recurrence", True, lang,
                           {"vars": [m.group(1), m.group(2)]}, note="Fibonacci-style linear recurrence")
    m3 = _RECURRENCE3.search(src)                                        # ★ §BP-11: 3-term left-shift rotation (Tribonacci/…)
    if m3:
        return StructMatch("linear_recurrence", True, lang,
                           {"vars": [m3.group(1), m3.group(2), m3.group(3)]}, note="3-term linear recurrence (left-shift tuple-rotation)")
    m2 = _RECURRENCE2.search(src)                                        # ★ §BP-8: coefficient-bearing tuple-swap (Pell/Lucas)
    if m2:
        return StructMatch("linear_recurrence", True, lang,
                           {"vars": [m2.group(1), m2.group(2)]}, note="2-term linear recurrence (coefficient-bearing tuple-swap)")
    if _HORNER.search(src) or _HORNER2.search(src):                      # ★ §BP-3: either operand order (acc*b+d | b*acc+d)
        return StructMatch("horner", True, lang, note="acc = acc*base + d (Horner; either operand order)")
    fk = _functional_sum_kind(src)                                       # sum()/reduce over a range (no acc+=i)
    if fk:
        return StructMatch(fk, True, lang, recognizer="regex-fallback",
                           note=f"{'Σk^d' if fk == 'poly_sum' else 'Σk'} via builtin sum()/reduce over range")
    if _HAS_LOOP.search(src):
        if _POLY_SUM.search(src):
            return StructMatch("poly_sum", True, lang, note="Σ k^d polynomial sum")
        if _PRODUCT.search(src):
            return StructMatch("product_loop", True, lang, note="acc *= i product")
        if _SUM_LOOP.search(src):
            return StructMatch("sum_loop", True, lang, note="acc += i summation")
        if _POLY_ASSIGN.search(src) or _POLY_ASSIGN_R.search(src):        # ★ §BP-5/-6: acc = acc + i*i | i*i + acc
            return StructMatch("poly_sum", True, lang, note="Σ k^d via acc = acc + i*i (non-augmented, either order)")
        if _SUM_ASSIGN.search(src) or _SUM_ASSIGN_R.search(src):          # ★ §BP-5/-6: acc = acc + i | i + acc
            return StructMatch("sum_loop", True, lang, note="Σ k via acc = acc + i (non-augmented, either order)")
    return StructMatch("raw", False, lang, note="no known structure recognized ⇒ raw (dispatcher will DECLINE)")


# a tiny per-structure corpus (the SAME shape across languages — used to MEASURE recognition breadth)
_CORPUS = {
    "sum_loop":          "def f(n):\n s=0\n for i in range(1,n+1): s += i\n return s",
    "poly_sum":          "def f(n):\n s=0\n for i in range(1,n+1): s += i*i\n return s",
    "product_loop":      "def f(n):\n p=1\n for i in range(1,n+1): p *= i\n return p",
    "linear_recurrence": "def fib(n):\n a, b = 0, 1\n for _ in range(n): a, b = b, a+b\n return a",
    "convolution":       "for i in range(n):\n  for j in range(m):\n   c[i+j] += a[i]*b[j]",
    "horner":            "def ev(ds, x):\n acc=0\n for d in ds: acc = acc*x + d\n return acc",
    "checksum":          "def luhn(ds):\n s=0\n for i,d in enumerate(ds): s += d if i%2 else (d*2 - 9 if d*2>9 else d*2)\n return s%10==0",
}


# ★ §BP-1: the SAME Σ written functionally (builtin sum()/reduce/generator) — previously `raw`, now recognized.
#   These map to the EXISTING sum_loop/poly_sum kinds (the fold engine + language z3 gate decide soundness).
_FUNCTIONAL_CORPUS = {
    "sum_range":      ("sum_loop", "def f(n):\n return sum(range(1, n+1))"),
    "sum_gen":        ("sum_loop", "def f(n):\n return sum(i for i in range(1, n+1))"),
    "poly_gen":       ("poly_sum", "def f(n):\n return sum(i*i for i in range(1, n+1))"),
    "poly_pow_gen":   ("poly_sum", "def f(n):\n return sum(i**2 for i in range(1, n+1))"),
    "reduce_sum":     ("sum_loop", "from functools import reduce\ndef f(n):\n return reduce(lambda a,b: a+b, range(1, n+1))"),
}


def measure_recognition() -> dict:
    """★ MEASURE the widened door: how many distinct structure families are now recognized (was 1 — sum only),
    PLUS (§BP-1) the functional-summation intake (sum()/reduce over a range, previously `raw`)."""
    rows = {struct: recognize(src).kind for struct, src in _CORPUS.items()}
    correct = sum(1 for struct, kind in rows.items() if kind == struct)
    func_rows = {name: recognize(src).kind for name, (exp, src) in _FUNCTIONAL_CORPUS.items()}
    func_ok = sum(1 for name, (exp, _src) in _FUNCTIONAL_CORPUS.items() if func_rows[name] == exp)
    return {"rows": rows, "families_recognized": correct, "families_total": len(_CORPUS),
            "functional_rows": func_rows, "functional_recognized": func_ok,
            "functional_total": len(_FUNCTIONAL_CORPUS),
            "was_before": 1, "note": "intake widened from 1 structure (sum) to the engine-backed families + the "
                                     "functional Σ idioms (sum()/reduce/generator over range) (RF-1: more "
                                     "recognition = engines reach more code, NOT a fold-rate multiplier)"}


def adversarial_battery() -> dict:
    """★ each structure family is recognized as its own kind (door widened past acc+=i); ★ poly_sum is NOT
    mis-read as sum_loop; ★ a structureless blob ⇒ raw (no false positive — the dispatcher then DECLINEs)."""
    m = measure_recognition()
    blob = recognize("def f(x):\n    return x.strip().upper() + str(hash(x)))")
    sum_arbitrary = recognize("def f(xs):\n return sum(xs)")              # ★ no range ⇒ must NOT fire (stays raw)
    cases = {
        "sum_recognized": m["rows"]["sum_loop"] == "sum_loop",
        "poly_distinct_from_sum": m["rows"]["poly_sum"] == "poly_sum",
        "product_recognized": m["rows"]["product_loop"] == "product_loop",
        "recurrence_recognized": m["rows"]["linear_recurrence"] == "linear_recurrence",
        "convolution_recognized": m["rows"]["convolution"] == "convolution",
        "horner_recognized": m["rows"]["horner"] == "horner",
        "checksum_recognized": m["rows"]["checksum"] == "checksum",
        "all_families_recognized": m["families_recognized"] == m["families_total"],
        "structureless_is_raw": not blob.matched and blob.kind == "raw",       # ★ no false positive
        "door_widened": m["families_total"] > m["was_before"],
        # ★ §BP-1: the functional Σ idioms (sum()/reduce/generator over range) are now recognized
        "functional_sum_recognized": m["functional_recognized"] == m["functional_total"],
        "sum_arbitrary_is_raw": sum_arbitrary.kind == "raw",                   # ★ sum(xs) w/o range ⇒ no false match
        # ★ §BP-3: Horner recognized in EITHER operand order (acc*base+d AND base*acc+d, e.g. 10*acc+d)
        "horner_const_first": recognize("def p(ds):\n acc=0\n for d in ds: acc = 10*acc + d\n return acc").kind == "horner",
        "horner_var_first_still": recognize("def p(ds,b):\n acc=0\n for d in ds: acc = acc*b + d\n return acc").kind == "horner",
        "non_horner_is_not_horner": recognize("def f(a,b,c):\n return a*b + c").kind != "horner",   # ★ x=a*b+c (no var reuse) ⇒ no false match
        # ★ §BP-5: non-augmented accumulation `acc = acc + …` recognized (was raw); x=y+z (no var reuse) is NOT
        "sum_assign_recognized": recognize("def f(n):\n s=0\n for i in range(1,n+1): s = s + i\n return s").kind == "sum_loop",
        "poly_assign_recognized": recognize("def f(n):\n s=0\n for i in range(1,n+1): s = s + i*i\n return s").kind == "poly_sum",
        "non_accumulation_is_raw": recognize("def f(n):\n z=0\n for i in range(n): z = x + y\n return z").kind == "raw",  # ★ no var reuse ⇒ no false match
        # ★ §BP-6: operand-REVERSED non-augmented accumulation (acc = i + acc / i*i + acc) — addition commutes
        "sum_assign_reversed": recognize("def f(n):\n s=0\n for i in range(1,n+1): s = i + s\n return s").kind == "sum_loop",
        "poly_assign_reversed": recognize("def f(n):\n s=0\n for i in range(1,n+1): s = i*i + s\n return s").kind == "poly_sum",
        # ★ §BP-8: coefficient-bearing 2-term linear recurrence (Pell a,b=b,2*b+a) recognized (was raw); not a false-match on a plain assign
        "pell_recurrence_recognized": recognize("a, b = b, 2*b + a").kind == "linear_recurrence",
        "lucas_recurrence_recognized": recognize("x, y = y, y + x").kind == "linear_recurrence",
        "swap_no_reuse_not_recurrence": recognize("a, b = b, c + d").kind != "linear_recurrence",  # ★ no reuse of a ⇒ not a recurrence
        # ★ §BP-11: 3-term left-shift rotation (Tribonacci a,b,c=b,c,a+b+c) recognized → reaches the order-3 C-finite tier
        "tribonacci_recognized": recognize("a, b, c = b, c, a + b + c").kind == "linear_recurrence",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
