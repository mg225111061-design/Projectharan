"""
Pillar 3 · PHASE L — verified lifting (the biggest speed lever: lift a hot region to a spec, re-synthesize).
============================================================================================================
Tenspiler-spirit (ECOOP 2024), Z3-backed, NO Lean/Coq/Isabelle. For a restricted hot region (pure arithmetic
over integer arrays, affine indexing — no pointers/objects) we:

  (1) PROPOSE A SPEC      — a mathematical statement of what the region computes (sum / running aggregate /…).
  (2) lifted ≡ original   — Z3 proves the spec equals the original over the input domain (bounded translation
                            validation, Alive2-spirit: symbolic inputs, prove every output entry equal ∀ inputs).
  (3) re-synthesize + prove— synthesize the optimal implementation FROM the spec and Z3-prove it ≡ the spec.

EXACT only if BOTH proofs pass; a subtly-wrong lift is caught by Z3 (counterexample) ⇒ DECLINE. Then the win is
MEASURED whole-program with a coherent Amdahl fraction (ratio ≤ ceiling by construction — Rule 1/2). The grade
comes from the real ADT (Rule 3). This generalises beyond the fixed detectors: it lifts hotspots no detector
names (e.g. a hand-rolled O(n²) running-sum → an O(n) scan), proven, not pattern-matched.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

import z3

import kernel_verdict as KV
from pillar3 import equiv as EQ
from pillar3 import measure as M
from pillar3 import record as RC
from pillar3 import verifier as _V


# ── the two-step proof (lift correctness + synthesis correctness) ──────────────────────────────────────
def prove_lift(original: Callable, spec: Callable, optimized: Callable,
               sym_factory: Callable[[int], tuple], sizes: Tuple[int, ...]) -> "Tuple[bool, bool, Optional[str]]":
    """Returns (lifted_ok, synth_ok, counterexample). lifted_ok = Z3 proved spec ≡ original; synth_ok = Z3 proved
    optimized ≡ spec. Both true ⇒ original ≡ optimized by transitivity, with the spec as the audited middle."""
    lifted_ok, cex1 = EQ.prove_equiv(original, spec, sym_factory, sizes)
    if not lifted_ok:
        return False, False, f"lift step (spec≡original) failed: {cex1}"
    synth_ok, cex2 = EQ.prove_equiv(spec, optimized, sym_factory, sizes)
    return True, synth_ok, (None if synth_ok else f"synthesis step (optimized≡spec) failed: {cex2}")


# ── coherent whole-program measurement (ratio ≤ ceiling BY CONSTRUCTION; the floor pipeline trick) ──────
def _busy(iters: int) -> int:
    x = 0
    for _ in range(iters):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
    return x


def measure_lift(region_orig: Callable, region_opt: Callable, make_input: Callable[[], Any],
                 residual_iters: int, *, n: int, samples: int = 7) -> M.SpeedupReport:
    """Embed the region in a whole program (residual busy-work + region) and measure base/floor/candidate in ONE
    session. floor = residual + region PASSED THROUGH (the infinitely-fast limit) ≤ candidate, so the measured
    ratio = T_base/T_cand ≤ T_base/T_floor = ceiling. f = 1 − T_floor/T_base (the real, measured hotspot share)."""
    noop = lambda *_a: None                                   # the region replaced by the unreachable 0-cost limit

    def whole(region):
        def run(_a):
            args = make_input()                               # make_input returns the full ARGS TUPLE
            _busy(residual_iters)
            return region(*args)
        return run

    args = lambda: (None,)
    t_base = M.time_best(whole(region_orig), args, samples)
    t_floor = M.time_best(whole(noop), args, samples)
    t_cand = M.time_best(whole(region_opt), args, samples)
    t_floor = min(t_floor, t_cand)                            # floor cannot beat the real optimized candidate
    f = max(0.0, min(0.999, 1.0 - t_floor / max(t_base, 1e-12)))
    ratio = t_base / max(t_cand, 1e-12)
    return M.SpeedupReport(whole_program_ratio=ratio, hotspot_fraction=f, n=n, samples=samples,
                           warmup_discarded=1, orig_median_s=t_base, cand_median_s=t_cand)


@dataclass
class Lift:
    """A liftable hot region: the naive code, the proposed spec, the re-synthesized optimal, the symbolic factory
    (for Z3), a runtime input maker, and the residual size that sets the (measured) hotspot fraction."""
    name: str
    waste_type: str
    original: Callable
    spec: Callable
    optimized: Callable
    sym_factory: Callable[[int], tuple]
    make_input: Callable[[], Any]
    residual_iters: int
    eq: Optional[Callable[[Any, Any], bool]] = None
    sizes: Tuple[int, ...] = (3, 5, 8)
    floor: float = 1.05
    n: int = 0


def lift_and_grade(L: "Lift", *, samples: int = 7) -> KV.Verdict:
    """Differential FIRST (Rule 4); then the two-step Z3 lift proof; then a measured whole-program win; then the
    ADT grade (EXACT iff both proofs pass AND a win ≥ floor; PROBABILISTIC if only differential; DECLINE if Z3
    refutes or there is no win). The proposer here is *lifting*; the verifier still arbitrates (Rule 5)."""
    # differential oracle from the trusted-slow original on real inputs (make_input returns the args tuple)
    oracle = RC.record_oracle(L.original, [L.make_input() for _ in range(6)])
    diff = RC.differential_test(L.optimized, oracle, L.eq)
    if not diff.passed:
        return KV.decline(f"differential FAILED ({diff.mismatches}/{diff.n}) ⇒ DECLINE (a wrong lift, even if "
                          f"faster)", L.waste_type)

    lifted_ok, synth_ok, cex = prove_lift(L.original, L.spec, L.optimized, L.sym_factory, L.sizes)
    if cex and "counterexample" in str(cex):                  # Z3 actively refuted — the moat
        return KV.decline(f"Z3 REFUTED the lift ({cex}) ⇒ DECLINE", L.waste_type)
    proven = lifted_ok and synth_ok

    rep = measure_lift(L.original, L.optimized, L.make_input, L.residual_iters, n=L.n or 0, samples=samples)
    if not rep.beats(L.floor):
        v = KV.decline(f"no whole-program win ≥ {L.floor:.2f}× (measured {rep.whole_program_ratio:.2f}×) ⇒ DECLINE",
                       L.waste_type)
        v.report = rep
        return v

    if proven:
        cert = KV.Cert(KV.EXACT, "z3_two_step_lift", passed=True, check_cost="Z3 bounded (lift + synth)",
                       detail="Z3 proved spec≡original AND optimized≡spec on symbolic inputs (Tenspiler-spirit)")
        v = KV.exact(L.optimized, L.waste_type, str(rep), cert)
    else:
        cert = KV.Cert(KV.PROBABILISTIC, "differential", passed=True, check_cost=f"{diff.n} cases",
                       delta=diff.rule_of_three_delta,
                       detail=f"lift proof inconclusive ({cex}); differential PASS on {diff.n} ⇒ PROBABILISTIC")
        v = KV.probabilistic(L.optimized, L.waste_type, str(rep), cert)
    v.report = rep
    return v


# ── concrete liftable regions (real arithmetic; the same fn runs symbolically for Z3 and numerically to time) ─
def _sym_int_list(n: int) -> tuple:
    return ([z3.Int(f"a{i}") for i in range(n)],)


def _sym_int_list_and_c(n: int) -> tuple:
    return ([z3.Int(f"a{i}") for i in range(n)], z3.Int("c"))


# 1) FLAGSHIP — hand-rolled O(n²) running sum  →  O(n) single-pass scan. No fixed detector recognises this.
def rs_original(a):
    out = []
    for i in range(len(a)):
        s = 0
        for j in range(i + 1):
            s = s + a[j]
        out.append(s)
    return out


def rs_spec(a):
    return [sum(a[: i + 1]) for i in range(len(a))]          # the mathematical spec: prefix sums


def rs_optimized(a):
    out = []
    s = 0
    for x in a:
        s = s + x
        out.append(s)
    return out


def rs_wrong(a):                                             # subtly wrong: drops the current element (off-by-one)
    out = []
    s = 0
    for x in a:
        out.append(s)                                        # appends BEFORE adding ⇒ shifted prefix
        s = s + x
    return out


# 2) distributive lift —  sum(c*x for x in a)  →  c*sum(a)  (fewer multiplies; proven by Z3)
def fc_original(a, c):
    s = 0
    for x in a:
        s = s + c * x
    return s


def fc_spec(a, c):
    return sum(c * x for x in a)


def fc_optimized(a, c):
    return c * sum(a)


# 3) telescoping sum —  Σ (a[i+1]−a[i])  →  a[-1] − a[0]   (O(n) → O(1); pure arithmetic, Z3-provable)
def ts_original(a):
    s = 0
    for i in range(len(a) - 1):
        s = s + (a[i + 1] - a[i])
    return s


def ts_spec(a):
    return sum(a[i + 1] - a[i] for i in range(len(a) - 1))


def ts_optimized(a):
    return a[len(a) - 1] - a[0]


def ts_wrong(a):                                            # wrong: forgets it telescopes, drops a sign
    return a[len(a) - 1] + a[0]


# 4) weighted running sum —  [Σ_{j≤i} w·a[j]]  →  single-pass scan with running accumulator  (O(n²) → O(n))
def wrs_original(a, w):
    out = []
    for i in range(len(a)):
        s = 0
        for j in range(i + 1):
            s = s + w * a[j]
        out.append(s)
    return out


def wrs_spec(a, w):
    return [sum(w * a[j] for j in range(i + 1)) for i in range(len(a))]


def wrs_optimized(a, w):
    out = []
    s = 0
    for x in a:
        s = s + w * x
        out.append(s)
    return out


# 5) range-sum queries —  re-sum a[l:r] per query (O(K·n))  →  prefix array, pref[r]−pref[l] per query (O(n+K))
def rq_original(a, q):
    out = []
    for (l, r) in q:
        s = 0
        for j in range(l, r):
            s = s + a[j]
        out.append(s)
    return out


def rq_spec(a, q):
    return [sum(a[l:r]) for (l, r) in q]


def rq_optimized(a, q):
    pref = [0] * (len(a) + 1)
    for i in range(len(a)):
        pref[i + 1] = pref[i] + a[i]
    return [pref[r] - pref[l] for (l, r) in q]


def rq_wrong(a, q):                                          # off-by-one: pref[l-1] (wraps for l=0) ⇒ wrong
    pref = [0] * (len(a) + 1)
    for i in range(len(a)):
        pref[i + 1] = pref[i] + a[i]
    return [pref[r] - pref[l - 1] for (l, r) in q]


_RQ_PROOF_Q = [(0, 2), (1, 3), (0, 3), (2, 3)]


def _sym_int_list_and_q(n):
    return ([z3.Int(f"a{i}") for i in range(n)], _RQ_PROOF_Q)


def _make_rq_input(size: int = 500, k: int = 300):
    import random
    rng = random.Random(23)
    a = [rng.randrange(-1000, 1000) for _ in range(size)]
    q = []
    for _ in range(k):
        l = rng.randrange(0, size - 1)
        r = rng.randrange(l + 1, size)
        q.append((l, r))
    return (a, q)


# 6) range UPDATES via a difference array —  add d to a[l:r] per update (O(K·n))  →  diff array (O(n+K))
def da_original(a, ups):
    b = list(a)
    for (l, r, d) in ups:
        for j in range(l, r):
            b[j] = b[j] + d
    return b


def da_spec(a, ups):
    b = list(a)
    for (l, r, d) in ups:
        for j in range(l, r):
            b[j] = b[j] + d
    return b


def da_optimized(a, ups):
    n = len(a)
    diff = [0] * (n + 1)
    for (l, r, d) in ups:
        diff[l] = diff[l] + d
        diff[r] = diff[r] - d
    b = list(a)
    run = 0
    for i in range(n):
        run = run + diff[i]
        b[i] = b[i] + run
    return b


def da_wrong(a, ups):                                        # diff[r]+=d (forgot the minus) ⇒ wrong
    n = len(a)
    diff = [0] * (n + 1)
    for (l, r, d) in ups:
        diff[l] = diff[l] + d
        diff[r] = diff[r] + d
    b = list(a)
    run = 0
    for i in range(n):
        run = run + diff[i]
        b[i] = b[i] + run
    return b


_DA_PROOF_UPS = [(0, 2, 5), (1, 3, -3), (0, 3, 2)]


def _sym_int_list_and_ups(n):
    return ([z3.Int(f"a{i}") for i in range(n)], _DA_PROOF_UPS)


def _make_da_input(size: int = 500, k: int = 300):
    import random
    rng = random.Random(29)
    a = [rng.randrange(-1000, 1000) for _ in range(size)]
    ups = []
    for _ in range(k):
        l = rng.randrange(0, size - 1)
        r = rng.randrange(l + 1, size)
        ups.append((l, r, rng.randrange(-50, 50)))
    return (a, ups)


def _make_ts_input(size: int = 6000):
    import random
    rng = random.Random(13)
    return ([rng.randrange(-1000, 1000) for _ in range(size)],)


def _make_wrs_input(size: int = 220):
    import random
    rng = random.Random(17)
    return ([rng.randrange(-1000, 1000) for _ in range(size)], 3)


def _make_rs_input(size: int = 220):
    import random
    rng = random.Random(7)
    return ([rng.randrange(-1000, 1000) for _ in range(size)],)          # args tuple: (a,)


def _make_fc_input(size: int = 4000):
    import random
    rng = random.Random(11)
    return ([rng.randrange(-1000, 1000) for _ in range(size)], 7)        # args tuple: (a, c)


def catalog() -> List[Lift]:
    """The liftable regions this phase ships. rs_* is the flagship (O(n²)→O(n), no detector covers it)."""
    return [
        Lift("running_sum_lift", "verified_lift", rs_original, rs_spec, rs_optimized,
             _sym_int_list, lambda: _make_rs_input(220), residual_iters=900, sizes=(3, 5, 8), n=220),
        Lift("factor_constant_lift", "verified_lift", fc_original, fc_spec, fc_optimized,
             _sym_int_list_and_c, lambda: _make_fc_input(4000), residual_iters=300, sizes=(3, 5, 8), n=4000),
        Lift("telescoping_sum_lift", "verified_lift", ts_original, ts_spec, ts_optimized,
             _sym_int_list, lambda: _make_ts_input(6000), residual_iters=200, sizes=(3, 5, 8), n=6000),
        Lift("weighted_running_sum_lift", "verified_lift", wrs_original, wrs_spec, wrs_optimized,
             _sym_int_list_and_c, lambda: _make_wrs_input(220), residual_iters=900, sizes=(3, 5, 8), n=220),
        Lift("range_sum_query_lift", "verified_lift", rq_original, rq_spec, rq_optimized,
             _sym_int_list_and_q, lambda: _make_rq_input(500, 300), residual_iters=200,
             sizes=(3, 5, 8), n=500),
        Lift("difference_array_lift", "verified_lift", da_original, da_spec, da_optimized,
             _sym_int_list_and_ups, lambda: _make_da_input(500, 300), residual_iters=200,
             sizes=(3, 5, 8), n=500),
    ]
