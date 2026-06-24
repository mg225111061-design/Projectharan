"""
§4 — MEASURED loop-collapse coverage: the honest, DOMAIN-CONDITIONAL delta (no fabricated coverage number).
=========================================================================================================
A representative corpus of LOOPS is run through the unified §2/§4 collapse decision (`engine_bridge._loop_collapse`)
and graded: how many collapse to a closed / O(log n) form WITH an EXACT certificate, how many are PROVEN
irreducible (a first-class result — "this loop has no closed form"), and how many honestly DECLINE (not in the
decided class). The deliverable is a MEASURED coverage inventory, DOMAIN-CONDITIONAL by construction: these are
structured loops (power sums, hypergeometric sums, C-finite recurrences); a product loop, a non-hypergeometric
sum, or glue code DECLINEs. This is NEVER a general-purpose-accelerator claim — it is the honest measured share of
a structured corpus, exactly as the MATH §7 benchmark reports measured coverage, never a score.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class LoopCase:
    name: str
    source: str
    expect: str                       # COLLAPSE | IRREDUCIBLE | DECLINE


def _corpus() -> List[LoopCase]:
    def sumf(body: str) -> str:
        return f"def f(n):\n    s = 0\n    for k in range(1, n + 1):\n        s += {body}\n    return s"

    def rec(init: str, upd: str) -> str:
        return f"def f(n):\n    a, b = {init}\n    for _ in range(n):\n        a, b = {upd}\n    return a"

    return [
        # ── Σ-loops that COLLAPSE to an O(1) closed form (Gosper / Faulhaber) ──
        LoopCase("Σk", sumf("k"), "COLLAPSE"),
        LoopCase("Σk²", sumf("k * k"), "COLLAPSE"),
        LoopCase("Σk³", sumf("k ** 3"), "COLLAPSE"),
        LoopCase("Σk·2^k", sumf("k * 2 ** k"), "COLLAPSE"),
        LoopCase("Σ1/(k(k+1))", sumf("1 / (k * (k + 1))"), "COLLAPSE"),
        # ── Σ-loops PROVEN irreducible (no hypergeometric / rational closed form) ──
        LoopCase("Σ1/k (harmonic)", sumf("1 / k"), "IRREDUCIBLE"),
        LoopCase("Σ1/(k²+1)", sumf("1 / (k * k + 1)"), "IRREDUCIBLE"),
        # ── C-finite state-update loops that COLLAPSE to an O(log n) companion ──
        LoopCase("Fibonacci", rec("0, 1", "b, a + b"), "COLLAPSE"),
        LoopCase("Pell-like", rec("0, 1", "b, 2 * b + a"), "COLLAPSE"),
        LoopCase("Lucas-ish", rec("2, 1", "b, a + b"), "COLLAPSE"),
        # ── NOT in the decided class → honest DECLINE (keep the loop) ──
        LoopCase("factorial (Π)", "def f(n):\n    p = 1\n    for k in range(1, n + 1):\n        p *= k\n    return p", "DECLINE"),
        LoopCase("Σ(k mod 3)", sumf("k % 3"), "DECLINE"),
        LoopCase("glue (no loop)", "def f(c):\n    return c.get('a', 1)", "DECLINE"),
    ]


def classify(source: str) -> tuple:
    """Return (label, grade, has_cert) for a loop. label ∈ COLLAPSE | IRREDUCIBLE | DECLINE."""
    from webapi.engine_bridge import _loop_collapse           # the unified §2/§4 entry
    col = _loop_collapse(source)
    if col is None:
        return ("DECLINE", None, False)
    if col["status"] in ("CLOSED_FORM", "COLLAPSED"):
        return ("COLLAPSE", col.get("grade"), bool(col.get("certificate")))
    if col["status"] == "NO_CLOSED_FORM":
        return ("IRREDUCIBLE", col.get("grade"), bool(col.get("certificate")))
    return ("DECLINE", None, False)


@dataclass
class CoverageReport:
    total: int
    collapse: int
    irreducible: int
    decline: int
    matched_expect: int
    certified: int                    # COLLAPSE/IRREDUCIBLE rows carrying an EXACT certificate
    rows: list


def run() -> CoverageReport:
    rows = []
    collapse = irreducible = decline = matched = certified = 0
    for c in _corpus():
        label, grade, has_cert = classify(c.source)
        collapse += int(label == "COLLAPSE")
        irreducible += int(label == "IRREDUCIBLE")
        decline += int(label == "DECLINE")
        ok = (label == c.expect)
        matched += int(ok)
        cert_ok = (label == "DECLINE") or (grade == "EXACT" and has_cert)
        if label in ("COLLAPSE", "IRREDUCIBLE") and grade == "EXACT" and has_cert:
            certified += 1
        rows.append((c.name, c.expect, label, grade, ok, cert_ok))
    return CoverageReport(len(rows), collapse, irreducible, decline, matched, certified, rows)


def format_report(r: CoverageReport) -> str:
    decided = r.collapse + r.irreducible
    return (f"loop-collapse coverage — {r.total} loops (DOMAIN-CONDITIONAL: structured loops only)\n"
            f"  COLLAPSE={r.collapse}  IRREDUCIBLE(proven)={r.irreducible}  DECLINE(out-of-class)={r.decline}\n"
            f"  matched-expected: {r.matched_expect}/{r.total}  ·  certified (EXACT) among decided: {r.certified}/{decided}\n"
            f"  ★ this is the MEASURED share of a STRUCTURED corpus — never a general-purpose-accelerator claim ★")
