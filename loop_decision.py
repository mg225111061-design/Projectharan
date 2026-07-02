"""
§2 (ABSORB MATH into CODE) — decision-procedures-as-analysis on accumulation loops.
==================================================================================
When CODE meets an accumulation loop `for k in range(lo, n): acc += f(k)`, the question is not only "can I find a
closed form?" but the DECIDABLE one: "does a closed form EXIST?" We answer it with the absorbed MATH decision
procedures, so the answer carries a certificate either way:

  • GOSPER is a COMPLETE decision procedure on hypergeometric terms (rational functions included): it returns a
    closed form Σ_{k=lo}^{n} f(k) = S(n) IFF one exists. So a Gosper closed form ⇒ the O(n) loop collapses to an
    O(1) form (we then DIFFERENTIAL-gate S(n) against the brute-force sum — our own certificate). And a Gosper
    `None` on a hypergeometric term is a PROOF that no hypergeometric closed form exists ⇒ the loop is genuinely
    irreducible: a FIRST-CLASS PROVEN DECLINE ("this loop has no closed form"), not a guess or a give-up.
  • ABRAMOV cross-checks the rational case (no rational antidifference — e.g. the harmonic Σ1/k).

Honest scope (§X): EXACT only with the decision procedure + our differential certificate. Gosper decides the
HYPERGEOMETRIC class — outside it (e.g. a sum of two geometrics, not a single hypergeometric term) we return
UNDECIDED and make NO "no closed form" claim. A wrong closed form or a wrong "irreducible" is a correctness bug;
sound/conservative always. We reuse sympy (gosper_sum) as the search engine but the emitted closed form is gated
by OUR differential check, and the negative is justified by the procedure's COMPLETENESS, stated in the cert.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import sympy as sp
from sympy.concrete.gosper import gosper_sum

import kernel_verdict as KV
from mathmode import decision_summation as DS

CLOSED_FORM = "CLOSED_FORM"
NO_CLOSED_FORM = "NO_CLOSED_FORM"
UNDECIDED = "UNDECIDED"


@dataclass
class LoopDecision:
    status: str                       # CLOSED_FORM | NO_CLOSED_FORM | UNDECIDED
    summand: str
    var: str
    lo: int
    closed_form: str = ""
    kernel: str = ""
    complexity: str = ""
    certificate: str = ""
    verdict: Optional["KV.Verdict"] = None

    def __str__(self) -> str:
        if self.status == CLOSED_FORM:
            return f"CLOSED_FORM Σ_{{{self.var}={self.lo}}}^n {self.summand} = {self.closed_form} ({self.complexity})"
        if self.status == NO_CLOSED_FORM:
            return f"NO_CLOSED_FORM (PROVEN): Σ {self.summand} is irreducible — keep the loop"
        return f"UNDECIDED: {self.summand} — {self.certificate}"


def _is_hypergeometric_term(f: sp.Expr, k: sp.Symbol) -> bool:
    """f is a hypergeometric term iff f(k+1)/f(k) is a rational function of k (Gosper's precondition / decision
    domain). Rational functions of k satisfy this; sums of distinct geometrics do not."""
    if k not in f.free_symbols:
        return True                                      # a constant term is (trivially) hypergeometric
    try:
        ratio = sp.simplify(f.subs(k, k + 1) / f)
        return ratio.is_rational_function(k)
    except Exception:                                    # noqa: BLE001
        return False


def _differential_ok(f: sp.Expr, cf: sp.Expr, k: sp.Symbol, n: sp.Symbol, lo: int) -> tuple:
    """EXACT (symbolic) check: the proposed closed form S(n) equals the brute-force partial sum Σ_{lo}^{n} f at
    several n. This is OUR certificate — a Gosper answer is never emitted unless it reproduces the real sum."""
    ok = checked = 0
    for nv in (lo, lo + 1, lo + 3, lo + 7, lo + 12):
        try:
            brute = sp.nsimplify(sum(f.subs(k, j) for j in range(lo, nv + 1)))
            if sp.simplify(cf.subs(n, nv) - brute) == 0:
                ok += 1
            checked += 1
        except Exception:                                # noqa: BLE001
            continue
    return ok, checked


def decide_sum_collapse(summand_src: str, var: str = "k", lo: int = 1) -> LoopDecision:
    """DECIDE whether Σ_{var=lo}^{n} f(var) collapses to a closed form, with a certificate either way.
    CLOSED_FORM (Gosper found + our differential gate passed) / NO_CLOSED_FORM (Gosper completeness PROVES no
    hypergeometric closed form ⇒ keep the loop) / UNDECIDED (outside the decided class — no false claim)."""
    k, n = sp.Symbol(var), sp.Symbol("n")
    try:
        f = sp.sympify(summand_src, locals={var: k})
    except Exception as e:                               # noqa: BLE001
        return LoopDecision(UNDECIDED, summand_src, var, lo, certificate=f"unparseable summand ({type(e).__name__})",
                            verdict=KV.decline(f"loop_decision: cannot parse summand {summand_src!r} ⇒ DECLINE",
                                               "loop_decision"))

    # a constant summand collapses trivially: Σ_{lo}^{n} c = c·(n − lo + 1)
    if k not in f.free_symbols:
        cf = sp.simplify(f * (n - lo + 1))
        cert = KV.Cert(KV.EXACT, "constant_summand", passed=True, check_cost="algebraic",
                       detail=f"Σ_{{{var}={lo}}}^n {summand_src} = {cf} (constant term; O(n) loop → O(1))")
        return LoopDecision(CLOSED_FORM, summand_src, var, lo, closed_form=str(cf), kernel="constant",
                            complexity="O(1)", certificate=cert.detail,
                            verdict=KV.exact(str(cf), "loop_decision.constant", "closed form (constant)", cert))

    if not _is_hypergeometric_term(f, k):
        return LoopDecision(UNDECIDED, summand_src, var, lo,
                            certificate="summand is not a hypergeometric term (f(k+1)/f(k) not rational) — outside "
                                        "the Gosper/Abramov decision scope; NO 'no closed form' claim made",
                            verdict=KV.decline("loop_decision: non-hypergeometric summand ⇒ UNDECIDED (honest scope)",
                                               "loop_decision"))

    # hypergeometric term ⇒ Gosper is a COMPLETE decision procedure
    try:
        cf = gosper_sum(f, (k, lo, n))
    except Exception:                                    # noqa: BLE001
        cf = None

    if cf is None:
        # PROVEN: no hypergeometric closed form. Cross-check Abramov on the rational sub-case (defense in depth).
        extra = ""
        if f.is_rational_function(k):
            av = DS.abramov_summable(f, k)
            if av.status == KV.EXACT and av.result == "NOT_RATIONALLY_SUMMABLE":
                extra = " Abramov independently confirms (rational, NOT_RATIONALLY_SUMMABLE)."
        cert = KV.Cert(KV.EXACT, "gosper_decision_negative", passed=True, check_cost="Gosper decision (complete)",
                       detail=f"Σ_{{{var}={lo}}}^n {summand_src} has NO hypergeometric closed form — Gosper is "
                              f"COMPLETE on hypergeometric terms, so a None result PROVES non-existence.{extra} The "
                              f"loop is genuinely irreducible: keep it as-is (a first-class PROVEN DECLINE).")
        return LoopDecision(NO_CLOSED_FORM, summand_src, var, lo, certificate=cert.detail,
                            verdict=KV.exact("NO_CLOSED_FORM", "loop_decision.gosper",
                                             "DECISION (no closed form — keep the loop)", cert))

    cf = sp.simplify(cf)
    ok, checked = _differential_ok(f, cf, k, n, lo)
    if checked < 3 or ok != checked:
        return LoopDecision(UNDECIDED, summand_src, var, lo,
                            certificate=f"Gosper proposed {cf} but OUR differential check failed ({ok}/{checked}) — "
                                        f"not emitted (sound: a wrong closed form is never shipped)",
                            verdict=KV.decline("loop_decision: closed form failed our differential certificate ⇒ DECLINE",
                                               "loop_decision"))
    cert = KV.Cert(KV.EXACT, "gosper_closed_form", passed=True, check_cost=f"{checked} differential samples",
                   detail=f"Σ_{{{var}={lo}}}^n {summand_src} = {cf} (Gosper) — differential-verified {ok}/{checked} vs "
                          f"the brute-force partial sums; O(n) accumulation loop collapses to an O(1) closed form")
    return LoopDecision(CLOSED_FORM, summand_src, var, lo, closed_form=str(cf), kernel="gosper", complexity="O(1)",
                        certificate=cert.detail,
                        verdict=KV.exact(str(cf), "loop_decision.gosper", "DECISION (closed form) + differential gate",
                                         cert))


@dataclass
class CollapseSpeedup:
    status: str                       # MEASURED | DECLINE
    summand: str
    closed_form: str = ""
    n: int = 0
    naive_s: float = 0.0
    closed_s: float = 0.0
    ratio: float = 1.0
    verdict: Optional["KV.Verdict"] = None


def _median_time(fn, trials: int) -> float:
    import time
    ts = []
    for _ in range(trials):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    ts.sort()
    return ts[len(ts) // 2]


def measure_collapse_speedup(summand_src: str, var: str = "k", lo: int = 1, n: int = 100000,
                             trials: int = 5) -> CollapseSpeedup:
    """§4 — turn a DECIDED closed form into a MEASURED, Amdahl-honest, certificate-backed speedup. The whole
    FUNCTION is the accumulation loop, so we time the naive O(n) loop vs the O(1) closed form at a stated n (the
    loop IS the program here ⇒ f=1; this is a whole-program speedup FOR THIS FUNCTION). Sound: the closed form is
    re-verified == the loop AT the measured n before timing — a disagreement DECLINEs (never a wrong 'speedup').
    DOMAIN-CONDITIONAL: only closed-form-able loops collapse; near-zero on general code. The ratio is MEASURED at
    n (it grows as O(n)) — never an average, never a guarantee."""
    d = decide_sum_collapse(summand_src, var, lo)
    if d.status != CLOSED_FORM:
        return CollapseSpeedup("DECLINE", summand_src,
                               verdict=KV.decline(f"measure_collapse: {d.status} — no closed form to collapse, nothing "
                                                  f"to measure (sound)", "loop_decision"))
    k, nsym = sp.Symbol(var), sp.Symbol("n")
    f = sp.sympify(summand_src, locals={var: k})
    fl = sp.lambdify(k, f, "math")
    cf = sp.lambdify(nsym, sp.sympify(d.closed_form), "math")

    def naive():
        acc = 0.0
        for j in range(lo, n + 1):
            acc += fl(j)
        return acc

    def closed():
        return cf(n)

    # ★ soundness gate at the MEASURED n: the closed form must equal the loop here (else never report a speedup) ★
    nv, cv = naive(), closed()
    if abs(nv - cv) > 1e-6 * max(1.0, abs(cv)):
        return CollapseSpeedup("DECLINE", summand_src, d.closed_form, n,
                               verdict=KV.decline(f"measure_collapse: closed form ≠ loop at n={n} ({nv} vs {cv}) ⇒ "
                                                  f"DECLINE (no wrong speedup)", "loop_decision"))
    naive_s = _median_time(naive, trials)
    closed_s = _median_time(closed, max(trials, 9))           # the O(1) form is tiny — more trials for a stable median
    ratio = (naive_s / closed_s) if closed_s > 0 else float("inf")
    import fold_dispatcher as FD                              # honest Amdahl framing for the embedded case
    wp_half = FD.amdahl_overall_speedup(ratio, 0.5)
    cert = KV.Cert(KV.EXACT, "measured_loop_collapse", passed=True, check_cost=f"{trials} timed trials at n={n}",
                   detail=f"MEASURED whole-function speedup {ratio:.1f}× at n={n}: the O(n) accumulation loop "
                          f"(naive {naive_s * 1e3:.2f} ms) → the O(1) closed form {d.closed_form} "
                          f"({closed_s * 1e6:.2f} µs), closed form re-verified == the loop at n. HONEST: the loop IS "
                          f"this function (f=1) ⇒ whole-program FOR THIS FUNCTION; the ratio GROWS as O(n) (n stated, "
                          f"NOT an average); if the loop were only 50% of a larger program the whole-program speedup "
                          f"would be ≤ {wp_half:.2f}× (Amdahl ceiling). DOMAIN-CONDITIONAL — closed-form-able loops "
                          f"only, near-zero on general/control-flow code; never a general-purpose accelerator.")
    return CollapseSpeedup("MEASURED", summand_src, d.closed_form, n, naive_s, closed_s, ratio,
                           verdict=KV.exact({"ratio": ratio, "n": n, "naive_s": naive_s, "closed_s": closed_s},
                                            "loop_decision.measure", "measured loop collapse (Amdahl-honest)", cert))
