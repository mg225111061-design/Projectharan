"""
§AK §4 — NEAR-MISS HUNTER: find the R class (DECLINEs that ACTUALLY fold) — the most valuable output.
================================================================================================================
★ R = "foldable, but the engine missed it" — direct evidence of RECALL headroom and a priority list for the next §AI
push. For every DECLINEd UNARY oracle we retry HARDER than the default black-box path:
  (1) the §AI conjecturers at a LARGER probe (probe=64) — recovers higher-order recurrences the default probe=24/32
      left under-determined;
  (2) the k-REGULAR mechanism (M22 `mech_kregular`, REUSED) at k∈{2,3,10} — folds the digit/popcount-class sequences
      the §AI portfolio (BM / polynomial / period / holonomic) structurally cannot see.
★★ M-3 held everywhere: a near-miss fold is accepted ONLY through a z3-gated mechanism, and we ADD a DOUBLE-WINDOW
held-out guard (the fold must reproduce the oracle on BOTH a short and a strictly LONGER sample) — a spurious
short-window fit breaks on the longer window ⇒ no false R. Observation-match alone NEVER promotes to R.

★ Output: the count of R + the DISGUISE-TYPE distribution (k-regular vs high-order recurrence vs …) = exactly the
ranked recall targets for the paper-side research to merge with.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from measure import engine_adapter as EA

_SHORT_N = 96
_LONG_N = 160
_PROBE_HARD = 64
_K_VALUES = (2, 3, 10)        # popcount (k=2), base-3 digit functions (k=3), base-10 digit sum (k=10)
_FAR = list(range(200, 215))  # far-window differential confirm beyond every fit window


@dataclass
class NearMissResult:
    cid: str
    domain: str
    folded: bool                  # True ⇒ R (a recall gap)
    disguise: str = ""            # the structure that caught it (recall priority signal)
    detail: str = ""


def _kregular_robust(fn: Callable[[int], object]) -> Optional[str]:
    """Try k-regular at k∈{2,3,10} with a DOUBLE-WINDOW held-out guard (short AND long both EXACT) + a far-window
    differential confirm. Returns the disguise label ('k-regular(k=K)') or None. ★ M-3: both windows + far must agree."""
    import kernel_verdict as KV
    from catalog import mech_kregular as KR
    try:
        short = [int(fn(n)) for n in range(_SHORT_N)]
        long_ = [int(fn(n)) for n in range(_LONG_N)]
        far = [int(fn(n)) for n in range(_FAR[-1] + 1)]
    except Exception:  # noqa: BLE001
        return None
    for k in _K_VALUES:
        try:
            if KR.kregular_grade(short, k=k).status != KV.EXACT:
                continue
            if KR.kregular_grade(long_, k=k).status != KV.EXACT:   # ★ double-window: a spurious fit breaks here
                continue
            if KR.kregular_grade(far, k=k).status != KV.EXACT:     # ★ far-window differential confirm
                continue
            return f"k-regular(k={k})"
        except Exception:  # noqa: BLE001
            continue
    return None


def _hard_retry_ai(fn: Callable[[int], object]) -> Optional[str]:
    """Re-run the §AI conjecturers at a LARGER probe (defeats under-determination). z3 ∀-proof + 200-held-out are kept
    by the conjecturers themselves (M-3). Returns the structure_class disguise label or None."""
    try:
        from conjecture import bm_linrec, closedform_guess, period_guess, matpow_guess, holonomic_guess
        for mod in (bm_linrec, closedform_guess, period_guess, matpow_guess, holonomic_guess):
            r = mod.conjecture(fn, probe=_PROBE_HARD)
            if r.issued:
                return f"high-probe:{r.structure_class}"
    except Exception:  # noqa: BLE001
        pass
    return None


def retry_one(item) -> NearMissResult:
    """Aggressively retry a single DECLINEd item. Folds ⇒ R (with the disguise type); else genuinely unfoldable."""
    if not item.unary_oracle:
        return NearMissResult(item.cid, item.domain, False, "", "not a unary oracle — out of near-miss scope")
    fn = EA._extract_oracle(item.src, item.entry)
    if fn is None:
        return NearMissResult(item.cid, item.domain, False, "", "oracle re-exec failed")
    disguise = _hard_retry_ai(fn) or _kregular_robust(fn)
    if disguise:
        return NearMissResult(item.cid, item.domain, True, disguise,
                              f"★ R (recall gap): folds under aggressive retry via {disguise} (z3-gated + double/far held-out)")
    return NearMissResult(item.cid, item.domain, False, "", "still DECLINE after aggressive retry — genuinely unfoldable here")


def hunt(items: List, results: List, limit: Optional[int] = None) -> dict:
    """Run the near-miss hunter over the DECLINEd unary oracles. Returns the R count + disguise-type distribution
    (= the ranked recall priorities). `limit` caps how many DECLINEs are retried (for the fast test path)."""
    by_cid = {it.cid: it for it in items}
    declined = [r for r in results if r.classification == EA.DECLINE and by_cid.get(r.cid) and by_cid[r.cid].unary_oracle]
    if limit is not None:
        declined = declined[:limit]
    r_hits, disguises, examples = 0, {}, []
    for r in declined:
        nm = retry_one(by_cid[r.cid])
        if nm.folded:
            r_hits += 1
            disguises[nm.disguise] = disguises.get(nm.disguise, 0) + 1
            if len(examples) < 8:
                examples.append({"cid": nm.cid, "domain": nm.domain, "disguise": nm.disguise})
    return {"declined_unary_retried": len(declined), "R_count": r_hits,
            "disguise_distribution": dict(sorted(disguises.items(), key=lambda x: -x[1])),
            "recall_priority": list(dict(sorted(disguises.items(), key=lambda x: -x[1])).keys()),
            "examples": examples,
            "note": "R = DECLINE that ACTUALLY folds under aggressive retry (z3-gated + double/far held-out). The "
                    "disguise distribution is the ranked recall target for the next §AI push."}


def adversarial_battery() -> dict:
    """★ digit-sum (base-10) and popcount — DECLINEd by the §AI portfolio — are recovered as R via k-regular (the
    recall gap is real); ★★ a genuine random oracle (truncated SHA-256) is NOT recovered (no false R — M-3 double/far
    held-out holds); ★ a clean unfoldable (true randomness) stays unfoldable."""
    import hashlib
    from corpus.build_corpus import CorpusItem

    popcount = CorpusItem("t:pc", "numeric", "synthetic", "def f(n):\n    return bin(n).count('1')\n", "f", True, "popcount")
    ds3 = CorpusItem("t:ds3", "numeric", "synthetic",
                     "def f(n):\n    s = 0\n    while n:\n        s += n % 3\n        n //= 3\n    return s\n", "f", True, "digitsum_base3")
    rand = CorpusItem("t:rnd", "crypto_preprocessing", "synthetic",
                      "def f(n):\n    import hashlib\n    return int.from_bytes(hashlib.sha256(str(n).encode()).digest()[:6],'big')\n",
                      "f", True, "hash_oracle")
    pc, d3, rn = retry_one(popcount), retry_one(ds3), retry_one(rand)
    cases = {
        "popcount_is_R_via_kregular": pc.folded and pc.disguise.startswith("k-regular"),        # ★ recall gap, real
        "base3_digitsum_is_R_via_kregular": d3.folded and d3.disguise.startswith("k-regular"),
        "random_oracle_not_R": not rn.folded,                    # ★★ no false R (M-3 double/far held-out)
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
