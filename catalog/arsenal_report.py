"""
NATIVE ARSENAL §D report — MEASURED inventory of in-repo native tools vs honest-deferred giants.
================================================================================================
Computed LIVE (never hardcoded): which native cores smoke-pass here, the zero-dependency proof (only z3 + stdlib +
numpy + the grandfathered sympy in source — no fpylll/sage/cypari2/cotengra/flint/julia/cvc5/coq/lean), the A-open
vs B-core DECLINE split on a held-out corpus, and the false-positive=0 audit (the impossible core stays untouched).
"""
from __future__ import annotations

from typing import Dict

import kernel_verdict as KV


def _probe(fn) -> str:
    try:
        v = fn()
        return "NATIVE-LIVE" if v is not None else "ERROR"
    except Exception as e:  # noqa: BLE001
        return f"ERROR:{type(e).__name__}"


def native_tools() -> Dict[str, str]:
    """Smoke-probe each native core (a representative EXACT/DECLINE call); NATIVE-LIVE iff it returns a graded verdict."""
    import catalog.compose as C
    probes = {
        "M6.markov_lump": lambda: C.route({"markov": [["1/2", "1/2"], ["1/2", "1/2"]], "partition": [[0], [1]]}).verdict,
        "M6.multigrid": lambda: C.route({"linsolve": [[4.0, 1.0], [1.0, 3.0]], "b": [1.0, 2.0]}).verdict,
        "M10.erdos_szekeres": lambda: C.route({"sequence": [3, 1, 4, 1, 5, 9, 2, 6]}).verdict,
        "M10.pigeonhole": lambda: C.route({"states": [0, 1, 2, 1]}).verdict,
        "M10.ramsey": lambda: C.route({"ramsey": (lambda u, v: (u + v) % 2), "n": 6}).verdict,
        "lll": lambda: C.route({"lll": [[1, 1], [1, 0]]}).verdict,
        "integer_relation": lambda: C.route({"int_relation": [1.5, 0.5, 1.0]}).verdict,
        "diophantine(Smith)": lambda: C.route({"diophantine": [[2, 3]], "b": [8]}).verdict,
        "sturm_realroots": lambda: C.route({"realroots": [1, -6, 11, -6]}).verdict,
        "berlekamp_massey": lambda: C.route({"recurrence_seq": [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]}).verdict,
        "re_pair": lambda: C.route({"repair": b"abc" * 40}).verdict,
        "knuth_bendix": lambda: C.route({"kb_rules": [("aa", "")], "u": "aaa", "v": "a"}).verdict,
        "model_count(#SAT)": lambda: C.route({"sat_count": [[1, 2]], "nvars": 2}).verdict,
        "unification": lambda: C.route({"unify": [("f", "?x"), ("f", "a")]}).verdict,
        "prng.lcg": lambda: C.route({"lcg": [(1103515245 * x + 12345) % (2 ** 31) for x in range(8)]}).verdict,
        "telescope(Gosper)": lambda: C.route({"telescope": "1/(n*(n+1))"}).verdict,
        "lstar": lambda: C.route({"lstar": (lambda w: w.count("a") % 2 == 0), "alphabet": ("a", "b"), "max_states": 6}).verdict,
        "z3_strings": lambda: C.route({"smt_string": [("eq", "x", "'ab'")]}).verdict,
        "chc_spacer": lambda: __import__("mechanisms").MECHANISMS[13].apply(
            {"chc": True, "varnames": ["x"], "init": lambda s: __import__("z3").And(s["x"] == 0),
             "trans": lambda s, p: p["x"] == s["x"] + 1, "prop": lambda s: s["x"] >= 0}),
    }
    return {name: _probe(fn) for name, fn in probes.items()}


def decline_ab_split(corpus) -> Dict[str, object]:
    """Split each DECLINE in `corpus` into A-open (a structured domain a future tool could move) vs B-core (a proven
    impossibility — secure randomness, the diagonal/halting core, past-Lyapunov prediction, Hilbert's 10th)."""
    import catalog.compose as C
    b_markers = ("incompressible", "kolmogorov", "random", "halt", "rice", "undecidable", "turbulence",
                 "secure", "csprng", "lyapunov", "diophantine", "OBSTRUCTION")
    a_open, b_core = [], []
    for label, x in corpus:
        r = C.route(x)
        if r.grade == KV.DECLINE:
            reason = (r.verdict.reason or "").lower()
            (b_core if any(m in reason for m in b_markers) else a_open).append(label)
    return {"A_open": a_open, "B_core": b_core, "a_count": len(a_open), "b_count": len(b_core)}


def report() -> dict:
    """The §D native-arsenal report — all measured live."""
    import os
    import catalog.capstone_report as CR
    import catalog.compose as C
    from catalog import heavy_bypasses as HB
    import dependency_audit as DA
    tools = native_tools()
    live = sorted(n for n, s in tools.items() if s == "NATIVE-LIVE")
    not_live = sorted(n for n, s in tools.items() if s != "NATIVE-LIVE")
    # false-positive = 0 on the impossible core
    negatives = [os.urandom(800), [__import__("random").gauss(0, 1) for _ in range(200)],
                 "does this program halt on every input?", "x**2 - 1 nonneg sos"]
    fp = sum(1 for neg in negatives if C.route(neg).grade != KV.DECLINE)
    return {
        "mechanisms_run": CR.report()["mechanisms_run"],
        "native_live": live,
        "native_live_count": len(live),
        "not_live": not_live,
        "fallback_defer": HB.status_report()["deferred_here"],
        "forbidden_imports": DA.final_dependency_set()["forbidden_present"],
        "zero_dep_ok": DA.final_dependency_set()["forbidden_present"] == [],
        "false_positive_count": fp,
        "false_positive_zero": fp == 0,
    }
