"""
Pillar 3 · ROUND 2 — the Ω(N) side-door: trade exactness for sublinearity (PROBABILISTIC, REPORT ε,δ).
=====================================================================================================
An exact aggregate over N items is Ω(N). The side-door: SAMPLE k≪N items and answer within ε with confidence
1−δ — cost independent of N. This is **never EXACT**: it is PROBABILISTIC and the ε,δ are first-class and
reported. `approx_grade` measures the whole-program speedup (coherent, ratio ≤ ceiling) AND the empirical ε
(95th-pct relative error over many trials) and δ (fraction outside the ε target); a biased estimator whose
error exceeds the target ⇒ DECLINE (the safety net — you cannot ship an approximation that isn't within ε).
"""
from __future__ import annotations

import random as _rnd
from dataclasses import dataclass
from typing import Any, Callable, Tuple

import kernel_verdict as KV
from pillar3 import lifting as LF

try:
    import numba as _numba
    import numpy as _np
    _NUMBA = True
except Exception:                                           # numba/llvmlite absent ⇒ item 31/#3 UNVERIFIED
    _NUMBA = False


@dataclass
class ApproxResult:
    verdict: "KV.Verdict"
    eps: float
    delta: float
    ratio: float
    ceiling: float


def approx_grade(exact_fn: Callable, approx_fn: Callable, make_input: Callable[[], tuple], residual_iters: int,
                 *, eps_target: float, n: int, samples: int = 7, trials: int = 60) -> ApproxResult:
    """Grade an APPROXIMATION. ε = 95th-percentile relative error of approx vs exact over `trials` inputs;
    δ = fraction of trials outside eps_target. PROBABILISTIC(ε,δ) iff ε ≤ target AND δ small AND a measured win;
    else DECLINE. Approximation is NEVER EXACT (Constitution Rule 3)."""
    errs = []
    for _ in range(trials):
        args = make_input()
        e = float(exact_fn(*args))
        a = float(approx_fn(*args))
        errs.append(abs(a - e) / (abs(e) + 1e-9))
    errs.sort()
    eps = errs[min(len(errs) - 1, int(0.95 * len(errs)))]
    delta = sum(1 for x in errs if x > eps_target) / len(errs)
    rep = LF.measure_lift(exact_fn, approx_fn, make_input, residual_iters, n=n, samples=samples)
    if eps > eps_target or delta > 0.1:
        v = KV.decline(f"approximation ε={eps:.4f} > target {eps_target} (δ={delta:.2f}) ⇒ DECLINE", "approx")
        v.report = rep
        return ApproxResult(v, eps, delta, rep.whole_program_ratio, rep.amdahl_ceiling)
    if not rep.beats(1.10):
        v = KV.decline(f"approximation within ε but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "approx")
        v.report = rep
        return ApproxResult(v, eps, delta, rep.whole_program_ratio, rep.amdahl_ceiling)
    cert = KV.Cert(KV.PROBABILISTIC, "sampling_approximation", passed=True, check_cost=f"{trials} trials",
                   delta=max(delta, 1e-6), detail=f"ε={eps:.4f} (95th pct), within-target {(1-delta):.0%}, cost ⟂ N")
    v = KV.probabilistic(approx_fn, "approx", str(rep), cert)
    v.report = rep
    return ApproxResult(v, eps, delta, rep.whole_program_ratio, rep.amdahl_ceiling)


# ── item 46 — sublinear approximation by sampling (mean of a huge array): O(N) → O(k), cost ⟂ N ──────────
_BIG_CACHE: dict = {}


def _make_big(n: int = 500000):
    if n not in _BIG_CACHE:
        rng = _rnd.Random(91)
        # bounded-variance values so a sample mean is within a few % of the true mean
        _BIG_CACHE[n] = [rng.gauss(100.0, 15.0) for _ in range(n)]
    return (_BIG_CACHE[n],)


def mean_exact(a):
    return sum(a) / len(a)


def mean_sampled(a):                                        # O(k): a fixed-size random sample, cost independent of N
    n = len(a)
    k = 2000
    if n <= k:
        return sum(a) / n
    rng = _rnd.Random(7)
    s = 0.0
    for _ in range(k):
        s += a[rng.randrange(n)]
    return s / k


def mean_biased(a):                                        # adversarial: only the smallest region ⇒ biased estimate
    k = 2000
    if len(a) <= k:
        return sum(a) / len(a)
    head = sorted(a[: k * 3])[:k]                          # systematically low ⇒ ε large ⇒ DECLINE
    return sum(head) / k


# ── item 49 — membership filter (Bloom): exact O(n) list membership → O(1) filter, FP ε, NO false negatives ─
import math as _math


class Bloom:
    def __init__(self, n: int, fp: float = 0.01):
        n = max(1, n)
        self.m = max(8, int(-n * _math.log(fp) / (_math.log(2) ** 2)))
        self.k = max(1, int(round(self.m / n * _math.log(2))))
        self.bits = bytearray((self.m + 7) // 8)

    def _idx(self, x, i):
        return (hash((x, i, 0x9E3779B1)) % self.m)

    def add(self, x):
        for i in range(self.k):
            j = self._idx(x, i)
            self.bits[j >> 3] |= (1 << (j & 7))

    def __contains__(self, x):
        for i in range(self.k):
            j = self._idx(x, i)
            if not (self.bits[j >> 3] >> (j & 7)) & 1:
                return False
        return True


def membership_exact(pool, queries):                        # pool is a LIST ⇒ each `in` is O(n)
    return [q in pool for q in queries]


def membership_bloom(pool, queries):                        # O(1)/query, false-positive ε, zero false negatives
    b = Bloom(len(pool))
    for x in pool:
        b.add(x)
    return [q in b for q in queries]


def membership_bloom_broken(pool, queries):                 # adversarial: adds only half ⇒ FALSE NEGATIVES ⇒ DECLINE
    b = Bloom(len(pool))
    for x in pool[::2]:
        b.add(x)
    return [q in b for q in queries]


def bloom_grade(pool, queries, residual_iters=0, *, approx_fn=None, eps_target=0.08, n=0, samples=7):
    approx_fn = approx_fn or membership_bloom
    exact = membership_exact(pool, queries)
    approx = approx_fn(pool, queries)
    false_neg = sum(1 for e, a in zip(exact, approx) if e and not a)
    false_pos = sum(1 for e, a in zip(exact, approx) if a and not e)
    nonmembers = sum(1 for e in exact if not e)
    eps = false_pos / max(1, nonmembers)
    rep = LF.measure_lift(lambda p, q: membership_exact(p, q), lambda p, q: approx_fn(p, q),
                          lambda: (pool, queries), residual_iters, n=n, samples=samples)
    if false_neg > 0:                                       # the Bloom invariant: NO false negatives
        v = KV.decline(f"Bloom produced {false_neg} FALSE NEGATIVES (invariant broken) ⇒ DECLINE", "approx")
        v.report = rep
        return ApproxResult(v, eps, 0.0, rep.whole_program_ratio, rep.amdahl_ceiling)
    if eps > eps_target or not rep.beats(1.10):
        v = KV.decline(f"Bloom FP ε={eps:.3f} > {eps_target} or no win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "approx")
        v.report = rep
        return ApproxResult(v, eps, 0.0, rep.whole_program_ratio, rep.amdahl_ceiling)
    cert = KV.Cert(KV.PROBABILISTIC, "bloom_filter", passed=True, check_cost=f"{len(queries)} queries",
                   delta=max(eps, 1e-6), detail=f"false-positive ε={eps:.4f}, ZERO false negatives (verified)")
    v = KV.probabilistic(approx_fn, "approx", str(rep), cert)
    v.report = rep
    return ApproxResult(v, eps, 0.0, rep.whole_program_ratio, rep.amdahl_ceiling)


_BLOOM_CACHE: dict = {}


def make_bloom_input(npool=3000, nq=3000):
    key = (npool, nq)
    if key not in _BLOOM_CACHE:
        rng = _rnd.Random(101)
        pool = [rng.randrange(0, npool * 8) for _ in range(npool)]
        pset = set(pool)
        # ~30% members, 70% non-members (so the exact O(n) scan dominates and Bloom's O(1) pre-check wins)
        q = []
        for _ in range(nq):
            q.append(rng.choice(pool) if rng.random() < 0.3 else rng.randrange(npool * 8, npool * 16))
        _BLOOM_CACHE[key] = (pool, q)
    return _BLOOM_CACHE[key]



# ── item 31/#3 — whole-region NATIVE COMPILATION via numba/llvmlite (remove interpreter overhead) ────────
# The structure-free ~80% lever: the SAME arithmetic, compiled to native, removes per-element interpreter
# overhead. Graded PROBABILISTIC (float-tolerant differential — native FP reassociation can differ in the last
# ULPs); measured whole-program, Amdahl-gated. UNVERIFIED [no numba] if the toolchain is absent.
if _NUMBA:
    @_numba.njit(cache=True)
    def _native_kernel(a):
        s = 0.0
        for i in range(a.shape[0]):
            x = a[i]
            s += x * x * x - 2.0 * x * x + 3.0 * x - 1.0
        return s

    @_numba.njit(cache=True)
    def _native_kernel_wrong(a):
        s = 0.0
        for i in range(a.shape[0]):
            x = a[i]
            s += x * x * x - 2.0 * x * x + 3.0 * x + 1.0     # +1 instead of -1 ⇒ wrong
        return s


def native_naive(a):
    s = 0.0
    for i in range(a.shape[0]):
        x = a[i]
        s += x * x * x - 2.0 * x * x + 3.0 * x - 1.0
    return s


def native_fast(a):
    return float(_native_kernel(a))


def native_wrong(a):
    return float(_native_kernel_wrong(a))


_NAT_CACHE: dict = {}


def make_native_input(n=300000):
    if n not in _NAT_CACHE:
        _NAT_CACHE[n] = _np.random.default_rng(13).standard_normal(n)
    return (_NAT_CACHE[n],)


def native_grade(make_input, fast_fn=None, residual_iters=0, *, n, samples=7, tol=1e-6):
    """Differential FIRST (float-tolerant), then a coherent whole-program measurement; PROBABILISTIC (native FP
    may differ in the last ULPs). Wrong arithmetic ⇒ DECLINE. UNVERIFIED [no numba] if the toolchain is absent."""
    if not _NUMBA:
        v = KV.decline("native compile UNVERIFIED [no numba/llvmlite in sandbox] — transform built, excluded", "native")
        return v, None
    fast_fn = fast_fn or native_fast
    a0 = make_input()[0]
    fast_fn(a0[:16])                                          # pre-warm (compile) — excluded from timing
    diverged = False
    for _ in range(8):
        args = make_input()
        e = native_naive(*args)
        g = fast_fn(*args)
        if abs(e - g) > tol * (1 + abs(e)):
            diverged = True
            break
    rep = LF.measure_lift(native_naive, fast_fn, make_input, residual_iters, n=n, samples=samples)
    if diverged:
        v = KV.decline("native result diverges from the interpreted original ⇒ DECLINE", "native")
        v.report = rep
        return v, rep
    if not rep.beats(1.10):
        v = KV.decline(f"native but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "native")
        v.report = rep
        return v, rep
    cert = KV.Cert(KV.PROBABILISTIC, "native_compile", passed=True, check_cost="8 float cases",
                   delta=3.0 / 8, detail=f"numba/llvmlite native; float-tolerant differential (tol={tol}); ratio≤ceiling")
    v = KV.probabilistic(fast_fn, "native", str(rep), cert)
    v.report = rep
    return v, rep


# ── items 47/48/50 — sublinear-MEMORY sketches: bounded memory for an unbounded stream (PROBABILISTIC, ε) ──
# These trade exactness for O(1)/sublinear MEMORY (not wall-clock): the value is answering a stream query with
# memory independent of N. Graded PROBABILISTIC with a REPORTED ε; an undersized sketch ⇒ ε too large ⇒ DECLINE.
import math as _m2


def hll_estimate(stream, p: int = 12):
    """HyperLogLog distinct-count estimate using 2^p registers (memory O(2^p), INDEPENDENT of the stream length)."""
    m = 1 << p
    reg = [0] * m
    maxbits = 64 - p
    for x in stream:
        h = hash((x, 0x9E3779B9)) & 0xFFFFFFFFFFFFFFFF
        idx = h & (m - 1)
        w = h >> p
        rank = (maxbits - w.bit_length() + 1) if w else (maxbits + 1)   # leftmost 1-bit (leading zeros + 1)
        if rank > reg[idx]:
            reg[idx] = rank
    alpha = 0.7213 / (1 + 1.079 / m)
    E = alpha * m * m / sum(2.0 ** -r for r in reg)
    V = reg.count(0)
    if E <= 2.5 * m and V:
        E = m * _m2.log(m / V)                              # small-range correction
    return E


def cardinality_grade(make_stream, *, p: int = 12, eps_target: float = 0.06, trials: int = 9, n: int = 0):
    """PROBABILISTIC distinct-count: 95th-pct relative error of HLL vs the exact set over `trials` streams; memory
    is O(2^p) registers regardless of N. ε ≤ target ⇒ PROBABILISTIC(ε); else DECLINE (sketch too small)."""
    errs = []
    for _ in range(trials):
        s = make_stream()
        exact = len(set(s))
        est = hll_estimate(s, p)
        errs.append(abs(est - exact) / max(1, exact))
    errs.sort()
    eps = errs[min(len(errs) - 1, int(0.95 * len(errs)))]
    if eps > eps_target:
        return KV.decline(f"HLL ε={eps:.4f} > target {eps_target} (p={p} too small) ⇒ DECLINE", "sketch")
    cert = KV.Cert(KV.PROBABILISTIC, "hyperloglog", passed=True, check_cost=f"{1 << p} registers (O(1) vs O(distinct))",
                   delta=max(eps, 1e-6), detail=f"distinct-count ε={eps:.4f} (95th pct), memory ⟂ N ({1 << p} regs)")
    return KV.probabilistic(hll_estimate, "sketch", f"O(1) memory ({1 << p} regs)", cert)


def count_min(stream, d: int = 5, w: int = 1000):
    """Count-Min frequency sketch (d×w counters, sublinear memory): a ONE-SIDED OVER-estimate of each item's count."""
    table = [[0] * w for _ in range(d)]
    for x in stream:
        for i in range(d):
            table[i][hash((x, i, 17)) % w] += 1
    return lambda x: min(table[i][hash((x, i, 17)) % w] for i in range(d))


def frequency_grade(make_stream, *, d: int = 5, w: int = 1000, eps_target: float = 0.05, trials: int = 7):
    """PROBABILISTIC frequency: Count-Min never UNDER-estimates (invariant); ε = max relative over-estimate vs the
    exact Counter, normalised by stream length, over `trials`. ε ≤ target ⇒ PROBABILISTIC; a false UNDER-estimate
    (broken sketch) ⇒ DECLINE (invariant broken); ε too large ⇒ DECLINE (table too small)."""
    from collections import Counter
    eps_max = 0.0
    for _ in range(trials):
        s = make_stream()
        exact = Counter(s)
        cm = count_min(s, d, w)
        N = max(1, len(s))
        if any(cm(k) < exact[k] for k in exact):            # the one-sided invariant: never under-estimate
            return KV.decline("Count-Min UNDER-estimated a count (invariant broken) ⇒ DECLINE", "sketch")
        eps_max = max(eps_max, max((cm(k) - exact[k]) for k in exact) / N)
    if eps_max > eps_target:
        return KV.decline(f"Count-Min over-estimate ε={eps_max:.4f} > {eps_target} (table {d}×{w} too small) ⇒ DECLINE", "sketch")
    cert = KV.Cert(KV.PROBABILISTIC, "count_min", passed=True, check_cost=f"{d}×{w} counters (sublinear)",
                   delta=max(eps_max, 1e-6), detail=f"frequency over-estimate ε={eps_max:.4f}, one-sided (never under)")
    return KV.probabilistic(count_min, "sketch", f"{d}×{w} counters", cert)


def reservoir_sample(stream, k: int = 100):
    """One-pass uniform sample of k items from a stream of UNKNOWN length, O(k) memory (never materialises N)."""
    res = []
    for i, x in enumerate(stream):
        if i < k:
            res.append(x)
        else:
            j = _rnd.Random(i * 2654435761 & 0xFFFFFFFF).randrange(i + 1)   # deterministic per-index for testability
            if j < k:
                res[j] = x
    return res


# deterministic-but-distinct per-call seeds (§0 reproducibility: a flaky unseeded stream cannot be trusted to <2%;
# a fixed base + per-call counter gives independent trials that are REPRODUCIBLE across runs).
_STREAM_SEED = [0]


def _make_card_stream(n: int = 200000):
    _STREAM_SEED[0] += 1
    rng = _rnd.Random(0xC0FFEE ^ _STREAM_SEED[0])
    return [rng.randrange(n * 3) for _ in range(n)]


def _make_freq_stream(n: int = 80000, keys: int = 800):
    _STREAM_SEED[0] += 1
    rng = _rnd.Random(0xBEEF ^ _STREAM_SEED[0])
    return [rng.randrange(keys) for _ in range(n)]


# ── item 40 — serialization swap: json round-trip → marshal round-trip (lossless, measured) ──────────────
import json as _json
import marshal as _marshal


def json_roundtrip(o):
    return _json.loads(_json.dumps(o))


def marshal_roundtrip(o):
    return _marshal.loads(_marshal.dumps(o))


def marshal_roundtrip_lossy(o):                            # adversarial: drops the last record ⇒ differential catches
    data = _marshal.dumps(o)
    out = _marshal.loads(data)
    return out[:-1] if isinstance(out, list) and out else out


def _make_serial_obj(n: int = 4000):
    return [{"id": i, "name": f"row-{i}", "vals": [i, i * 2, i * 3], "ok": i % 2 == 0} for i in range(n)]


def serialization_grade(make_obj, fast_fn=None, *, n: int, samples: int = 5, residual_iters: int = 0, floor: float = 1.20):
    """A serialization round-trip swap (json→marshal): the fast round-trip must reproduce the object EXACTLY
    (differential) AND measure a whole-program win. Lossless+win ⇒ PROBABILISTIC (round-trip verified on the
    workload, not proven for all objects ⇒ never EXACT); a lossy serializer ⇒ DECLINE."""
    fast_fn = fast_fn or marshal_roundtrip
    o = make_obj()
    if json_roundtrip(o) != o or fast_fn(o) != o:
        return KV.decline("serialization round-trip is LOSSY (≠ original) ⇒ DECLINE", "serialize")
    rep = LF.measure_lift(lambda x: json_roundtrip(x), lambda x: fast_fn(x), lambda: (o,), residual_iters, n=n, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"serialization swap but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "serialize")
        v.report = rep
        return v
    cert = KV.Cert(KV.PROBABILISTIC, "lossless_serialization_swap", passed=True, check_cost="round-trip==original",
                   delta=1e-6, detail=f"marshal round-trip lossless on the workload (verified), ×{rep.whole_program_ratio:.2f}")
    v = KV.probabilistic(fast_fn, "serialize", str(rep), cert)
    v.report = rep
    return v


# ── items 32/34 — type specialization / devirtualization: monomorphic dispatch → direct op ──────────────
def process_poly(items):
    """Polymorphic per-element dispatch (an isinstance chain — the dynamic-dispatch overhead)."""
    out = []
    for x in items:
        if isinstance(x, bool):
            out.append(2 if x else 0)
        elif isinstance(x, int):
            out.append(x * x)
        elif isinstance(x, float):
            out.append(x * 2.0)
        elif isinstance(x, str):
            out.append(len(x))
        else:
            out.append(None)
    return out


def process_int_specialized(items):
    return [x * x for x in items]                          # devirtualized: type proven int ⇒ direct op


def process_int_wrong(items):
    return [x * x + 1 for x in items]                      # wrong specialization ⇒ differential catches


def _is_monomorphic(items, ty=int):
    return bool(items) and all(type(x) is ty for x in items)


def typespec_grade(make_input, fast_fn=None, *, n: int, samples: int = 5, residual_iters: int = 0, floor: float = 1.20):
    """Specialize a polymorphic dispatch to a monomorphic direct op. Sound guard: the input must be PROVEN
    monomorphic (all the same concrete type) AND the specialized result must match the polymorphic one
    (differential). Monomorphic+match+win ⇒ PROBABILISTIC; non-monomorphic OR mismatch ⇒ DECLINE."""
    fast_fn = fast_fn or process_int_specialized
    items = make_input()[0]
    if not _is_monomorphic(items, int):                    # the soundness guard — can't devirtualize a polymorphic site
        return KV.decline("call site is NOT monomorphic (mixed types) ⇒ cannot specialize ⇒ DECLINE", "typespec")
    if process_poly(items) != fast_fn(items):
        return KV.decline("specialized result ≠ polymorphic result ⇒ DECLINE", "typespec")
    rep = LF.measure_lift(lambda x: process_poly(x), lambda x: fast_fn(x), make_input, residual_iters, n=n, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"specialized but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "typespec")
        v.report = rep
        return v
    cert = KV.Cert(KV.PROBABILISTIC, "type_specialization", passed=True, check_cost="monomorphism guard + differential",
                   delta=1e-6, detail=f"monomorphic (all int) ⇒ devirtualized direct op, ×{rep.whole_program_ratio:.2f}; dispatch removed")
    v = KV.probabilistic(fast_fn, "typespec", str(rep), cert)
    v.report = rep
    return v


def _make_mono_int(n: int = 200000):
    return ([i for i in range(n)],)


def _make_polymorphic(n: int = 200000):
    return ([(i if i % 3 else float(i)) for i in range(n)],)   # mixed int/float ⇒ NOT monomorphic


# ── item 57 — dead-code / unreachable-branch elimination: Z3 proves the guard UNSAT ⇒ block is dead ──────
import z3 as _z3


def dead_branch_grade(name, guard):
    """Z3 proves the branch guard is UNSATISFIABLE ⇒ the guarded block is unreachable (dead) ⇒ removing it is
    behavior-preserving ⇒ EXACT (verified). A SATISFIABLE guard ⇒ the block is reachable ⇒ DECLINE (live code)."""
    x = _z3.Int("x")
    s = _z3.Solver()
    s.add(guard(x))
    r = s.check()
    if r == _z3.unsat:
        cert = KV.Cert(KV.EXACT, "unreachable_proof", passed=True, check_cost="Z3 SAT(guard)=UNSAT",
                       detail=f"{name}: guard unsatisfiable ⇒ block dead ⇒ removable (behavior-preserving)")
        return KV.exact(name, f"deadcode:{name}", "verified DCE (Clock-B)", cert)
    if r == _z3.sat:
        return KV.decline(f"{name}: guard is SATISFIABLE (e.g. x={s.model()[x]}) ⇒ block is LIVE ⇒ DECLINE (keep it)", f"deadcode:{name}")
    return KV.decline(f"{name}: z3 unknown ⇒ conservatively keep the block ⇒ DECLINE", f"deadcode:{name}")


def dead_guards():
    return [("x2_lt_0", lambda x: x * x < 0), ("gt5_and_lt3", lambda x: _z3.And(x > 5, x < 3)),
            ("even_and_odd", lambda x: _z3.And(x % 2 == 0, x % 2 == 1))]


def live_guards():
    return [("gt5", lambda x: x > 5), ("eq42", lambda x: x == 42)]


# ── item 60 — loop unswitching: a loop-INVARIANT branch tested per-iteration → hoisted out (test once) ───
def loop_switched(a, flag):
    out = []
    for x in a:
        if flag:                                           # invariant: flag is loop-invariant ⇒ redundant per-iter test
            out.append(x * 2)
        else:
            out.append(x + 1)
    return out


def loop_unswitched(a, flag):
    return [x * 2 for x in a] if flag else [x + 1 for x in a]   # branch hoisted OUT of the loop


def loop_unswitched_wrong(a, flag):
    return [x * 2 for x in a] if not flag else [x + 1 for x in a]   # inverted ⇒ differential catches


def _make_unswitch_input(n=300000):
    return (list(range(n)), True)


def unswitch_grade(make_input, fast_fn=None, *, n, samples=5, residual_iters=0):
    """Hoist a loop-invariant branch out of the loop (test once, not per-iteration). The flag domain {True,False}
    is EXHAUSTIVELY checked (both branches) and the per-element op is identical ⇒ behavior-preserving ⇒ EXACT
    (a verified transform; pure-Python speed benefit is modest, the real win is at the compiled level). An
    inverted/wrong hoist ⇒ differential ⇒ DECLINE."""
    fast_fn = fast_fn or loop_unswitched
    a, flag = make_input()
    if loop_switched(a, flag) != fast_fn(a, flag) or loop_switched(a, not flag) != fast_fn(a, not flag):
        return KV.decline("unswitched result ≠ switched on the exhaustive flag domain (wrong hoist) ⇒ DECLINE", "unswitch")
    rep = LF.measure_lift(lambda ar, fl: loop_switched(ar, fl), lambda ar, fl: fast_fn(ar, fl),
                          make_input, residual_iters, n=n, samples=samples)
    cert = KV.Cert(KV.EXACT, "loop_unswitching_verified", passed=True, check_cost="exhaustive flag domain + identical op",
                   detail=f"loop-invariant branch hoisted (test once); flag∈{{T,F}} exhaustively verified, op identical "
                          f"⇒ behavior-preserving (measured ×{rep.whole_program_ratio:.2f}, modest in pure-Python)")
    v = KV.exact(fast_fn, "unswitch", str(rep), cert)
    v.report = rep
    return v
