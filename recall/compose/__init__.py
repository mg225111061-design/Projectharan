"""
§AP §1 — COMPOSITIONAL FOLD: atomize → fold_each → recombine. The genuine win is CROSS-LENS composition: a stream
================================================================================================================
that is (C-finite atom) + (k-automatic atom) is neither C-finite nor k-automatic, so no single conjecturer folds the
whole — but each atom folds in its own lens and the verified recombination reassembles it. No new mechanism, no new
disposer: every atom routes through the existing z3 gate; the only added obligation (the combine operator) is
re-verified on a multi-scale carry-straddle held-out.
"""
from __future__ import annotations

from typing import Callable, List

from recall.compose import atomize as AT, fold_each as FE, recombine as RC


def fold_parts(parts: List[Callable[[int], object]], combine: str = "add") -> RC.ComposeResult:
    """Fold a composite given the decomposition the code exposes (atom oracles + combine op)."""
    atoms = AT.from_parts(parts, combine)
    if not atoms.ok:
        return RC.ComposeResult(False, len(parts), combine, [], atoms.detail)
    folds = FE.fold_all(atoms.atoms)
    return RC.recombine_verify(lambda n: AT.reconstruct(atoms, n), atoms, folds)


def adversarial_battery() -> dict:
    """★ CROSS-LENS: (linear C-finite) + (popcount k-automatic) — the SUM is neither (BM fails, M22 fails) but compose
    folds it (each atom in its lens, recombine verified); ★ (polynomial) × (geometric) folds via the `mul` combiner;
    ★★ a composite with a RANDOM atom DECLINEs (fold_each rejects it — no false EXACT); ★ a single atom is refused
    (not a composite)."""
    import hashlib

    def fib(n):                                                   # C-finite (order 2), EXPONENTIAL growth ⇒ NOT k-regular
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a
    popcount = lambda n: bin(n).count("1")                        # k-automatic (M22) — NOT C-finite (BM fails)
    cross = fold_parts([fib, popcount], "add")                    # Fib+popcount: neither C-finite NOR k-regular

    poly = lambda n: n * n + 1                                    # polynomial (conjecturers)
    geom = lambda n: 2 ** n                                       # geometric (conjecturers)
    prod = fold_parts([poly, geom], "mul")

    rnd = lambda n: int.from_bytes(hashlib.sha256(str(n).encode()).digest()[:6], "big")
    with_random = fold_parts([fib, rnd], "add")                  # one atom is random ⇒ DECLINE

    single = fold_parts([fib], "add")                            # not a composite

    # ★ confirm the whole cross-lens sum is genuinely NOT seen by a single lens (so compose is doing real work):
    #   Fib is C-finite but exponential ⇒ not k-regular; popcount is k-automatic ⇒ not C-finite; their sum is in
    #   NEITHER closed class, so both the conjecturers (BM) and M22 DECLINE the whole — only the split folds it.
    from recall import core, k_regular as KR
    whole = lambda n: fib(n) + popcount(n)
    whole_direct = core.fold_via_ai(whole, "whole").folded or KR.fold(whole).folded

    cases = {
        "cross_lens_sum_folds": cross.folded and "k_automatic(M22)" in (cross.lenses or []),
        "whole_not_seen_by_single_lens": not whole_direct,        # ★ compose folds what no single lens does
        "product_composite_folds": prod.folded,
        "random_atom_declines": not with_random.folded,           # ★★ no false EXACT
        "single_atom_refused": not single.folded,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
