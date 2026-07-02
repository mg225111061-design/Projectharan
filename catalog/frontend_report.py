"""
FRONT-END §E report — MEASURED detection precision/recall, lift rate, and A/B DECLINE re-classification.
=======================================================================================================
All computed LIVE. The headline is PRECISION = 1.0 (zero false positives) — the proof that the central
proposer→exact-certifier invariant holds: detection/lifting may be liberal, but nothing folds without passing the
exact gate, so no random / impossible-core input is ever folded.
"""
from __future__ import annotations

from typing import Dict, List

import kernel_verdict as KV


def _structured_corpus():
    """Inputs with genuine hidden structure a conservative probe might miss (label, input)."""
    import numpy as np
    return [
        ("fibonacci", {"detect": [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]}),
        ("tribonacci", {"detect": [0, 0, 1, 1, 2, 4, 7, 13, 24, 44, 81, 149]}),
        ("squares", {"detect": [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]}),
        ("periodic_signal", {"detect": (np.cos(2 * np.pi * 5 * np.arange(64) / 64) + np.cos(2 * np.pi * 13 * np.arange(64) / 64)).tolist()}),
        ("repetitive_bytes", {"detect": b"the quick brown fox " * 12}),
        ("low_rank_matrix", {"detect": [[1, 2, 3], [2, 4, 6], [3, 6, 9], [1, 0, 1]]}),
        ("constants_relation", {"detect": [2.5, 0.5, 1.0]}),
        ("lift_sum_sq", {"lift_code": "s = 0\nfor k in range(1, n+1):\n  s += k*k\nreturn s"}),
        ("lift_sum_lin", {"lift_sum": "3*k+1", "var": "k", "base": 1}),
    ]


def _impossible_corpus():
    """The impossible core + true randomness — NONE may ever fold (precision gate)."""
    import os
    import random
    random.seed(20)
    return [
        ("secure_csprng_600", os.urandom(600)),
        ("secure_csprng_1500", os.urandom(1500)),
        ("random_ints", {"detect": [random.randint(0, 99999) for _ in range(80)]}),
        ("random_floats", {"detect": [random.gauss(0, 1) for _ in range(80)]}),
        ("random_bits", {"detect": [random.randint(0, 1) for _ in range(160)]}),
        ("incompressible_prose", "qz7Kx9mW2vL8pR3nT6"),
        ("full_rank_matrix", {"detect": [[2, 1, 0], [1, 3, 1], [0, 1, 2]]}),
        ("halting", "does this arbitrary program halt on every input?"),
        ("non_liftable_code", {"lift_code": "return network_call(parse(stdin))"}),
        ("unsound_opt", {"validate": [lambda e: e["x"] * 2, lambda e: e["x"] + 1, ["x"]]}),
    ]


def report() -> dict:
    """The §E front-end report — recall, PRECISION (must be 1.0), lift rate, A/B re-classification, all measured."""
    import catalog.compose as C
    structured = _structured_corpus()
    impossible = _impossible_corpus()
    recovered = [lbl for lbl, x in structured if C.route(x).grade != KV.DECLINE]
    false_positives = [lbl for lbl, x in impossible if C.route(x).grade != KV.DECLINE]
    recall = round(len(recovered) / len(structured), 3)
    precision = 1.0 if not false_positives else round(len(recovered) / (len(recovered) + len(false_positives)), 3)
    # lift rate among the lift-tagged corpus
    lifts = [(lbl, x) for lbl, x in structured if isinstance(x, dict) and ("lift_sum" in x or "lift_code" in x)]
    lifted = [lbl for lbl, x in lifts if C.route(x).grade == KV.EXACT]
    # A/B DECLINE re-classification: of the IMPOSSIBLE set, how many stayed DECLINE (B-core, correct) — all should
    b_core_held = [lbl for lbl, x in impossible if C.route(x).grade == KV.DECLINE]
    return {
        "structured_total": len(structured), "recovered": recovered, "recall": recall,
        "false_positives": false_positives, "precision": precision, "precision_is_one": not false_positives,
        "lift_total": len(lifts), "lifted": lifted, "lift_rate": round(len(lifted) / max(1, len(lifts)), 3),
        "impossible_total": len(impossible), "b_core_held": len(b_core_held),
        "central_invariant_holds": not false_positives,
    }
