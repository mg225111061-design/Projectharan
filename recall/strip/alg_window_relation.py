"""
§AL §1.8 — ALGEBRAIC WINDOW RELATION: a sliding-window / stream aggregate over a STRUCTURED index stream has a
================================================================================================================
non-trivial closed form. A window sum `W(n) = Σ_{k=n}^{n+w-1} g(k)` over a polynomial/structured `g` is itself
structured (a window over a degree-d polynomial is degree-d in n). The strip builds the window oracle `W(n)` and lets
§AI recover the closed form; z3 disposes. ★ REUSE the §Z window-lens territory in spirit; over genuine DATA (not a
structured index) there is no closed form ⇒ DECLINE (honest).
"""
from __future__ import annotations

from typing import Callable

from recall import core


def window_oracle(g: Callable[[int], object], w: int) -> Callable[[int], object]:
    """W(n) = Σ_{k=n}^{n+w-1} g(k) — the sliding window of width w over the structured stream g."""
    return lambda n: sum(g(n + j) for j in range(w))


def fold(g: Callable[[int], object], w: int = 4) -> core.StripResult:
    return core.fold_via_ai(window_oracle(g, w), f"window(w={w})")


def adversarial_battery() -> dict:
    """★ a width-4 window over the linear stream g(k)=3k+1 folds (the window of a polynomial is a polynomial, z3-gated);
    ★ a window over a quadratic stream folds; ★ a window over a hash stream DECLINEs (no closed form — z3 gate holds)."""
    lin = fold(lambda k: 3 * k + 1, 4)
    quad = fold(lambda k: k * k, 5)

    def hashstream(k):
        import hashlib
        return int.from_bytes(hashlib.sha256(str(k).encode()).digest()[:6], "big")
    rnd = fold(hashstream, 4)
    cases = {
        "window_over_linear_folds": lin.folded,
        "window_over_quadratic_folds": quad.folded,
        "window_over_hash_declines": not rnd.folded,             # ★ z3 gate holds (no false EXACT)
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
