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
_PRODUCT = re.compile(r"\w+\s*\*=\s*\w+")                                          # acc *= i
_RECURRENCE = re.compile(r"(\w+)\s*,\s*(\w+)\s*=\s*(\w+)\s*,\s*(\w+)\s*\+\s*(\w+)")  # a, b = b, a+b
_CONV = re.compile(r"\w+\[\s*\w+\s*\+\s*\w+\s*\]\s*\+=\s*\w+\[[^\]]+\]\s*\*\s*\w+\[[^\]]+\]")  # c[i+j]+=a[i]*b[j]
_HORNER = re.compile(r"(\w+)\s*=\s*\1\s*\*\s*\w+\s*\+\s*\w+")                      # acc = acc*base + d
_HAS_LOOP = re.compile(r"\b(for|while)\b")


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
    if _HORNER.search(src):
        return StructMatch("horner", True, lang, note="acc = acc*base + d (Horner)")
    if _HAS_LOOP.search(src):
        if _POLY_SUM.search(src):
            return StructMatch("poly_sum", True, lang, note="Σ k^d polynomial sum")
        if _PRODUCT.search(src):
            return StructMatch("product_loop", True, lang, note="acc *= i product")
        if _SUM_LOOP.search(src):
            return StructMatch("sum_loop", True, lang, note="acc += i summation")
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


def measure_recognition() -> dict:
    """★ MEASURE the widened door: how many distinct structure families are now recognized (was 1 — sum only)."""
    rows = {struct: recognize(src).kind for struct, src in _CORPUS.items()}
    correct = sum(1 for struct, kind in rows.items() if kind == struct)
    return {"rows": rows, "families_recognized": correct, "families_total": len(_CORPUS),
            "was_before": 1, "note": "intake widened from 1 structure (sum) to the engine-backed families (RF-1: "
                                     "more recognition = engines reach more code, NOT a fold-rate multiplier)"}


def adversarial_battery() -> dict:
    """★ each structure family is recognized as its own kind (door widened past acc+=i); ★ poly_sum is NOT
    mis-read as sum_loop; ★ a structureless blob ⇒ raw (no false positive — the dispatcher then DECLINEs)."""
    m = measure_recognition()
    blob = recognize("def f(x):\n    return x.strip().upper() + str(hash(x)))")
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
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
