"""
§AY QLA-8 — tensor-train / MPS bond-dimension fold.
================================================================================================================
A d-way tensor with LOW bond rank factors as a train T = G_1·G_2·…·G_d (TT-SVD), storing/evaluating in O(d·n·χ²)
instead of nᵈ. REUSE gpu.hidden_structure.exact_rank_factorization (RREF over ℚ) on the sequential unfoldings —
each factorization is EXACT (residual 0), so the TT reconstructs the tensor exactly.

★ EXACT only when the bond ranks are genuinely small (TT storage < full storage); a generic tensor has FULL bond
rank ⇒ no compression ⇒ DECLINE. Float entries ⇒ DECLINE (no float-EXACT, §1-Q3).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Sequence, Tuple

import kernel_verdict as KV

from . import _la


def _tt_decompose(dims: Sequence[int], flat: List[Fraction]) -> Optional[Tuple[List[int], List, bool]]:
    """TT-SVD via exact ℚ RREF. Returns (bond_ranks, cores, residual_zero) or None. Each unfolding M = C·R exactly."""
    from gpu import hidden_structure as HS
    d = len(dims)
    cur = list(flat)
    r_prev = 1
    ranks: List[int] = []
    cores = []
    for k in range(d - 1):
        rows = r_prev * dims[k]
        if rows == 0 or len(cur) % rows != 0:
            return None
        cols = len(cur) // rows
        Mmat = [[cur[i * cols + j] for j in range(cols)] for i in range(rows)]
        fr = HS.exact_rank_factorization(Mmat)
        if fr is None:
            return None
        C, R, r = fr
        if _la.matmul(C, R) != Mmat:                          # exact reconstruction (residual 0) — defensive
            return None
        ranks.append(r)
        cores.append(C)
        cur = [R[i][j] for i in range(r) for j in range(cols)]
        r_prev = r
    cores.append(cur)
    return ranks, cores, True


def tensor_train_fold(dims: Sequence[int], flat: Sequence) -> KV.Verdict:
    """Fold a tensor (row-major flat list, shape `dims`) into a TT. EXACT iff TT storage < full storage (genuine low
    bond rank, exact reconstruction); generic full-rank tensor or float entries ⇒ DECLINE."""
    try:
        f = _la.fvec(flat)
    except _la.NonExact as e:
        return KV.decline(f"tensor_train: {e} ⇒ DECLINE (no float-EXACT)", "tensor_train")
    d = len(dims)
    if d < 2:
        return KV.decline("tensor_train: need a ≥2-way tensor", "tensor_train")
    full = 1
    for x in dims:
        full *= x
    if len(f) != full:
        return KV.decline("tensor_train: flat length != prod(dims)", "tensor_train")
    dec = _tt_decompose(dims, f)
    if dec is None:
        return KV.decline("tensor_train: exact unfolding factorization failed ⇒ DECLINE", "tensor_train")
    ranks, _cores, resid_ok = dec
    rfull = [1] + ranks + [1]
    tt_storage = sum(rfull[k] * dims[k] * rfull[k + 1] for k in range(d))
    if not (resid_ok and tt_storage < full):
        return KV.decline(f"tensor_train: bond ranks {ranks} give TT storage {tt_storage} ≥ full {full} (no "
                          f"compression — generic full bond rank) ⇒ DECLINE", "tensor_train")
    cert = KV.Cert(KV.EXACT, "tensor_train_bond_rank", passed=True, check_cost="exact ℚ RREF unfoldings (residual 0)",
                   detail=f"TT bond ranks {ranks}; storage {tt_storage} < full {full}; each unfolding M=C·R exact "
                          f"(residual 0) ⇒ exact reconstruction")
    return KV.exact({"bond_ranks": ranks, "tt_storage": tt_storage, "full_storage": full}, "tensor_train",
                    f"O(d·n·χ²) store/eval (χ=max bond {max(ranks)}) vs nᵈ", cert,
                    reason=f"Axis-A: low-bond-rank tensor recognized; Axis-B nᵈ→O(d·n·χ²)")


def adversarial_battery() -> dict:
    """★ EXACT: a rank-1 tensor T[i,j,k]=u_i·v_j·w_k has bond ranks (1,1) ⇒ huge compression. ★★ DECLINE: a generic
    full-bond-rank tensor (no compression) and a float tensor ⇒ DECLINE (no false-EXACT on a dense tensor)."""
    u, v, w = [1, 2, 3], [1, 0, 2], [2, 1, 1]
    rank1 = [u[i] * v[j] * w[k] for i in range(3) for j in range(3) for k in range(3)]    # 3×3×3 rank-1
    r1 = tensor_train_fold((3, 3, 3), rank1)
    r1_ok = r1.status == KV.EXACT and max(r1.result["bond_ranks"]) == 1
    # generic tensor (coprime-ish entries) ⇒ full bond rank ⇒ no compression
    gen = [(i * 9 + j * 3 + k) * 7 + 1 for i in range(3) for j in range(3) for k in range(3)]
    gen[5] = 1000; gen[20] = -7                                                           # break any accidental rank
    rg = tensor_train_fold((3, 3, 3), gen)
    gen_declines = rg.status == KV.DECLINE
    flt = tensor_train_fold((2, 2), [1.0, 2.0, 3.0, 4.0])
    flt_declines = flt.status == KV.DECLINE
    cases = {"rank1_exact": r1_ok, "generic_declines": gen_declines, "float_declines": flt_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
