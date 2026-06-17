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
