"""
§AP §5.9 — DEFUNCTIONALIZE (the 9th disguise dimension): a sequence produced by HIGHER-ORDER dispatch — an operation
================================================================================================================
selected from a table/strategy per step (`ops[select(k)](state)`) — is opaque to the black-box oracle extractor, which
sees a function-valued indirection rather than a recurrence. Defunctionalization RESOLVES the dispatch to first order:
state_{k+1} = apply(tag_k, state_k). Once first-order, a PERIODIC dispatch is a per-residue recurrence (REUSE §AL
control_flatten) and any resolved dispatch is a plain unary oracle the §AI conjecturers dispose. ★ S-1: normalization
only — the existing z3 gate disposes; a chaotic dispatch is REJECTED (no false EXACT).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict


@dataclass
class DefuncResult:
    folded: bool
    lens: str = ""
    detail: str = ""


def resolve(ops: Dict[object, Callable], select: Callable[[int], object], init):
    """Build the first-order unary oracle from the higher-order dispatch: apply ops[select(k)] for k=0..n to init."""
    def oracle(n: int):
        s = init
        for k in range(n + 1):
            s = ops[select(k)](s)
        return s
    return oracle


def fold(ops: Dict[object, Callable], select: Callable[[int], object], init) -> DefuncResult:
    """Resolve the higher-order dispatch to first order, then dispose via the existing gate (control_flatten for a
    periodic dispatch, else the §AI conjecturers)."""
    oracle = resolve(ops, select, init)
    from recall.strip import control_flatten as CF
    r = CF.fold(oracle)                                           # periodic dispatch ⇒ per-residue recurrence
    if r.folded:
        return DefuncResult(True, "control_flatten", r.detail)
    from recall import core
    rr = core.fold_via_ai(oracle, "defunctionalize")
    return DefuncResult(rr.folded, rr.structure_class, rr.detail)


def adversarial_battery() -> dict:
    """★ a PERIODIC 2-op dispatch (alternating s→s+1 and s→2s) resolves to a per-residue recurrence and folds (REUSE
    control_flatten); ★ a single-op dispatch (s→s+3) folds (linear); ★★ a CHAOTIC dispatch (logistic step) is REJECTED
    (the gate holds — no false EXACT)."""
    periodic = fold({0: lambda s: s + 1, 1: lambda s: 2 * s}, lambda k: k % 2, 1)
    single = fold({0: lambda s: s + 3}, lambda k: 0, 0)

    def chaos_step(s):
        x = (s % 1000 + 1) / 1000.0
        return int(3.99 * x * (1 - x) * 1000)
    chaotic = fold({0: chaos_step}, lambda k: 0, 1)

    cases = {
        "periodic_dispatch_folds": periodic.folded,
        "single_op_dispatch_folds": single.folded,
        "chaotic_dispatch_declines": not chaotic.folded,         # ★★ no false EXACT
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
