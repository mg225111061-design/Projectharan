"""
test_build.py — regression + measurement tests for the autonomous accuracy/speed build.
========================================================================================
Every claim in BUILDLOG.md is backed by an assertion here. Run: `python3 test_build.py`.
These tests need NO API key and NO Rust binaries — they exercise the pure-Python/z3/sympy paths.

Honesty: tests assert REAL behavior (no oracle bypass, no hardcoded answers). Where a result is a
measurement (coverage %, counterexample count, cache hit-rate) the test asserts the measured value.
"""
from __future__ import annotations

import claude_agent as CA


# ─────────────────────────────────────────────────────────────────────────────────────────────────
# STAGE 0 — error surfacing (key-safe). The 400 reason must be visible; the key must NEVER appear.
# ─────────────────────────────────────────────────────────────────────────────────────────────────
def test_error_surfacing_shows_cause_hides_key():
    # Simulate an SDK BadRequestError whose message embeds both the real cause AND (worst case) a key.
    class BadRequestError(Exception):
        pass
    e = BadRequestError("Error code: 400 - thinking.budget_tokens unsupported; key=sk-ant-SECRET12345 leaked")
    msg = CA._friendly_error(e)
    assert "thinking.budget_tokens unsupported" in msg, f"cause not surfaced: {msg}"      # diagnosable
    assert "sk-ant-SECRET12345" not in msg, f"KEY LEAKED in error: {msg}"                  # LEVEL-1
    assert "SECRET12345" not in msg, f"KEY fragment leaked: {msg}"
    assert "BadRequestError" in msg
    # auth errors still map to the friendly message (no raw dump)
    auth = CA._friendly_error(Exception("401 invalid x-api-key sk-ant-AAAA"))
    assert "API 키" in auth and "sk-ant-AAAA" not in auth
    print("PASS test_error_surfacing_shows_cause_hides_key")


def test_redact_key_still_holds():
    # belt-and-suspenders: the masking primitive itself
    assert "sk-ant-" not in CA.redact_key("prefix sk-ant-abc123 suffix").replace("sk-***REDACTED***", "")
    assert CA.redact_key("no key here") == "no key here"
    print("PASS test_redact_key_still_holds")


# ─────────────────────────────────────────────────────────────────────────────────────────────────
# STAGE 1.3 — Clover spec consistency gate. Real specs must pass (FP=0); vacuous specs must be caught.
# ─────────────────────────────────────────────────────────────────────────────────────────────────
# (label, haran_src, expect_vacuous)
SPEC_GATE_CORPUS = [
    # REAL specs — must NOT be flagged (false-positive guard)
    ("triangular",      "fn f(n: Int) -> Int\n  ensures result = n*(n+1)/2\n{ n }", False),
    ("square",          "fn f(n: Int) -> Int\n  ensures result = n*n\n{ n }", False),
    ("lower_bound",     "fn f(n: Int) -> Int\n  ensures result > n\n{ n }", False),
    ("linear",          "fn f(n: Int) -> Int\n  ensures result = 2*n + 1\n{ n }", False),
    ("nonneg",          "fn f(n: Int) -> Int\n  ensures result >= n*n - n\n{ n }", False),
    ("opaque_unmodeled","fn f(n: Int) -> Int\n  ensures is_sorted(result)\n{ n }", False),  # → UNMODELED, passes
    # VACUOUS / CONTRADICTORY specs — must be caught
    ("ensures_true",    "fn f(n: Int) -> Bool\n  ensures true\n{ true }", True),
    ("result_eq_self",  "fn f(n: Int) -> Int\n  ensures result = result\n{ n }", True),
    ("ge_self",         "fn f(n: Int) -> Int\n  ensures result >= result\n{ n }", True),
    ("tautology_inputs","fn f(n: Int) -> Int\n  ensures n = n\n{ n }", True),
    ("contradiction",   "fn f(n: Int) -> Int\n  ensures result = result + 1\n{ n }", True),
    ("strict_self",     "fn f(n: Int) -> Int\n  ensures result > result\n{ n }", True),
]


