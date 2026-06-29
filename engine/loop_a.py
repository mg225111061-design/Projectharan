"""
§3 ENGINE — LOOP A: corpus-driven fold-rate hunt (HONEST, measure-and-log-either-way).
================================================================================================================
The directive: re-measure the corpus, dig into the biggest DECLINE cluster (UNCLASSIFIED), attempt the new
§AY/§AU recognizers on it, and measure the fold-rate delta — logging the result whether it is large or (the honest
expectation) ~0.

★ THE INV-5 (no-double-count) DISCIPLINE — why most of the new islands provably add 0 to THIS corpus:
  • `qfold.krylov.fold_moment_sequence` uses Berlekamp–Massey + held-out replay — the SAME core the existing
    black-box conjecturer path already runs. Re-running it on an oracle the conjecturers already saw recovers
    NOTHING and would be a double-count. So we do NOT count those.
  • Pfaffian / free-fermion / stabilizer operate on raw skew matrices / Clifford circuits / quadratic-fermion
    Hamiltonians — structures NOT present as corpus Python. Their corpus recall is 0 by construction (logged, honest).
  • The ONE legitimate, non-double-counting probe is a PROBE-LENGTH gap: the black-box path uses _PROBE=32 samples
    (BM determines order L only when 2L+2 ≤ 32 ⇒ L ≤ 15). A monotonic C-finite oracle of order 16..31 is therefore
    DECLINED at 32 samples but RECOVERABLE by a 128-sample Krylov fold — MORE DATA, not a new algorithm on the same
    data. That is genuine recall headroom; whether the corpus CONTAINS any is the empirical question this measures.

★ Every recovery is INDEPENDENTLY re-verified against the TRUE oracle on a FAR window (n≈400–420), well beyond the
fold's training window — a divergence there is a false-EXACT (INV-1; must be 0). We never count a recovery we cannot
re-verify against ground truth.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List

import cfinite
import kernel_verdict as KV
from measure import decline_taxonomy as DT
from measure import engine_adapter as EA

_LONG_PROBE = 128                      # vs the engine's _PROBE=32 — the probe-length headroom test
_FAR = list(range(400, 421))           # independent far-window re-verification (ground truth = the true oracle)


def _reverify_far(fn, coeffs: List[str], order: int, train: List[Fraction]) -> Dict:
    """INDEPENDENT ground-truth check: the recovered order-L recurrence must reproduce the TRUE oracle on the FAR
    window n∈[400,420]. Returns {ok, false_exact, detail}. A mismatch ⇒ false-EXACT (must never happen)."""
    try:
        c = [Fraction(x) for x in coeffs]
        init = train[:order]
        for k in _FAR:
            true_k = Fraction(fn(k))
            pred_k = cfinite.companion_nth(c, init, k)
            if pred_k != true_k:
                return {"ok": False, "false_exact": True,
                        "detail": f"★ FALSE-EXACT: fold predicts {pred_k} but oracle is {true_k} at n={k}"}
        return {"ok": True, "false_exact": False,
                "detail": f"order-{order} recurrence reproduces the TRUE oracle on n∈[400,420]"}
    except Exception as e:  # noqa: BLE001
        # could not evaluate the oracle that far (overflow / cost) — NOT a confirmed recovery, and NOT a false-EXACT
        return {"ok": False, "false_exact": False, "detail": f"far re-verify inconclusive ({e}); not counted"}


def dig(n: int = None, seed: int = 20260628) -> Dict:
    """Re-measure the corpus, isolate the UNCLASSIFIED DECLINE cluster, and empirically test the probe-length Krylov
    headroom on its unary oracles with full far-window ground-truth re-verification. Honest: counts only confirmed,
    non-double-counted recoveries; surfaces any false-EXACT (must be 0)."""
    from corpus import build_corpus as BC
    from qfold import krylov as KRY
    if n is None:
        n = BC.TOTAL
    # mirror run_corpus's measurement hygiene: a harness-level z3 timeout so a hard query can't hang the dig
    # (the engine code is untouched; the param is RESTORED in the finally so it never leaks to other code).
    try:
        import z3
        z3.set_param("timeout", 5000)
    except Exception:  # noqa: BLE001
        pass
    items = BC.build_corpus(n, seed)
    by_cid = {it.cid: it for it in items}

    overall = {EA.EXACT_FOLD: 0, EA.PROBABILISTIC_FOLD: 0, EA.DECLINE: 0, EA.ERROR: 0}
    unclassified = []                                  # AdapterResults that taxonomy calls UNCLASSIFIED
    try:
        for it in items:
            r = EA.classify(it)
            overall[r.classification] += 1
            if r.classification == EA.DECLINE:
                cls, _, _ = DT.classify_decline(r.reason_signals)
                if cls == "UNCLASSIFIED":
                    unclassified.append(r)
    finally:
        try:
            import z3
            z3.set_param("timeout", 0)                  # RESTORE z3's default — never leak the timeout
        except Exception:  # noqa: BLE001
            pass

    # ── characterize UNCLASSIFIED: unary-oracle vs not, and by AST shape (what are these declines, really?) ──
    unary_unc, nonunary_unc = [], []
    shape = {"has_loop": 0, "has_data_branch": 0, "has_io": 0, "has_float": 0, "none": 0}
    for r in unclassified:
        (unary_unc if r.reason_signals.get("unary_oracle") else nonunary_unc).append(r)
        sig = r.reason_signals
        tagged = False
        for k in ("has_loop", "has_data_branch", "has_io", "has_float"):
            if sig.get(k):
                shape[k] += 1
                tagged = True
        if not tagged:
            shape["none"] += 1

    # ── the probe-length headroom test on UNCLASSIFIED unary oracles (the only non-double-counting Krylov probe) ──
    confirmed_recoveries, false_exacts, attempted, inconclusive = [], [], 0, 0
    for r in unary_unc:
        it = by_cid[r.cid]
        fn = EA._extract_oracle(it.src, it.entry)
        if fn is None:
            continue
        try:
            seq = [Fraction(fn(k)) for k in range(_LONG_PROBE)]
        except Exception:  # noqa: BLE001
            continue                                   # not a clean numeric oracle over the long probe
        attempted += 1
        v = KRY.fold_moment_sequence(seq)              # BM + held-out replay on 128 samples (vs the engine's 32)
        if v.status == KV.EXACT:
            chk = _reverify_far(fn, v.result["coeffs"], v.result["order"], seq)
            if chk["false_exact"]:
                false_exacts.append({"cid": r.cid, "detail": chk["detail"]})
            elif chk["ok"]:
                confirmed_recoveries.append({"cid": r.cid, "order": v.result["order"], "detail": chk["detail"]})
            else:
                inconclusive += 1

    folded = overall[EA.EXACT_FOLD]
    denom = overall[EA.EXACT_FOLD] + overall[EA.PROBABILISTIC_FOLD] + overall[EA.DECLINE]
    return {
        "corpus": {"n": n, "seed": seed, "overall": dict(overall),
                   "fold_rate": round(folded / denom, 4) if denom else 0.0},
        "unclassified_total": len(unclassified),
        "unclassified_unary_oracles": len(unary_unc),
        "unclassified_nonunary": len(nonunary_unc),
        "unclassified_shape": shape,
        "krylov_probe_length_headroom": {
            "long_probe": _LONG_PROBE, "engine_probe": EA._PROBE,
            "oracles_attempted": attempted,
            "confirmed_recoveries": confirmed_recoveries,        # genuine, far-reverified, non-double-counted
            "n_confirmed": len(confirmed_recoveries),
            "inconclusive_far": inconclusive,
            "false_exacts": false_exacts,                        # ★ MUST be empty (INV-1)
            "n_false_exact": len(false_exacts),
        },
        "honest_conclusion": (
            "non-unary UNCLASSIFIED ({nu}) are general control-flow/data code with no arithmetic fold target — the new "
            "§AY/§AU islands (Pfaffian/free-fermion/stabilizer) take raw matrices/circuits not present here ⇒ 0 corpus "
            "recall by construction. The only non-double-counting Krylov probe (32→128 samples) confirmed {nc} recovery(ies) "
            "with {nf} false-EXACT.".format(nu=len(nonunary_unc), nc=len(confirmed_recoveries), nf=len(false_exacts))
        ),
    }


def adversarial_battery() -> Dict:
    """★ A SYNTHETIC PROOF that the probe-length headroom is real AND sound (does not depend on the corpus containing
    such an oracle): an order-18 C-finite oracle (sum of geometric terms) is DECLINED by a 32-sample fold but RECOVERED
    by a 128-sample fold, and the recovery re-verifies against the TRUE oracle on the far window; ★ a hash stream is
    DECLINED at 128 samples too (no false-EXACT from more data)."""
    from qfold import krylov as KRY
    # an order-r C-finite oracle: f(k) = Σ_i a_i · b_i^k with r distinct small integer ratios ⇒ minimal recurrence
    # order exactly r. With r=18, 2r+2=38 > 32 (the engine probe can't determine it) but ≤ 128 (the long probe can).
    ratios = list(range(2, 20))            # 18 distinct ratios b_i = 2..19
    def f(k):
        return sum((i + 1) * (b ** k) for i, b in enumerate(ratios))
    short = [Fraction(f(k)) for k in range(32)]
    long = [Fraction(f(k)) for k in range(128)]
    v_short = KRY.fold_moment_sequence(short)
    v_long = KRY.fold_moment_sequence(long)
    far_ok = False
    if v_long.status == KV.EXACT:
        chk = _reverify_far(f, v_long.result["coeffs"], v_long.result["order"], long)
        far_ok = chk["ok"] and not chk["false_exact"]
    import hashlib
    rnd = [int.from_bytes(hashlib.sha256(str(k).encode()).digest()[:4], "big") for k in range(128)]
    rnd_declines = KRY.fold_moment_sequence(rnd).status == KV.DECLINE
    cases = {
        "order18_declined_at_32": v_short.status == KV.DECLINE,        # the engine probe genuinely can't see it
        "order18_recovered_at_128": v_long.status == KV.EXACT,        # more data recovers it
        "recovery_far_reverifies": far_ok,                            # ★ and it matches the TRUE oracle far out
        "hash_declines_at_128": rnd_declines,                          # ★ more data never manufactures a false-EXACT
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(dig(), indent=2, default=str))
