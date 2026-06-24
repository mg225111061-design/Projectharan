"""Mechanism 13 — KLEENE FIXPOINT (★ the abstract form of fold itself). Chain-of-recurrences, C-finite folds,
coupled-cluster e^T amplitudes, Bellman/HJB value iteration, separation-logic frame inference, abstract
interpretation. Output: the least/greatest fixpoint = the closed form / value function the loop computes.
This is what the existing fold engine already does; M13 is its catalog-level name."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "recurrence" in f.tags:
        s += 0.5
    if "fixpoint" in f.tags:
        s += 0.4
    if "sum" in f.tags or "loop" in f.tags:
        s += 0.3
    return min(1.0, s)


def _apply(x, **kw):
    # M13 routes to the EXISTING fold engine (PHASE E wires this); until then, honest defer.
    return honest_defer("M13.kleene_fixpoint", "routes to the existing fold engine (structure_recognizer/fold_dispatcher) — wired in PHASE E")


MECHANISM = Mechanism(
    num=13, name="kleene_fixpoint", probe=_probe, apply=_apply,
    cert_kinds=("fold_closed_form", "value_function", "frame_inference"),
    contract="requires a monotone iteration / recurrence / DP; ensures the fixpoint (closed form / value function), "
            "differential-equivalence-gated against the real loop; grade EXACT; Clock C only (not perceived speed)",
    composable_with=(1, 2, 6, 8),
    ur_form="fold = least-fixpoint of the loop functional; the catalog's most-instantiated mechanism",
)
