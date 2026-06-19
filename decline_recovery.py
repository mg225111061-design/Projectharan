"""
v39 PHASE B — DECLINE-pile recovery: separate fake-Ω(N) (hidden structure) from real-Ω(N) (genuine noise).
==========================================================================================================
v38's coverage work only refined ALREADY-folded cases (O(log n)→O(1)); it never RECOVERED declined ones. This
module wakes the sleeping v37 sublinear cluster (hidden_closed / prony / sparse_fft / compressed_sensing /
randomized_svd / planted_detect) and points it AT the DECLINE pile. Each recovery passes a SOUND, per-instance,
HELD-OUT certificate or it does not happen.

★ THE LINE WE NEVER CROSS ★ real-Ω(N) (genuine random/independent data) must NEVER be "recovered" — that would
  be a false structure / a wrong answer. The hard guarantee measured here is false_structure == 0 on the
  real-random cases. fake-Ω(N) (a polynomial / exponential-sum / k-sparse / low-rank hiding behind an opaque
  presentation that the current engine declines) IS recovered, with its grade (EXACT or PROBABILISTIC(ε,δ)).

★ GRADES ★ never mixed: polynomial / exact exp-sum / k-sparse → EXACT; low-rank / spiked → PROBABILISTIC(ε,δ);
  no certificate → DECLINE (byte-identical to before — lossless defer).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

import sublinear_layer as SL
import hidden_closed as HC
import prony
import sparse_fft
import compressed_sensing as CS
import randomized_svd as RS
import planted_detect as PD


@dataclass
class RecoveryCase:
    cid: str
    category: str                       # numeric-sequence | signal | matrix | statistical
    truth: str                          # ground truth: hidden_poly|hidden_expsum|hidden_sparse|hidden_lowrank|
                                        #                hidden_spiked | real_random
    shape: str                          # "sequence" | "signal" | "matrix"
    data: object
    split: str = "measure"              # "tune" | "measure" (held-out)


@dataclass
class RecoveryVerdict:
    cid: str
    grade: str                          # EXACT | PROBABILISTIC | DECLINE
    kind: str                           # which detector certified it (or "—")
    bound: Optional[float] = None
    detail: str = ""


def recover(case: RecoveryCase) -> RecoveryVerdict:
    """Try the SHAPE-appropriate sound-gated detectors; return the first that CERTIFIES, else DECLINE.
    Every non-DECLINE carries the underlying v37 per-instance certificate (held-out / residual / dual / gap)."""
    if case.shape == "sequence":
        samples = list(case.data)
        # 1) hidden polynomial (finite differences + held-out) → EXACT O(1)
        if all(float(x).is_integer() for x in samples):
            rec = HC.classify(lambda n: int(samples[n]), m=len(samples) - 1)
            if rec.status == HC.CLOSED_O1 and rec.grade == "EXACT":
                return RecoveryVerdict(case.cid, SL.EXACT, "hidden_closed:poly", float(rec.degree),
                                       f"degree-{rec.degree} polynomial, held-out×{rec.checked_holdout}")
        # 2) hidden exponential sum (Prony/ESPRIT, residual < machine-ε, cfinite cross-checked) → EXACT
        #    ★ soundness guard: an INTEGER sequence may earn EXACT only if its values are within float64's
        #    exact-integer range (<2^53); beyond that a small RELATIVE residual could mask float error → a
        #    false EXACT. Outside the exact range we DECLINE (float arithmetic cannot certify bit-exactness). ★
        exact_ok = (not all(float(x).is_integer() for x in samples)) or max(abs(x) for x in samples) < 2 ** 53
        v = prony.recover(np.asarray(samples, dtype=float))
        if v.status == SL.EXACT and exact_ok:
            return RecoveryVerdict(case.cid, SL.EXACT, "prony:exp_sum", v.certificate.bound,
                                   "exponential sum recovered, held-out residual < machine-ε (values < 2^53)")
        return RecoveryVerdict(case.cid, SL.DECLINE, "—", None, "no polynomial / exp-sum structure (held-out)")

    if case.shape == "signal":
        v = sparse_fft.recover(np.asarray(case.data, dtype=float))   # k-sparse spectrum (Prony on O(k) samples)
        if v.status == SL.EXACT:
            return RecoveryVerdict(case.cid, SL.EXACT, "sparse_fft", v.certificate.bound, "k-sparse spectrum")
        return RecoveryVerdict(case.cid, SL.DECLINE, "—", None, "spectrum not k-sparse")

    if case.shape == "matrix":
        M = np.asarray(case.data, dtype=float)
        # low-rank (rSVD posterior residual, δ stated) → PROBABILISTIC
        v = RS.approximate(M)
        if v.status == SL.PROBABILISTIC:
            return RecoveryVerdict(case.cid, SL.PROBABILISTIC, "randomized_svd", v.certificate.bound,
                                   f"low-rank, ε={v.certificate.epsilon:.1e} δ={v.certificate.delta:.0e}")
        # spiked/planted (BBP spectral gap) → PROBABILISTIC (detectability, never an absence proof)
        if M.shape[0] == M.shape[1]:
            v2 = PD.detect(M)
            if v2.status == SL.PROBABILISTIC:
                return RecoveryVerdict(case.cid, SL.PROBABILISTIC, "planted_detect", v2.certificate.bound,
                                       "spectral gap above BBP edge")
        return RecoveryVerdict(case.cid, SL.DECLINE, "—", None, "no low-rank / spectral structure")

    return RecoveryVerdict(case.cid, SL.DECLINE, "—", None, "unknown shape")


# ───────────────────────────────────── B0: a GROUND-TRUTH-labelled corpus (fake-Ω(N) + real-Ω(N))
def make_corpus(seed: int = 0) -> List[RecoveryCase]:
    """Each case has a KNOWN truth so recovery can be scored honestly and false-structure caught. The current
    engine DECLINES all of these (raw sequences/signals/matrices — outside the HARAN-fold front-end), so the
    baseline recovery is 0%. tune/measure = train/held-out split (we report on held-out)."""
    rng = np.random.default_rng(seed)
    C: List[RecoveryCase] = []

    # fake-Ω(N): hidden POLYNOMIAL (current engine sees an opaque sequence → DECLINE; hidden_closed recovers)
    for cid, poly in [("poly_cubic", lambda n: 3 * n**3 - 2 * n + 5), ("poly_sq", lambda n: n * n),
                      ("poly_sumk", lambda n: n * (n + 1) // 2), ("poly_quartic", lambda n: n**4 - n + 1)]:
        C.append(RecoveryCase(cid, "numeric-sequence", "hidden_poly", "sequence",
                              [poly(n) for n in range(40)], "tune" if cid.endswith("sq") else "measure"))

    # fake-Ω(N): hidden EXPONENTIAL SUM (Prony recovers; not polynomial). Ranges kept within float64's exact
    # range (<2^53) so the EXACT grade is GENUINELY exact (not a float-masked relative residual).
    for cid, f, m in [("exp_2_5", lambda n: 3 * 2**n + 2 * 5**n, 18), ("exp_fib", None, 0),
                      ("exp_mix", lambda n: 2**n + 3**n + 1, 24)]:
        if cid == "exp_fib":
            fib = [0, 1]
            for _ in range(28):
                fib.append(fib[-1] + fib[-2])
            data = fib
        else:
            data = [f(n) for n in range(m)]
        C.append(RecoveryCase(cid, "numeric-sequence", "hidden_expsum", "sequence", data,
                              "tune" if cid == "exp_fib" else "measure"))

    # fake-Ω(N): hidden k-SPARSE signal (a few tones in noise-free spectrum) → sparse_fft EXACT
    for cid, tones in [("sparse_3", [5, 40, 100]), ("sparse_2", [7, 64])]:
        N = 256
        sig = np.zeros(N)
        for t in tones:
            sig += np.cos(2 * np.pi * t * np.arange(N) / N)
        C.append(RecoveryCase(cid, "signal", "hidden_sparse", "signal", sig, "measure"))

    # fake-Ω(N): hidden LOW-RANK / SPIKED matrix → rSVD / planted PROBABILISTIC
    A = rng.standard_normal((120, 5)) @ rng.standard_normal((5, 120))
    C.append(RecoveryCase("lowrank_r5", "matrix", "hidden_lowrank", "matrix", A, "measure"))
    spiked, _ = PD.make_spiked(160, snr=3.0, seed=seed)
    C.append(RecoveryCase("spiked_snr3", "statistical", "hidden_spiked", "matrix", spiked, "measure"))

    # ★ real-Ω(N): GENUINE noise — every detector MUST DECLINE (recovery here = false structure = wrong) ★
    C.append(RecoveryCase("rand_seq", "numeric-sequence", "real_random", "sequence",
                          [int(x) for x in rng.integers(0, 1_000_000, 40)], "measure"))
    C.append(RecoveryCase("hash_seq", "numeric-sequence", "real_random", "sequence",
                          [(n * 2654435761) % 1_000_003 for n in range(40)], "tune"))
    C.append(RecoveryCase("rand_signal", "signal", "real_random", "signal", rng.standard_normal(256), "measure"))
    C.append(RecoveryCase("rand_matrix", "matrix", "real_random", "matrix", rng.standard_normal((120, 120)), "measure"))
    return C


# ───────────────────────────────────── B2: recovery measurement (held-out, by category) + the hard guarantee
def measure_recovery(split: Optional[str] = "measure", seed: int = 0) -> dict:
    """Recovery rate over the labelled corpus (held-out by default). Reports recovered_exact / recovered_prob /
    still_decline, the per-instance grades, and — the hard soundness number — false_structure (a real_random
    case wrongly graded non-DECLINE), which MUST be 0."""
    cases = [c for c in make_corpus(seed) if (split is None or c.split == split)]
    fake = [c for c in cases if c.truth != "real_random"]
    real = [c for c in cases if c.truth == "real_random"]
    rec_exact = rec_prob = missed = 0
    false_structure = 0
    rows = []
    for c in cases:
        v = recover(c)
        rows.append((c.cid, c.truth, v.grade, v.kind))
        if c.truth == "real_random":
            if v.grade != SL.DECLINE:
                false_structure += 1                       # ★ must stay 0 ★
        else:
            if v.grade == SL.EXACT:
                rec_exact += 1
            elif v.grade == SL.PROBABILISTIC:
                rec_prob += 1
            else:
                missed += 1
    nf = len(fake)
    return {"split": split or "all", "n_fake": nf, "n_real": len(real),
            "recovered_exact": rec_exact, "recovered_probabilistic": rec_prob, "still_decline_fake": missed,
            "recovery_rate": round((rec_exact + rec_prob) / nf, 3) if nf else 0.0,
            "false_structure": false_structure,                       # real-Ω(N) wrongly recovered — MUST be 0
            "real_correctly_declined": sum(1 for c in real if recover(c).grade == SL.DECLINE),
            "rows": rows}
