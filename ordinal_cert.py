"""
ORDINAL-BOUNDED TERMINATION certificate (Constitution §4.8/§8, mechanism 14/ordinal) — the fold engine's
decreases-clause backbone. A loop/recursion whose LEXICOGRAPHIC measure (a tuple of naturals) maps to a strictly
DESCENDING sequence of ordinals (in Cantor normal form) terminates — ordinals are well-founded, so a strictly
descending sequence is finite. The certificate is the ordinal descent, machine-rechecked by `ordinal.check_descent`
(re-uses the existing [이미 있음] ordinal module). EXACT (descent holds) or honest DECLINE (measure does not
strictly decrease → cannot certify; never a false termination claim).
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import kernel_verdict as KV
import ordinal as O


def _ords(measures: Sequence[Tuple[int, ...]]) -> List["O.Ord"]:
    return [O.lex_measure_to_ordinal(tuple(int(v) for v in m)) for m in measures]


def descent_witness(measures: Sequence[Tuple[int, ...]]) -> KV.Verdict:
    """Certify termination from a SEQUENCE of lexicographic measures (one per step/iteration): EXACT if the
    corresponding ordinal sequence is strictly descending (well-founded ⇒ finite ⇒ terminates), else DECLINE."""
    if len(measures) < 2:
        return KV.decline("ordinal: need ≥2 measure points to witness descent", "ordinal_termination")
    try:
        ords = _ords(measures)
        ok = O.check_descent(ords)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"ordinal: measures not lex-orderable ({type(e).__name__})", "ordinal_termination")
    if ok:
        cert = KV.Cert(KV.EXACT, "ordinal_descent", passed=True, check_cost="O(k) ordinal compares (CNF)",
                       detail=f"lex measures {list(map(tuple, measures))} → strictly descending ordinal sequence "
                              f"(well-founded ⇒ terminates)")
        return KV.exact(True, "ordinal_termination", "ordinal-bounded termination (EXACT)", cert)
    return KV.decline(f"ordinal: measures {list(map(tuple, measures))} are NOT strictly ordinal-descending — "
                      "cannot certify termination (no false claim)", "ordinal_termination")


def step_cert(before: Tuple[int, ...], after: Tuple[int, ...]) -> KV.Verdict:
    """Certify a single recursive step's measure decrease: EXACT if after <_ord before (the fold/loop decreases-
    clause), else DECLINE. A whole recursion terminates if EVERY step satisfies this on the same well-founded measure."""
    return descent_witness([before, after])
