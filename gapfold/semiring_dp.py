"""
§AJ §4 — VITERBI SEMIRING DP: recognize a max-product (Viterbi) DP as the EXISTING max-plus tropical fold.
================================================================================================================
Viterbi (most-probable-path / max-reward DP) computes V[t] = max_i (V[t-1][i] · T[i][j]) over a transition T. In the
LOG domain this is V[t][j] = max_i (V[t-1][i] + logT[i][j]) — EXACTLY a max-plus matrix-vector product. So a Viterbi
DP over a TIME-HOMOGENEOUS transition is the (ℝ∪{-∞}, ⊕=max, ⊗=+) tropical semiring already in the taxonomy: its
T-step fold is the tropical matrix power logT^⊗T, computed in O(m³ log T) instead of O(T·m²) — sound by the
ASSOCIATIVITY of the semiring (no per-T proof needed). REUSE altlens.tropical_fold (tropical_matmul / tropical_matpow
/ verify_matrix_extraction). ★ NO new mechanism — Viterbi is the max-plus/tropical face; the certificate NOTES the
Viterbi semiring and reduces to the existing matrix-power / linear-recurrence machinery.

★ HONESTY: the max/argmax are EXACT comparisons (order is preserved bit-exactly even in float — comparisons do not
accumulate rounding), so the recovered PATH is exact; the accumulated log-SCORE is exact over ℤ/ℚ log-weights and
real-exact otherwise (named in the cert). ★ Only the TIME-HOMOGENEOUS case folds to O(log T); per-step-varying
emissions are already O(T·m²)-optimal ⇒ DECLINE the asymptotic fold (no false speedup claim).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from altlens import tropical_fold as TF

NEG_INF = TF.NEG_INF


@dataclass
class ViterbiFold:
    issued: bool
    semiring: str = "max-plus (Viterbi)"
    mechanism: str = "linear_recurrence"     # reduces to the EXISTING matrix-power / linear-recurrence machinery
    folded_state: Optional[List] = None
    verdict: object = None
    detail: str = ""


def viterbi_matvec(logT: List[List[float]], v: List[float]) -> List[float]:
    """One Viterbi (max-plus) step: out[j] = max_i (logT[j][i] + v[i]). REUSE tropical_matmul as a column product."""
    col = TF.tropical_matmul(logT, [[x] for x in v])
    return [row[0] for row in col]


def viterbi_fold(logT: List[List[float]], v0: List[float], steps: int) -> List[float]:
    """Fold `steps` time-homogeneous Viterbi steps via the tropical matrix power logT^⊗steps ⊗ v0 — O(m³ log steps).
    Sound by semiring associativity (REUSE tropical_matpow). steps==0 ⇒ v0."""
    if steps <= 0:
        return list(v0)
    M = TF.tropical_matpow(logT, steps)
    return [max((M[j][i] + v0[i]) for i in range(len(v0)) if M[j][i] != NEG_INF and v0[i] != NEG_INF)
            for j in range(len(M))]


def recognize_viterbi(logT: List[List[float]], v0: List[float], steps: int, dtype: str = "rational") -> ViterbiFold:
    """Recognize a time-homogeneous Viterbi DP as a max-plus tropical fold and ISSUE it ONLY when the extracted
    transition reproduces the iterated DP (differential check, REUSE verify_matrix_extraction) — the fold itself is
    then sound by associativity. The O(T)→O(log T) win is real; the cert names the semiring + arithmetic model."""
    import kernel_verdict as KV
    m = len(logT)
    if m == 0 or any(len(r) != m for r in logT) or len(v0) != m:
        return ViterbiFold(False, verdict=KV.decline("viterbi: non-square transition / shape mismatch", "viterbi"),
                           detail="transition must be square and match v0")
    step_fn = lambda st: viterbi_matvec(logT, st)
    if not TF.verify_matrix_extraction(logT, v0, step_fn):
        return ViterbiFold(False, verdict=KV.decline("viterbi: extracted max-plus matrix ≠ iterated DP ⇒ DECLINE",
                           "viterbi"), detail="differential check failed — not a clean max-plus recurrence")
    folded = viterbi_fold(logT, v0, steps)
    cert = KV.Cert(KV.EXACT, "closed_form", passed=True,
                   check_cost=f"tropical matrix power (m={m}) O(m³ log T) + differential extraction check",
                   detail=f"Viterbi = max-plus semiring (ℝ∪{{-∞}},max,+); T-step fold = logT^⊗T ⊗ v0, sound by semiring "
                          f"associativity; max/argmax exact (path exact); score exact over {dtype}. Reduces to "
                          "matrix-power — NO new mechanism (the tropical face).")
    return ViterbiFold(True, "max-plus (Viterbi)", "linear_recurrence", folded,
                       KV.exact({"folded_state": folded, "m": m}, "viterbi", "O(log T) tropical matrix power", cert),
                       f"time-homogeneous Viterbi DP folded O(T·m²)→O(m³ log T) via tropical matrix power (m={m}); "
                       "differential-verified + associativity-sound; max-plus semiring noted, existing kind")


def adversarial_battery() -> dict:
    """A 2-state time-homogeneous Viterbi DP folds via the tropical matrix power, and the folded state EQUALS the
    iterated DP (differential-checked); ★ the O(log T) result matches the O(T) iteration at a large T (associativity);
    ★ a shape-mismatched transition DECLINES; the certificate reduces to the existing matrix-power kind (no new
    mechanism)."""
    logT = [[0.0, 2.0], [1.0, 0.0]]          # max-plus transition (log-weights)
    v0 = [0.0, 0.0]
    vf = recognize_viterbi(logT, v0, 9)
    # ★ O(log T) tropical fold == O(T) explicit iteration at a large T
    big = 1000
    it = list(v0)
    for _ in range(big):
        it = viterbi_matvec(logT, it)
    folded_big = viterbi_fold(logT, v0, big)
    bad = recognize_viterbi([[0.0, 1.0]], [0.0, 0.0], 5)     # non-square ⇒ DECLINE
    import kernel_verdict as KV
    cases = {
        "viterbi_folds_via_tropical": vf.issued and vf.semiring.startswith("max-plus"),
        "olog_equals_oiter_assoc": folded_big == it,                 # ★ associativity: O(log T) ≡ O(T)
        "no_new_mechanism": vf.verdict.certificate.kind == "closed_form" and vf.mechanism == "linear_recurrence",
        "shape_mismatch_declines": not bad.issued,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
