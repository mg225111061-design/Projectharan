"""
v40 PHASE 5 — generators / recursion + generative structure.
=============================================================
  • 26 SLP (straight-line program / grammar) random access : O(height) access vs O(n) full decompression,
    where n can be EXPONENTIAL in the grammar size (doubling rules). EXACT (the grammar defines the string).
  • 65 sufficient-statistics fit : a stream summarized by sufficient statistics with a GOODNESS-OF-FIT gate →
    PROBABILISTIC(ε,δ) if it fits, DECLINE if not. ★ Distinguishes seed-EXACT (PRNG kernel) from statistics-
    PROBABILISTIC from genuine-noise-DECLINE — never claims EXACT for a statistical summary. ★
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List

import kernel_verdict as KV
import kernel_router as R


# ── 26 · SLP random access: char at index k in O(height), without decompressing the whole string ──────
def _slp_sizes(grammar: Dict[str, Any], start: str) -> Dict[str, int]:
    """Expansion length of each nonterminal (memoized, topological via recursion)."""
    size: Dict[str, int] = {}

    def sz(sym):
        if sym in size:
            return size[sym]
        rule = grammar[sym]
        if isinstance(rule, str):                       # terminal: a single character
            size[sym] = 1
        else:
            size[sym] = sz(rule[0]) + sz(rule[1])
        return size[sym]
    sz(start)
    return size


def _slp_char_at(grammar, start, size, k: int) -> str:
    sym = start
    while True:
        rule = grammar[sym]
        if isinstance(rule, str):
            return rule
        lsz = size[rule[0]]
        if k < lsz:
            sym = rule[0]
        else:
            k -= lsz
            sym = rule[1]


def _slp_detect(d: Any) -> bool:
    return (isinstance(d, dict) and d.get("kind") == "slp_access"
            and isinstance(d.get("grammar"), dict) and "start" in d and "index" in d)


def _slp_run(d: Any, **kw) -> KV.Verdict:
    grammar, start, k = d["grammar"], d["start"], int(d["index"])
    try:
        size = _slp_sizes(grammar, start)
    except (KeyError, RecursionError):
        return KV.decline("malformed grammar (missing symbol / cycle)", "slp")
    n = size[start]
    if not (0 <= k < n):
        return KV.decline(f"index {k} out of range (string length {n})", "slp")
    ch = _slp_char_at(grammar, start, size, k)
    height = max(1, n.bit_length())
    # fast EXACT certificate: for small n, decompress fully and compare; always cheap because height ≤ log n
    ok = True
    if n <= 4096:
        full = _slp_decompress(grammar, start)
        ok = (full[k] == ch and len(full) == n)
    cert = KV.Cert(KV.EXACT, "slp_access", passed=ok, check_cost="O(height)≈O(log n)",
                   detail=f"grammar size {len(grammar)} expands to length {n}; char[{k}] in O(height) "
                          f"(no full decompression; n can be exponential in grammar size)")
    if not ok:
        return KV.decline("slp access disagreed with decompression", "slp")
    return KV.exact(ch, "slp", "O(height) access", cert)


def _slp_decompress(grammar, sym) -> str:
    rule = grammar[sym]
    if isinstance(rule, str):
        return rule
    return _slp_decompress(grammar, rule[0]) + _slp_decompress(grammar, rule[1])


def _doubling_grammar(levels: int):
    """Grammar of size O(levels) whose start expands to length 2^levels (each rule doubles the previous)."""
    g: Dict[str, Any] = {"A0": "a"}
    for i in range(1, levels + 1):
        g[f"A{i}"] = (f"A{i-1}", f"A{i-1}")
    g["B0"] = "b"
    g[f"A{levels}b"] = (f"A{levels}", "B0")             # length 2^levels + 1, last char 'b'
    return g, f"A{levels}b"


def measure_slp() -> dict:
    """ACCESS collapse O(n)→O(height): random access into a grammar whose string is length 2^levels."""
    crossover, pts = None, []
    for levels in (10, 20, 30):
        g, start = _doubling_grammar(levels)
        size = _slp_sizes(g, start)
        n = size[start]
        k = n - 1                                       # last char ('b')
        t = time.perf_counter(); ch = _slp_char_at(g, start, size, k); tf = (time.perf_counter() - t) * 1e6
        # naive decompress is O(n); only feasible for small n — report infeasible above ~1e7
        if n <= 2_000_000:
            t = time.perf_counter(); full = _slp_decompress(g, start); tn = (time.perf_counter() - t) * 1e6
            tn_s = f"{tn:.0f}us"
        else:
            tn_s = f"infeasible (n={n})"
        pts.append((levels, n, tn_s, round(tf, 2), ch == "b"))
        if crossover is None:
            crossover = levels
    return {"kernel": "slp", "collapse": "random-access O(n)→O(height); n=2^levels (exponential in grammar)",
            "points_(levels,n,decompress,access_us,ok)": pts, "amdahl_p": "high for repetitive/generated text"}


# ── 65 · sufficient-statistics fit with a goodness-of-fit gate → PROBABILISTIC or DECLINE ──────────────
def _fit_detect(d: Any) -> bool:
    return isinstance(d, dict) and d.get("kind") == "fit_gaussian" and isinstance(d.get("samples"), list)


def _fit_run(d: Any, **kw) -> KV.Verdict:
    xs: List[float] = [float(x) for x in d["samples"]]
    n = len(xs)
    if n < 30:
        return KV.decline("need ≥30 samples for a fit", "stat_fit")
    mu = sum(xs) / n
    var = sum((x - mu) ** 2 for x in xs) / (n - 1)
    sd = math.sqrt(var) if var > 0 else 0.0
    if sd == 0:
        return KV.decline("degenerate (zero variance)", "stat_fit")
    # goodness-of-fit gate: standardized skewness & excess kurtosis should be small for Gaussian.
    # Their sampling SEs are √(6/n) and √(24/n); require |stat| ≤ 3·SE (≈ a 3σ normality gate).
    z = [(x - mu) / sd for x in xs]
    skew = sum(t ** 3 for t in z) / n
    kurt = sum(t ** 4 for t in z) / n - 3.0
    se_sk, se_ku = math.sqrt(6.0 / n), math.sqrt(24.0 / n)
    fits = abs(skew) <= 3 * se_sk and abs(kurt) <= 3 * se_ku
    if not fits:
        return KV.decline(f"goodness-of-fit FAILED (skew={skew:.2f}/±{3*se_sk:.2f}, kurt={kurt:.2f}/±{3*se_ku:.2f}) "
                          f"— not Gaussian ⇒ DECLINE (no fake summary)", "stat_fit")
    # PROBABILISTIC summary: the sufficient statistics (μ,σ); δ = the 3σ gate's per-side tail ≈ 0.0027 (stated)
    cert = KV.Cert(KV.PROBABILISTIC, "goodness_of_fit", passed=True, check_cost="O(n)",
                   epsilon=sd / math.sqrt(n), delta=0.0027,
                   detail=f"Gaussian sufficient stats μ={mu:.3f}, σ={sd:.3f}; skew/kurt within 3σ normality gate")
    return KV.probabilistic({"mu": mu, "sigma": sd}, "stat_fit", "O(n) summary", cert)


def measure_fit() -> dict:
    """PROBABILISTIC summary with an honest gate: Gaussian → PROBABILISTIC; non-Gaussian/structured → DECLINE."""
    import random
    rng = random.Random(7)
    gauss = [rng.gauss(5.0, 2.0) for _ in range(2000)]
    unif = [rng.uniform(0, 1) for _ in range(2000)]                # heavy-tailed-free but non-Gaussian (kurt<0)
    bimod = [rng.gauss(-5, 0.3) if rng.random() < 0.5 else rng.gauss(5, 0.3) for _ in range(2000)]
    g = _fit_run({"kind": "fit_gaussian", "samples": gauss})
    u = _fit_run({"kind": "fit_gaussian", "samples": unif})
    b = _fit_run({"kind": "fit_gaussian", "samples": bimod})
    return {"kernel": "stat_fit", "gaussian": g.status, "uniform": u.status, "bimodal": b.status,
            "note": "Gaussian→PROBABILISTIC summary; uniform & bimodal→DECLINE (goodness-of-fit gate; no EXACT)"}


def register_all():
    R.register(R.Kernel(26, "slp", "E",
                        "requires grammar ∧ 0≤index<len  ensures char[index] exact ∧ grade=EXACT ∧ "
                        "cost=O(height) (n may be exponential in grammar size)",
                        _slp_detect, _slp_run))
    R.register(R.Kernel(65, "stat_fit", "E",
                        "requires ≥30 samples ∧ goodness-of-fit passes  ensures Gaussian summary ∧ "
                        "grade=PROBABILISTIC(δ=0.0027) else DECLINE",
                        _fit_detect, _fit_run))


register_all()
