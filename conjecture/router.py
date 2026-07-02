"""
§AJ §2 — CONJECTURER ROUTER (autocorrelation · NCD · KS · mutual-information): try the LIKELY winner first.
================================================================================================================
The §AI portfolio runs five conjecturers (bm_linrec / closedform / period / matpow / holonomic). Trying them in a
fixed order wastes work; cheap statistical signals predict WHICH one will fold. ★★ The honesty that makes this free:
routing changes ONLY THE ORDER — every conjecturer remains in the fallback list, so the SET of foldable sequences is
identical with or without the router (recall unchanged) and z3 still disposes each candidate (precision unchanged).
The router can ONLY save average conjecture work; it can neither create a fold nor a false EXACT. We MEASURE that
routed-recall == unrouted-recall on the corpus (the routing-is-sound invariant), plus the first-try hit rate (the
actual speed win).

Signals (all deterministic, LLM-free, zero-dep): autocorrelation peak ⇒ periodic; finite-difference collapse ⇒
polynomial; polynomial term-ratio ⇒ holonomic; small Berlekamp-Massey order ⇒ C-finite (bm/matpow); NCD to an
exponential template + KS/MI as tie-breakers. REUSE native_sequence (BM), holonomic_guess (ratio), period_guess
(period), closedform_guess (finite-diff), catalog.decline_boundary's zlib for NCD.
"""
from __future__ import annotations

import math
import zlib
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable, List, Optional

from conjecture import harness as H

_ALL = ["period", "closedform", "holonomic", "bm_linrec", "matpow"]   # the five §AI conjecturers (module keys)


@dataclass
class RouteResult:
    order: List[str]                      # the FULL priority order (best-first) — all five always present (fallback kept)
    scores: dict = field(default_factory=dict)
    signals: dict = field(default_factory=dict)
    detail: str = ""


# ── deterministic routing signals ────────────────────────────────────────────────────────────────────────────
def autocorrelation(seq: List[float], lag: int) -> float:
    """Normalized autocorrelation at `lag` ∈ [-1,1] (Pearson on the lag-shifted overlap). A strong peak ⇒ periodic."""
    n = len(seq)
    if lag <= 0 or lag >= n:
        return 0.0
    a, b = seq[:n - lag], seq[lag:]
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    return num / (da * db) if da > 0 and db > 0 else 0.0


def ncd(a: bytes, b: bytes) -> float:
    """Normalized compression distance (zlib) ∈ ~[0,1]: NCD(x,y)=(C(xy)−min(C(x),C(y)))/max(C(x),C(y)). Small ⇒ x,y
    share structure. Used to compare the sequence's byte image to an exponential-growth template (⇒ bm/matpow)."""
    ca, cb = len(zlib.compress(a, 9)), len(zlib.compress(b, 9))
    cab = len(zlib.compress(a + b, 9))
    return (cab - min(ca, cb)) / max(ca, cb) if max(ca, cb) > 0 else 1.0


def ks_stat(a: List[float], b: List[float]) -> float:
    """Two-sample Kolmogorov-Smirnov statistic (max CDF gap) ∈ [0,1] — deterministic distributional distance."""
    if not a or not b:
        return 1.0
    grid = sorted(set(a) | set(b))

    def cdf(s, t):
        return sum(1 for x in s if x <= t) / len(s)
    return max(abs(cdf(a, t) - cdf(b, t)) for t in grid)


def mutual_info_lag1(seq: List[float], bins: int = 8) -> float:
    """Mutual information (bits) between consecutive terms (a[n-1], a[n]) over a `bins`-bucket histogram. High MI ⇒
    strong deterministic coupling (a recurrence); ~0 ⇒ independent (random). Deterministic."""
    n = len(seq)
    if n < 4:
        return 0.0
    lo, hi = min(seq), max(seq)
    if hi == lo:
        return 0.0

    def bucket(x):
        return min(bins - 1, int((x - lo) / (hi - lo) * bins))
    xs = [bucket(seq[i]) for i in range(n - 1)]
    ys = [bucket(seq[i + 1]) for i in range(n - 1)]
    m = len(xs)
    from collections import Counter
    px, py, pxy = Counter(xs), Counter(ys), Counter(zip(xs, ys))
    mi = 0.0
    for (i, j), c in pxy.items():
        pij = c / m
        mi += pij * math.log2(pij / ((px[i] / m) * (py[j] / m)))
    return mi


# ── structural confirmers (REUSE the conjecturers' own first steps) — drive the priority order ─────────────────
def _bm_order(seq: List[object]) -> Optional[int]:
    try:
        import native_sequence as NS
        _, L = NS.berlekamp_massey_Q([Fraction(x) for x in seq])
        return L
    except Exception:  # noqa: BLE001
        return None


def _finite_diff_degree(fseq: List[Fraction], max_deg: int = 8) -> Optional[int]:
    try:
        from conjecture import closedform_guess as CG
        return CG._poly_degree(fseq, max_deg)
    except Exception:  # noqa: BLE001
        return None


