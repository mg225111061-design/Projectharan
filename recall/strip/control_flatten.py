"""
§AL §1.6 — CONTROL FLATTEN: a recurrence hidden inside conditionals/switch where each branch updates differently.
================================================================================================================
The FULL sequence may not be C-finite, but SPLIT BY THE GUARD (residue class n mod p) each branch is. The strip
separates the unary oracle into per-residue sub-oracles `g_r(m) = f(p·m + r)` and folds each; a fold = every residue
class of some small modulus folds (a per-guard recurrence separation). ★ each sub-oracle is z3-gated independently.
"""
from __future__ import annotations

from typing import Callable, Optional

from recall import core


def fold(fn: Callable[[int], object], moduli=(2, 3, 4)) -> core.StripResult:
    """Find the smallest modulus p such that EVERY residue class g_r(m)=f(p·m+r) folds; else DECLINE."""
    for p in moduli:
        classes = [(lambda r: (lambda m: fn(p * m + r)))(r) for r in range(p)]
        results = [core.fold_via_ai(g, f"control(mod {p}, class {r})") for r, g in enumerate(classes)]
        if all(rr.folded for rr in results):
            kinds = sorted({rr.structure_class for rr in results})
            return core.StripResult(True, f"control_flatten(mod {p})", "+".join(kinds), None,
                                    f"all {p} residue classes fold (z3-gated each): {kinds}")
    return core.StripResult(False, "control_flatten", "", None, "no modulus splits the guards into foldable classes")


def adversarial_battery() -> dict:
    """★ a parity-branched function (even: 2n, odd: 3n+1) splits mod-2 into two linear classes that BOTH fold (z3-gated);
    ★ a branch that hides genuine randomness in one class DECLINEs (z3 gate holds — no false EXACT)."""
    def parity(n):
        return 2 * n if n % 2 == 0 else 3 * n + 1
    r = fold(parity)

    def rnd_branch(n):
        import hashlib
        return 5 * n if n % 2 == 0 else int.from_bytes(hashlib.sha256(str(n).encode()).digest()[:6], "big")
    d = fold(rnd_branch)
    cases = {
        "parity_branches_split_and_fold": r.folded and r.disguise.startswith("control_flatten"),
        "random_branch_declines": not d.folded,                  # ★ z3 gate holds
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