def test_spec_gate_no_false_positives_and_catches_vacuous():
    import spec_gate
    m = spec_gate.measure_gate(SPEC_GATE_CORPUS)
    # the core soundness promise: a REAL spec is NEVER wrongly rejected
    assert m["false_pos"] == 0, f"false positive(s): {[r for r in m['rows']]}"
    # every clearly-vacuous spec in the corpus is caught (the opaque one is intentionally UNMODELED→not vacuous)
    assert m["false_neg"] == 0, f"missed a vacuous spec: {[r for r in m['rows']]}"
    assert m["true_pos"] == 6, f"expected 6 vacuous caught, got {m['true_pos']}"
    print(f"PASS test_spec_gate (caught {m['true_pos']}/6 vacuous, FP={m['false_pos']}, "
          f"unmodeled={m['unmodeled']})")


def test_spec_gate_categories():
    import spec_gate
    from haran_parser import parse
    def kind(src):
        return spec_gate.gate_spec(parse(src).items[0]).kind
    assert kind("fn f(n: Int) -> Bool\n  ensures true\n{ true }") == "VACUOUS_TRUE"
    assert kind("fn f(n: Int) -> Int\n  ensures result = result + 1\n{ n }") == "CONTRADICTORY"
    assert kind("fn f(n: Int) -> Int\n  ensures result = n*(n+1)/2\n{ n }") == "OK"
    print("PASS test_spec_gate_categories")


def test_proof_cache_lossless_and_hits():
    """STAGE 2.1: structural cache reuses verdicts losslessly (incl. α-renamed goals)."""
    import z3_adapter as Z
    import proof_cache as PC
    def g(expr, t):
        return (Z.parse_predicate(expr, t), t, ())
    workload = [
        g("a*a >= 0", {"a": "Int"}),
        g("x*x >= 0", {"x": "Int"}),                 # α-renamed equiv → hit
        g("a + b >= b + a", {"a": "Int", "b": "Int"}),
        g("a*a >= 0", {"a": "Int"}),                 # exact repeat → hit
        g("a*b >= a + b", {"a": "Int", "b": "Int"}),  # distinct (REFUTED)
    ]
    m = PC.measure_cache(workload)
    assert m["lossless_mismatches"] == 0, f"cache returned a wrong verdict: {m}"   # the key promise
    assert m["hits"] >= 2, f"expected reuse, got {m}"
    # spot-check: hit carries the cached verdict + a 'cache' marker; α-rename aliases correctly
    PC.reset()
    a1 = PC.prove_forall_cached(Z.parse_predicate("a*a >= 0", {"a": "Int"}), {"a": "Int"})
    a2 = PC.prove_forall_cached(Z.parse_predicate("z*z >= 0", {"z": "Int"}), {"z": "Int"})
    assert a1.verdict == a2.verdict == "PROVEN" and "cache" in a2.backend
    print(f"PASS test_proof_cache_lossless_and_hits (hits={m['hits']}, mismatches=0)")