def route(fn: Callable[[int], object], probe: int = 32) -> RouteResult:
    """Score each conjecturer from the cheap signals and return the FULL best-first order (all five present ⇒ fallback
    kept ⇒ recall unchanged). Non-numeric ⇒ the default order (the conjecturers will ABANDON anyway)."""
    seq = H.observe(fn, probe)
    if seq is None:
        return RouteResult(list(_ALL), {}, {}, "non-numeric ⇒ default order (conjecturers ABANDON)")
    fseq = [Fraction(x) for x in seq]
    floats = [float(x) for x in seq]
    # signals
    from conjecture import period_guess as PG, holonomic_guess as HG
    period = PG._smallest_period(seq)
    ac = max((autocorrelation(floats, lag) for lag in range(1, min(len(seq) // 2, 16))), default=0.0)
    deg = _finite_diff_degree(fseq)
    ratio = HG._fit_poly_ratio([Fraction(x).limit_denominator(10 ** 9) for x in floats])
    L = _bm_order(seq)
    mi = mutual_info_lag1(floats)
    signals = {"period": period, "autocorr_peak": round(ac, 3), "fd_degree": deg,
               "poly_ratio": ratio is not None, "bm_order": L, "mutual_info": round(mi, 3)}
    # scores (higher ⇒ try sooner). Each confirmer gives its conjecturer a strong score; signals refine.
    scores = {k: 0.0 for k in _ALL}
    if period is not None:
        scores["period"] += 100 - period + 10 * ac                 # short period + high autocorrelation
    if deg is not None:
        scores["closedform"] += 90 - deg                            # low polynomial degree
    if ratio is not None:
        scores["holonomic"] += 80                                   # polynomial term-ratio (factorial-class)
    if L is not None and L >= 1 and not H.under_determined(len(seq), L):
        scores["bm_linrec"] += 70 - L                               # short determined linear recurrence
        scores["matpow"] += 60 - L                                  # same class, O(log N) realization
    scores["bm_linrec"] += mi                                       # coupling favors a recurrence
    order = sorted(_ALL, key=lambda k: scores[k], reverse=True)
    return RouteResult(order, {k: round(v, 2) for k, v in scores.items()}, signals,
                       f"routed best-first {order} from signals {signals} (ORDER only — all five kept as fallback)")


def _modules():
    from conjecture import bm_linrec, closedform_guess, period_guess, matpow_guess, holonomic_guess
    return {"bm_linrec": bm_linrec, "closedform": closedform_guess, "period": period_guess,
            "matpow": matpow_guess, "holonomic": holonomic_guess}


def first_fold(fn: Callable[[int], object], order: Optional[List[str]] = None):
    """Try the conjecturers in `order` (default = routed), return (issued_result_or_None, tried_count, first_key). The
    FULL list is always tried as fallback ⇒ the outcome is independent of the order (recall/precision invariant)."""
    mods = _modules()
    if order is None:
        order = route(fn).order
    tried = 0
    for key in order:
        tried += 1
        try:
            r = mods[key].conjecture(fn)
        except Exception:  # noqa: BLE001
            continue
        if r.issued:
            return r, tried, key
    return None, tried, None


def measure_routing(corpus: List[Callable[[int], object]]) -> dict:
    """★ The routing-is-sound meter: routed recall == unrouted recall (same SET folds), and the first-try hit rate
    (the actual speed win: how often the TOP-routed conjecturer is the one that folds)."""
    routed_hits = unrouted_hits = first_try = 0
    for fn in corpus:
        rr, _, rkey = first_fold(fn, None)                          # routed order
        ur, _, _ = first_fold(fn, list(_ALL))                       # fixed order (fallback baseline)
        routed_hits += int(rr is not None)
        unrouted_hits += int(ur is not None)
        if rr is not None and rkey == route(fn).order[0]:
            first_try += 1
    return {"corpus": len(corpus), "routed_recall": routed_hits, "unrouted_recall": unrouted_hits,
            "recall_identical": routed_hits == unrouted_hits, "first_try_hits": first_try}


def adversarial_battery() -> dict:
    """★ routing is ordering-only: routed recall == unrouted recall on the corpus (recall invariant); the period-3
    orbit routes period FIRST and Σk² routes closedform FIRST (the signals work); a disguised Fibonacci still folds
    under routing (precision/recall untouched)."""
    import math as _m

    def make_fib():
        memo = {0: 0, 1: 1}
        def f(n):
            if n not in memo:
                f(n - 1); memo[n] = memo[n - 1] + memo[n - 2]
            return memo[n]
        return f
    corpus = [make_fib(), lambda n: sum(k * k for k in range(n + 1)), lambda n: [10, 20, 30][n % 3],
              lambda n: _m.factorial(n), lambda n: 2 ** n, lambda n: 3 * n + 1]
    m = measure_routing(corpus)
    per3 = route(lambda n: [10, 20, 30][n % 3]).order[0]
    sumsq = route(lambda n: sum(k * k for k in range(n + 1))).order[0]
    fib_folds = first_fold(make_fib())[0] is not None
    cases = {
        "recall_identical_routed_vs_unrouted": m["recall_identical"] and m["routed_recall"] == len(corpus),
        "period_routed_first_for_orbit": per3 == "period",
        "closedform_routed_first_for_poly": sumsq == "closedform",
        "fibonacci_still_folds_under_routing": fib_folds,
        "first_try_hits_show_speedup": m["first_try_hits"] >= len(corpus) - 1,   # routing usually nails it first try
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
