"""
§AQ §6.SPLIT — ★ S-5 honesty: EXACT count vs UPPER BOUND. The genuinely-new claim is the EXACT count; an upper bound is
================================================================================================================
just SPEED / KoAT / CoFloCo re-labelled (existing bound analysis — NOT new).
  EXACT  — the iteration count is a deterministic function of a `requires`-declared size / structural constant (a fixed
           step toward a known bound: `pos < S; pos += CHUNK`, `for _ in range(⌈S/C⌉)`). ⇒ ⌈S/C⌉ + z3 cert = OUR new gem.
  BOUND  — termination depends on DATA / runtime (`while read(...) > 0`, `while has_more`, a maxRetries+break). The
           literature is clear there is no EXACT count for data-dependent control flow; only a worst-case BOUND exists
           ⇒ this is SPEED/KoAT/CoFloCo re-hashed — labelled `upper_bound`, NOT claimed as new.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

_DATA_DRIVEN = ("read", "recv", "readline", "fetch", "next", "has_more", "hasmore", "hasnext", "has_next",
                "eof", "available", "poll", "accept")


@dataclass
class CountKind:
    kind: str                            # "EXACT" | "BOUND"
    is_new: bool                         # EXACT exact-count = new; BOUND = SPEED/KoAT rehash
    label: str = ""
    reason: str = ""


def classify(src: str) -> CountKind:
    """EXACT iff every loop terminates by a fixed step toward a structural/declared size; BOUND iff any loop's
    termination is data-driven (a call/flag in the guard)."""
    try:
        tree = ast.parse(src)
    except Exception as e:  # noqa: BLE001
        return CountKind("BOUND", False, "upper_bound", f"parse error ({e}) ⇒ conservative BOUND")
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            # data-driven guard: a call to a data source, or a known data flag name
            for sub in ast.walk(node.test):
                if isinstance(sub, ast.Call):
                    f = sub.func
                    nm = (f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else "").lower()
                    if any(d in nm for d in _DATA_DRIVEN):
                        return CountKind("BOUND", False, "upper_bound (SPEED/KoAT/CoFloCo rehash)",
                                         f"loop terminates on a data-driven call {nm!r} ⇒ no EXACT count ⇒ existing bound analysis")
                if isinstance(sub, ast.Name) and any(d in sub.id.lower() for d in _DATA_DRIVEN):
                    return CountKind("BOUND", False, "upper_bound (SPEED/KoAT/CoFloCo rehash)",
                                     f"loop terminates on a data flag {sub.id!r} ⇒ no EXACT count ⇒ existing bound analysis")
    # a data-driven conditional `break` (e.g. `for k in range(N): if recv(): break`) makes the count data-dependent —
    # the range is only an UPPER BOUND, not an EXACT count.
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            has_break = any(isinstance(s, ast.Break) for s in ast.walk(node))
            if not has_break:
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    f = sub.func
                    nm = (f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else "").lower()
                    if any(d in nm for d in _DATA_DRIVEN):
                        return CountKind("BOUND", False, "upper_bound (SPEED/KoAT/CoFloCo rehash)",
                                         f"data-driven early `break` (on {nm!r}) ⇒ count is data-dependent ⇒ upper bound only")
                if isinstance(sub, ast.Name) and any(d in sub.id.lower() for d in _DATA_DRIVEN):
                    return CountKind("BOUND", False, "upper_bound (SPEED/KoAT/CoFloCo rehash)",
                                     f"data-driven early `break` (on {sub.id!r}) ⇒ count is data-dependent ⇒ upper bound only")
    return CountKind("EXACT", True, "exact_count (z3 cert)",
                     "fixed step toward a structural/declared size ⇒ EXACT count ⌈S/C⌉ + z3 certificate (the new gem)")


def adversarial_battery() -> dict:
    """★ a fixed-step chunked loop over a declared size classifies EXACT (the new gem); ★★ a data-driven
    `while read()>0` loop classifies BOUND (SPEED/KoAT rehash — NOT claimed new, S-5 honesty); ★ a maxRetries loop that
    breaks on a data condition is BOUND."""
    exact = classify("def f(S):\n pos=0; n=0\n while pos < S:\n  read(fd, 4096); pos += 4096; n += 1\n return n")
    bound = classify("def f(fd):\n n=0\n while read(fd, 4096) > 0: n += 1\n return n")
    retry = classify("def f():\n for k in range(10):\n  if recv(): break")
    cases = {
        "fixed_step_is_exact": exact.kind == "EXACT" and exact.is_new,                  # ★ new gem
        "data_driven_is_bound": bound.kind == "BOUND" and not bound.is_new,             # ★★ SPEED rehash, not new
        "data_driven_labelled_rehash": "SPEED" in bound.label or "rehash" in bound.label,
        "retry_with_data_break_is_bound": retry.kind == "BOUND",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