def test_cfinite_lossless_and_coverage():
    """STAGE 3.1: C-finite recurrences classify as CLOSED O(log n); companion ≡ naive (lossless)."""
    import cfinite
    from haran_parser import parse
    import closure_classifier as CC
    # exact value spot-checks against known sequences
    assert cfinite.companion_nth([1, 1], [0, 1], 10) == 55                 # fib(10)
    assert cfinite.companion_nth([1, 1], [0, 1], 40) == 102334155          # fib(40)
    assert cfinite.companion_nth([2, 1], [0, 1], 8) == 408                 # pell(8)
    # lossless: companion == naive across many n (including non-trivial ones)
    for n in range(0, 60):
        assert cfinite.companion_nth([1, 1], [0, 1], n) == cfinite.naive_nth([1, 1], [0, 1], n)
    # coverage: a recurrence corpus that was UNKNOWN (Rust binary absent) is now CLOSED
    corpus = {
        "fib":  "fn f(n: Nat) -> Nat { match n { 0 => 0 1 => 1 _ => f(n-1) + f(n-2) } }",
        "pell": "fn p(n: Nat) -> Nat { match n { 0 => 0 1 => 1 _ => 2*p(n-1) + p(n-2) } }",
        "trib": "fn t(n: Nat) -> Nat { match n { 0 => 0 1 => 0 2 => 1 _ => t(n-1)+t(n-2)+t(n-3) } }",
        "lucas":"fn l(n: Nat) -> Nat { match n { 0 => 2 1 => 1 _ => l(n-1) + l(n-2) } }",
    }
    closed = sum(1 for s in corpus.values() if CC.classify_fn(parse(s).items[0]).kind == "CLOSED")
    assert closed == len(corpus), f"only {closed}/{len(corpus)} recurrences CLOSED"
    # the fold path is untouched: a polynomial fold still collapses (sympy/gosper)
    tri = parse("fn t(n: Nat) -> Nat\n  ensures result = n*(n+1)/2\n{ fold k in 1..n { k } }").items[0]
    assert CC.classify_fn(tri).kind == "CLOSED"
    print(f"PASS test_cfinite_lossless_and_coverage ({closed}/{len(corpus)} recurrences CLOSED, lossless)")


def test_counterexample_diversification_sound_and_distinct():
    """STAGE 3.3: multiple DISTINCT counterexamples, each a genuine violation (SOUND)."""
    import z3_adapter as Z
    goal = Z.parse_predicate("a*b >= a+b", {"a": "Int", "b": "Int"})
    verdict, cxs = Z.find_counterexamples(goal, {"a": "Int", "b": "Int"}, k=4)
    assert verdict == "REFUTED"
    assert len(cxs) >= 3, f"expected several CXs, got {len(cxs)}"
    pts = {(c["point"]["a"], c["point"]["b"]) for c in cxs}
    assert len(pts) == len(cxs), "counterexamples must be distinct"
    # SOUND: re-check each in plain Python — every returned point must actually violate the goal
    for c in cxs:
        a, b = int(c["point"]["a"]), int(c["point"]["b"])
        assert not (a * b >= a + b), f"returned a non-counterexample: {c}"
        assert c["violation"] in ("lhs<rhs", "lhs>rhs", "boundary", "—")
    # a TRUE goal yields PROVEN with zero counterexamples
    v2, c2 = Z.find_counterexamples(Z.parse_predicate("n*n >= 0", {"n": "Int"}), {"n": "Int"})
    assert v2 == "PROVEN" and c2 == []
    print(f"PASS test_counterexample_diversification ({len(cxs)} distinct, all sound)")


def test_gate_wired_into_proof_path():
    """The gate must actually change the proof verdict: real spec PROVEN, vacuous spec VACUOUS."""
    import prove_exact as PE
    from haran_parser import parse
    good = parse("fn t(n: Nat) -> Nat\n  ensures result = n*(n+1)/2\n{ fold k in 1..n { k } }").items[0]
    assert PE.prove_correctness(good, {good.name: good}).tier == "PROVEN"
    vac = parse("fn t(n: Nat) -> Nat\n  ensures result = result\n{ fold k in 1..n { k } }").items[0]
    assert PE.prove_correctness(vac, {vac.name: vac}).tier == "VACUOUS"
    # and the agentic mock corpus is unchanged (no regression from the gate)
    import agentic as AG
    m = AG.measure_agentic(mode="extended")
    assert (m.solved, m.proven_forall, m.optimized, m.wrong) == (4, 4, 4, 0), \
        f"agentic corpus regressed: {m}"
    print("PASS test_gate_wired_into_proof_path")


ALL = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    import traceback
    passed = failed = 0
    for t in ALL:
        try:
            t()
            passed += 1
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n==== test_build: {passed} passed, {failed} failed (of {len(ALL)}) ====")
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
