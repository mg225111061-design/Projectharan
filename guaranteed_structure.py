"""
NATIVE ARSENAL — M10 guaranteed-structure-by-size (in-repo, zero external dep, CONSTRUCTIVE).
=============================================================================================
Where the size of an instance FORCES a substructure, extract it constructively with a directly-checkable witness:
  • Erdős–Szekeres / Dilworth — any sequence of length n contains a monotone subsequence of length ≥ ⌈√n⌉
    (length > (r−1)(s−1) ⇒ an increasing run of r or a decreasing run of s). Witness: the monotone subsequence.
  • Pigeonhole-on-size — a run of states longer than the state count repeats a state ⇒ a cycle. Witness: (i,j).
  • Ramsey small-case — any 2-colouring of the edges of K_n (n ≥ 6 ⇒ R(3,3)) has a monochromatic triangle.
    Witness: three mutually same-coloured vertices.
Mechanism ⑩. EXACT-with-certificate above the forcing threshold; BELOW threshold (no guarantee) ⇒ honest DECLINE.
This is the CONSTRUCTIVE counterpart to the non-constructive Robertson–Seymour bound (which stays deferred).
"""
from __future__ import annotations

from typing import List, Sequence

import kernel_verdict as KV


def longest_monotone(seq: Sequence) -> tuple:
    """Return (kind, subsequence) for the longer of the longest strictly-increasing / strictly-decreasing
    subsequences (O(n²) DP — exact, with the actual indices)."""
    n = len(seq)
    if n == 0:
        return ("increasing", [])
    best = ("increasing", [])
    for inc in (True, False):
        L = [1] * n
        prev = [-1] * n
        for i in range(n):
            for j in range(i):
                if (seq[j] < seq[i]) if inc else (seq[j] > seq[i]):
                    if L[j] + 1 > L[i]:
                        L[i] = L[j] + 1
                        prev[i] = j
        end = max(range(n), key=lambda i: L[i])
        sub = []
        while end != -1:
            sub.append(seq[end])
            end = prev[end]
        sub.reverse()
        if len(sub) > len(best[1]):
            best = ("increasing" if inc else "decreasing", sub)
    return best


def _is_monotone(sub, kind) -> bool:
    return all((sub[i] < sub[i + 1]) if kind == "increasing" else (sub[i] > sub[i + 1]) for i in range(len(sub) - 1))


def erdos_szekeres_grade(seq) -> KV.Verdict:
    """Extract the forced monotone subsequence and certify length ≥ ⌈√n⌉ (the Erdős–Szekeres guarantee)."""
    import math
    n = len(seq)
    if n < 2:
        return KV.decline("M10.erdos_szekeres: sequence too short (n<2) — no forcing ⇒ DECLINE", "guaranteed_structure")
    thresh = math.ceil(math.sqrt(n))
    kind, sub = longest_monotone(seq)
    if len(sub) < thresh or not _is_monotone(sub, kind):
        return KV.decline(f"M10.erdos_szekeres: longest monotone run {len(sub)} < ⌈√{n}⌉={thresh} (bug guard) ⇒ DECLINE",
                          "guaranteed_structure")
    cert = KV.Cert(KV.EXACT, "forced_monotone_subsequence", passed=True, check_cost="re-verify monotone + length ≥ ⌈√n⌉",
                   detail=f"Erdős–Szekeres: a length-{n} sequence forces a {kind} subsequence of length ≥ {thresh}; "
                          f"witness (len {len(sub)}): {sub[:12]}{'…' if len(sub) > 12 else ''}")
    return KV.exact({"kind": kind, "subsequence": sub, "length": len(sub), "threshold": thresh},
                    "guaranteed_structure", "Erdős–Szekeres extractor", cert)


def pigeonhole_cycle_grade(states) -> KV.Verdict:
    """A run longer than the number of distinct states repeats a state ⇒ a cycle witness (i<j, states[i]==states[j])."""
    seen = {}
    for j, s in enumerate(states):
        key = s if isinstance(s, (int, str, tuple, bool)) else repr(s)
        if key in seen:
            i = seen[key]
            cert = KV.Cert(KV.EXACT, "pigeonhole_repeated_state", passed=True, check_cost="re-check states[i]==states[j]",
                           detail=f"pigeonhole: index {i} and {j} share state {s!r} ⇒ a cycle of length {j - i} is forced")
            return KV.exact({"i": i, "j": j, "cycle_length": j - i, "state": s}, "guaranteed_structure",
                            "pigeonhole cycle extractor", cert)
        seen[key] = j
    return KV.decline(f"M10.pigeonhole: all {len(states)} states distinct (run not longer than the state set) — no "
                      "forced repeat ⇒ DECLINE", "guaranteed_structure")


def ramsey_mono_triangle_grade(coloring, n: int) -> KV.Verdict:
    """A 2-colouring of K_n edges (n ≥ 6 ⇒ R(3,3)=6) forces a monochromatic triangle. `coloring(u,v)` → 0/1."""
    if n < 6:
        return KV.decline(f"M10.ramsey: n={n} < R(3,3)=6 — a monochromatic triangle is NOT forced ⇒ DECLINE",
                          "guaranteed_structure")
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                cab, cbc, cac = coloring(a, b), coloring(b, c), coloring(a, c)
                if cab == cbc == cac:
                    cert = KV.Cert(KV.EXACT, "ramsey_mono_clique", passed=True, check_cost="re-check 3 edge colours equal",
                                   detail=f"Ramsey R(3,3): vertices ({a},{b},{c}) form a colour-{cab} monochromatic triangle")
                    return KV.exact({"triangle": [a, b, c], "color": cab}, "guaranteed_structure", "Ramsey extractor", cert)
    return KV.decline("M10.ramsey: no monochromatic triangle found — contradicts R(3,3) (input not a valid 2-colouring) "
                      "⇒ DECLINE (bug guard)", "guaranteed_structure")


def m10_grade(x) -> KV.Verdict:
    """Route a structured M10 input: {"sequence":[...]} → Erdős–Szekeres; {"states":[...]} → pigeonhole cycle;
    {"ramsey": coloring_fn, "n": n} → Ramsey monochromatic triangle."""
    if isinstance(x, dict) and "sequence" in x:
        return erdos_szekeres_grade(x["sequence"])
    if isinstance(x, dict) and "states" in x:
        return pigeonhole_cycle_grade(x["states"])
    if isinstance(x, dict) and "ramsey" in x and "n" in x:
        return ramsey_mono_triangle_grade(x["ramsey"], x["n"])
    return KV.decline("M10: expected {sequence} / {states} / {ramsey,n}", "guaranteed_structure")
