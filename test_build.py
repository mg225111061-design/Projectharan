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


def test_prompt_caching_request_shape():
    """STAGE 1.1: the live request puts an ephemeral cache breakpoint on the stable system prefix,
    with the volatile per-round prompt after it. (Pure shape check — no key/network needed.)"""
    k = CA._build_kwargs("USER_PROMPT_WITH_COUNTEREXAMPLE", None, "claude-opus-4-8", 4096, True)
    assert isinstance(k["system"], list) and k["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert k["system"][0]["text"] == CA.SYSTEM_PROMPT          # stable prefix is the system prompt
    assert k["messages"][0]["role"] == "user"                  # volatile prompt comes AFTER
    assert k["messages"][0]["content"] == "USER_PROMPT_WITH_COUNTEREXAMPLE"
    assert k["thinking"] == {"type": "adaptive"}               # valid on Opus 4.8 (only on-mode)
    assert "budget_tokens" not in str(k) and "temperature" not in k   # removed params → would 400
    print("PASS test_prompt_caching_request_shape")


def test_spec_conformance_tripwire():
    """The offline tripwire must reject every known 400-causer and accept the real request body."""
    ok = CA._build_kwargs("p", None, "claude-opus-4-8", CA.DEFAULT_MAX_TOKENS, True)
    CA._assert_spec_conformant(ok)                       # the real body is conformant
    assert CA.DEFAULT_MAX_TOKENS <= CA.SAFE_NONSTREAM_MAX_TOKENS  # default stays non-streaming-safe
    base = {"model": "claude-opus-4-8", "max_tokens": 10, "messages": [{"role": "user", "content": "x"}]}
    bad_cases = [
        {**base, "temperature": 0.5},                                  # removed on 4.8 → 400
        {**base, "top_p": 0.9},
        {**base, "top_k": 5},
        {**base, "thinking": {"type": "enabled", "budget_tokens": 1024}},  # removed → 400
        {**base, "thinking": {"type": "adaptive", "budget_tokens": 5}},     # stray budget → 400
        {"model": "m", "max_tokens": 10, "messages": [{"role": "assistant", "content": "prefill"}]},  # prefill → 400
        {**base, "max_tokens": 0},                                     # invalid
        {"model": "m", "max_tokens": 10, "messages": []},              # empty
    ]
    for bad in bad_cases:
        try:
            CA._assert_spec_conformant(bad)
            assert False, f"tripwire MISSED a 400-causer: {bad}"
        except CA.ClaudeError:
            pass
    print(f"PASS test_spec_conformance_tripwire ({len(bad_cases)} 400-causers all rejected)")


def test_provider_config_resolution():
    """Router compat: PROVIDER/HARAN_MODEL/HARAN_BASE_URL resolve correctly; invalid → safe default."""
    import os
    import importlib
    import provider
    keys = ("HARAN_PROVIDER", "PROVIDER", "HARAN_MODEL", "HARAN_BASE_URL", "OPENAI_BASE_URL", "ANTHROPIC_BASE_URL")
    saved = {k: os.environ.get(k) for k in keys}
    try:
        for k in keys:
            os.environ.pop(k, None)
        importlib.reload(provider)
        assert (provider.provider_name(), provider.model(), provider.base_url()) == \
            ("anthropic", "claude-opus-4-8", None)
        os.environ.update({"HARAN_PROVIDER": "openai_compat", "HARAN_MODEL": "qwen/qwen3-coder",
                           "HARAN_BASE_URL": "https://openrouter.ai/api/v1"})
        assert provider.provider_name() == "openai_compat"
        assert provider.model() == "qwen/qwen3-coder"
        assert provider.base_url() == "https://openrouter.ai/api/v1"
        os.environ.update({"HARAN_PROVIDER": "anthropic_compat", "HARAN_BASE_URL": "https://agentrouter.org/v1"})
        assert provider.base_url() == "https://agentrouter.org/v1"
        os.environ["HARAN_PROVIDER"] = "bogus"           # invalid → safe fallback to anthropic
        assert provider.provider_name() == "anthropic"
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        importlib.reload(provider)
    print("PASS test_provider_config_resolution")


def test_openai_request_shape():
    """openai_compat builds an OpenAI /chat/completions body: system+user messages, no Anthropic-only keys."""
    k = CA._build_openai_kwargs("USER_TEXT", None, "qwen/qwen3-coder", 16000, False)
    assert k["model"] == "qwen/qwen3-coder" and k["max_tokens"] == 16000
    assert k["messages"][0]["role"] == "system"
    assert k["messages"][1] == {"role": "user", "content": "USER_TEXT"}
    assert "thinking" not in k and "cache_control" not in str(k)   # Anthropic-only — absent here
    # and the anthropic builder is unchanged (still carries the cache breakpoint + adaptive thinking)
    a = CA._build_kwargs("U", None, "claude-opus-4-8", 16000, True)
    assert a["system"][0]["cache_control"] == {"type": "ephemeral"} and a["thinking"] == {"type": "adaptive"}
    print("PASS test_openai_request_shape")


def test_ct_certifier_proves_and_refutes():
    """v26 S1 (flagship): constant-time certifier — CT_PROVEN for safe code, concrete leak for each
    violation class, 0 false positives, honest IR-level label, and a loop-style fix to convergence."""
    import ct_certifier as CT
    P = "  requires secret(s)\n"
    def st(src, sec=None):
        return CT.certify_ct(src, secrets=sec).status
    # CT-safe → PROVEN (incl. a branch on a PUBLIC value — must NOT be flagged: false-positive guard)
    assert st(f"fn f(s: Int, x: Int) -> Int\n{P}{{ s + x }}") == "CT_PROVEN"
    assert st(f"fn f(s: Int, p: Int) -> Int\n{P}{{ match p {{ 0 => s _ => s }} }}") == "CT_PROVEN"
    assert st("fn f(a: Int) -> Int\n{ a*a + 1 }", {"a"}) == "CT_PROVEN"     # explicit secrets= label
    # each leak class → CT_VIOLATION with the right kind
    def kinds(src):
        v = CT.certify_ct(src)
        return v.status, [l["kind"] for l in v.leaks]
    assert kinds(f"fn f(s: Int) -> Int\n{P}{{ match s {{ 0 => 1 _ => 2 }} }}") == ("CT_VIOLATION", ["branch"])
    assert kinds(f"fn f(s: Int, q: Int) -> Int\n{P}{{ s / q }}") == ("CT_VIOLATION", ["var_time_op"])
    assert kinds(f"fn f(s: Int, q: Int) -> Int\n{P}{{ s % q }}") == ("CT_VIOLATION", ["var_time_op"])
    assert kinds(f"fn f(s: Int, t: Int) -> Int\n{P}{{ get(t, s) }}") == ("CT_VIOLATION", ["mem_index"])
    assert kinds(f"fn f(s: Int) -> Int\n{P}{{ fold k in 1..s {{ k }} }}") == ("CT_VIOLATION", ["secret_loop_bound"])
    # no secret labels → honest NO_SECRETS (not a false PROVEN)
    assert st("fn f(x: Int) -> Int\n{ x + 1 }") == "NO_SECRETS"
    # honest level label present; binary level NOT claimed
    cert = CT.certify_ct(f"fn f(s: Int, x: Int) -> Int\n{P}{{ s + x }}").certificate()
    assert "HARAN-IR" in cert and "binary-level NOT covered" in cert
    # loop connection: a violation yields a concrete fix instruction; the constant-time rewrite verifies
    bad = CT.certify_ct(f"fn f(s: Int) -> Int\n{P}{{ match s {{ 0 => 1 _ => 2 }} }}")
    fb = CT.ct_feedback(bad)
    assert "VIOLATION" in fb and "line" in fb and len(fb) > 40          # precise, not vague
    fixed = CT.certify_ct(f"fn f(s: Int) -> Int\n{P}{{ s + 0 }}")        # constant-time rewrite
    assert fixed.status == "CT_PROVEN"
    print("PASS test_ct_certifier_proves_and_refutes (PROVEN + 4 leak classes + FP=0 + IR-label + loop)")


def test_s9_runtime_engine():
    """v26.2 S9: 3-tier analyzer + differential-equivalence gate + measured associative parallelism."""
    import layout_simd as LS
    import parallel_algebra as PA
    assert LS.analyze(LS.Kernel("k", "reduction", "+")).tier == "A"          # assoc reduction → tier A
    assert LS.analyze(LS.Kernel("k", "io")).tier == "C"                       # IO → physics floor
    assert LS.analyze(LS.Kernel("k", "map", aliasing=True)).safe is False     # aliasing → unsafe
    assert LS.analyze(LS.Kernel("k", "reduction", "+", loop_carried_dep=True)).safe is False
    data = list(range(2000))
    scalar = lambda d: sum(x * x for x in d)
    wrong = lambda d: scalar(d) + 1
    # never a wrong transform: a non-equivalent "fast" path is rejected
    assert LS.measure(LS.Kernel("k", "reduction", "+"), scalar, wrong, data,
                      equiv_samples=[data, [1, 2, 3]]).status == "MISMATCH"
    # SIMD eligible but no native backend here → honest BLOCKED (not a fake speedup)
    assert LS.measure(LS.Kernel("k", "reduction", "+"), scalar, None, data).status == "BLOCKED"
    # the genuinely-measured win: associative parallel reduction (equivalence MUST hold)
    v = PA.parallelize_reduction("square", "+", 1_000_000, cores=4)
    assert v.status in ("OPTIMIZED", "NO_GAIN")        # ran + equivalence held (never MISMATCH/DECLINED)
    if v.status == "OPTIMIZED":
        assert v.speedup >= 1.1 and v.cores == 4 and "reduce(+" in v.workload
    # non-associative op must be DECLINED (parallelizing would change the result)
    assert PA.parallelize_reduction("square", "-", 1000).status == "DECLINED"
    print(f"PASS test_s9_runtime_engine (parallel reduce: {v.status} {v.speedup:.2f}x on {v.cores} cores)")


def test_s8_glm_preset():
    """v26.2 S8: GLM/Z.ai preset (web-confirmed base_url+model), openai_compat shape, UI prefilled."""
    import provider
    prov, base, model, _src = provider.GATEWAY_PRESETS["GLM (Z.ai)"]
    assert prov == "openai_compat" and base == "https://api.z.ai/api/paas/v4/" and model == "glm-4.6"
    # the openai request shape for a GLM model is the chat/completions form (no thinking/cache_control)
    k = CA._build_openai_kwargs("hi", None, "glm-4.6", 16000, False)
    assert k["model"] == "glm-4.6" and k["messages"][0]["role"] == "system" and "thinking" not in k
    # the UI dropdown is prefilled with the verified Z.ai endpoint + model
    html = open("haran.html").read()
    assert 'data-baseurl="https://api.z.ai/api/paas/v4/" data-model="glm-4.6">GLM (Z.ai)' in html
    print("PASS test_s8_glm_preset")


def test_s7_fold_kernels():
    """v26 S7: FOLDED where structure is provable, ABSENT/DECLINED honestly, never a wrong closed form."""
    import fold_kernels as FK
    def stt(src):
        return FK.fold_certificate(src).status
    assert stt("fn f(n: Nat) -> Nat { fold k in 1..n { k } }") == "FOLDED"
    assert stt("fn f(n: Nat) -> Nat { fold k in 1..n { k*k } }") == "FOLDED"
    assert stt("fn f(n: Nat) -> Nat { fold k in 0..n { 2**k } }") == "FOLDED"
    assert stt("fn f(n: Nat) -> Nat { match n { 0 => 0 1 => 1 _ => f(n-1) + f(n-2) } }") == "FOLDED"  # cfinite
    assert stt("fn f(n: Nat) -> Nat { fold k in 1..n { 1 / k } }") == "ABSENT"        # Gosper non-summable
    assert stt("fn f(n: Nat) -> Nat { fold k in 1..n { is_prime(k) } }") == "DECLINED"  # Ω(N) data-dependent
    # the closed form carries the right complexity
    v = FK.fold_certificate("fn f(n: Nat) -> Nat { fold k in 1..n { k } }")
    assert v.complexity == "O(1)" and "n*(n + 1)/2" in v.closed_form and "recheck" in v.certificate
    # ★ never a wrong closed form ★: force the engine to return a wrong form → the recheck must DECLINE
    import closure_classifier as CC
    from haran_parser import parse
    orig = CC.classify_fold
    def wrong(fold):
        verdict = orig(fold); verdict.closed_form = "n*n"; return verdict   # wrong for Σk
    CC.classify_fold = wrong
    try:
        assert FK._numeric_recheck(parse("fn f(n: Nat) -> Nat { fold k in 1..n { k } }").items[0]) == "MISMATCH"
    finally:
        CC.classify_fold = orig
    print("PASS test_s7_fold_kernels")


def test_s6_modelcheck_linearizability():
    """v26 S6: bounded explicit-state model checker + Wing-Gong linearizability checker."""
    import model_check_bridge as MC
    import linearizability as LZ
    ok = MC.check_model([0], lambda s: [(s + 1) % 3], lambda s: s < 3)
    assert ok.status == "MODEL_OK"
    bad = MC.check_model([0], lambda s: ([s + 1] if s < 5 else []), lambda s: s < 3)
    assert bad.status == "MODEL_COUNTEREXAMPLE" and bad.trace[0] == 0 and bad.trace[-1] == 3
    H_lin = [{"id": 0, "call": 0, "ret": 1, "op": "write", "arg": 1, "result": "ok"},
             {"id": 1, "call": 2, "ret": 3, "op": "read", "arg": None, "result": 1}]
    H_bad = [{"id": 0, "call": 0, "ret": 1, "op": "write", "arg": 1, "result": "ok"},
             {"id": 1, "call": 2, "ret": 3, "op": "read", "arg": None, "result": 0}]
    H_conc = [{"id": 0, "call": 0, "ret": 3, "op": "write", "arg": 1, "result": "ok"},
              {"id": 1, "call": 1, "ret": 2, "op": "read", "arg": None, "result": 0}]
    assert LZ.is_linearizable(H_lin, LZ.register_apply, 0).status == "LINEARIZABLE"
    assert LZ.is_linearizable(H_bad, LZ.register_apply, 0).status == "NOT_LINEARIZABLE"
    assert LZ.is_linearizable(H_conc, LZ.register_apply, 0).status == "LINEARIZABLE"   # read may precede write
    print("PASS test_s6_modelcheck_linearizability")


def test_s5_assume_guarantee():
    """v26 S5: modular assume-guarantee + bi-abduction + opaque-boundary runtime contracts."""
    import assume_guarantee as AG
    inc = "fn inc(x: Int) -> Int\n  ensures result = x + 1\n{ x + 1 }"
    use = "fn use_inc(y: Int) -> Int\n  ensures result = y + 1\n{ inc(y) }"
    bad = "fn bad(y: Int) -> Int\n  ensures result = y + 2\n{ inc(y) }"
    cert = AG.verify_system([inc, use, bad])
    byname = {m.name: m for m in cert.modules}
    assert byname["inc"].status == "MODULE_PROVEN"
    assert byname["use_inc"].status == "MODULE_PROVEN"      # proven assuming inc's contract
    assert byname["bad"].status == "MODULE_REFUTED"
    # bi-abduction: caller can't discharge pos's requires b>=1 → it's abduced, then proven
    pos = "fn pos(b: Int) -> Int\n  requires b >= 1\n  ensures result = b\n{ b }"
    call = "fn caller(b: Int) -> Int\n  ensures result = b\n{ pos(b) }"
    c2 = {m.name: m for m in AG.verify_system([pos, call]).modules}
    assert c2["caller"].status == "MODULE_PROVEN" and c2["caller"].abduced_pre == ["pos.requires"]
    # opaque boundary: no contract → cannot prove; runtime-monitored contract → proven + blame in TCB
    netc = "fn netcaller(x: Int) -> Int\n  ensures result >= 0\n{ network(x) }"
    assert AG.verify_system([netc]).modules[0].status == "MODULE_REFUTED"
    mon = AG.verify_system([netc], opaque_contracts={"network": "result >= 0"})
    m0 = mon.modules[0]
    assert m0.status == "MODULE_PROVEN" and "network" in m0.opaque_boundaries
    assert "network" in mon.residual_tcb()["opaque_boundaries"]
    print("PASS test_s5_assume_guarantee")


def test_s4_race_deadlock():
    """v26 S4: lockset data-race + lock-order deadlock on an explicit concurrency model."""
    import race_detector as RD
    assert RD.detect_races({"t1": [("wr", "x")], "t2": [("wr", "x")]}).status == "RACE"
    assert RD.detect_races({"t1": [("acq", "L"), ("wr", "x"), ("rel", "L")],
                            "t2": [("acq", "L"), ("wr", "x"), ("rel", "L")]}).status == "RACE_FREE"
    assert RD.detect_races({"t1": [("acq", "A"), ("wr", "x"), ("rel", "A")],   # disjoint locks → race
                            "t2": [("acq", "B"), ("wr", "x"), ("rel", "B")]}).status == "RACE"
    assert RD.detect_races({"t1": [("rd", "x")], "t2": [("rd", "x")]}).status == "RACE_FREE"   # read-read
    dl = RD.detect_races({"t1": [("acq", "A"), ("acq", "B")], "t2": [("acq", "B"), ("acq", "A")]})
    assert dl.status == "DEADLOCK" and dl.cycles
    v = RD.detect_races({"t1": [("wr", "x")], "t2": [("wr", "x")]})
    assert v.races[0]["var"] == "x" and "DATA RACE" in RD.race_feedback(v)
    print("PASS test_s4_race_deadlock")


def test_s3_incorrectness_ux():
    """v26 S3: UX bug-existence — reachable div/mod-by-zero with a REAL witness; path-sensitive (FP=0)."""
    import incorrectness as IC
    v = IC.check_reachable_bugs("fn d(a: Int, b: Int) -> Int\n{ a / b }")
    assert v.status == "BUG_REACHABLE" and v.bugs[0]["witness"]["b"] == "0"   # witness is a real model
    assert IC.check_reachable_bugs("fn m(a: Int, b: Int) -> Int\n{ a % b }").status == "BUG_REACHABLE"
    # path-sensitive soundness (FP=0): a guarded division is NOT reported
    assert IC.check_reachable_bugs("fn d(a: Int, b: Int) -> Int\n  requires b != 0\n{ a / b }").status == "NO_BUG_FOUND"
    assert IC.check_reachable_bugs("fn d(a: Int, b: Int) -> Int\n{ match b { 0 => 0 _ => a / b } }").status == "NO_BUG_FOUND"
    assert IC.check_reachable_bugs("fn f(a: Int, b: Int) -> Int\n{ a + b }").status == "NO_BUG_FOUND"
    assert "REACHABLE BUG" in IC.bug_feedback(v)
    print("PASS test_s3_incorrectness_ux")


def test_s2_injection_ifds():
    """v26 S2: taint reachability — witness flow for source→sink, FREE when sanitized/no-flow."""
    import taint_ifds as TI
    S = "  requires source(u)\n"
    def st(src):
        return TI.prove_injection_free(src).status
    assert st(f"fn h(u: Int) -> Int\n{S}{{ query(u) }}") == "INJECTION_FLOW"
    assert st(f"fn h(u: Int) -> Int\n{S}{{ let v = u + 1\n  exec(v) }}") == "INJECTION_FLOW"   # taint via let
    assert st(f"fn h(u: Int) -> Int\n{S}{{ query(escape(u)) }}") == "INJECTION_FREE"           # sanitizer barrier
    assert st(f"fn h(u: Int) -> Int\n{S}{{ query(42) }}") == "INJECTION_FREE"                   # no tainted arg
    assert st("fn h(u: Int) -> Int\n{ u + 1 }") == "UNMODELED"                                  # no source/sink
    # witness + feedback are concrete (a real flow, line, source)
    v = TI.prove_injection_free(f"fn h(u: Int) -> Int\n{S}{{ query(u) }}")
    assert v.flows[0]["sink"] == "query" and v.flows[0]["source"] == "u"
    assert "INJECTION at line" in TI.injection_feedback(v)
    print("PASS test_s2_injection_ifds")


def test_s0_runtime_provider_threading():
    """v26 S0: provider/model/baseUrl thread from the request body through route→agentic→claude_generate
    (network-free: no key → mock path, but the kwargs must be accepted end-to-end)."""
    import server
    import agentic as AG
    import intent as IN
    assert server._gen_cfg({"provider": "openai_compat", "model": "qwen/q", "baseUrl": "https://x/v1"}) \
        == ("openai_compat", "qwen/q", "https://x/v1")
    assert server._gen_cfg({}) == (None, None, None)
    # whole chain accepts the new kwargs; no key → labeled mock (cfg accepted without error)
    r = AG.agentic_code("sum 1..n", "normal", None, provider="openai_compat",
                        model="qwen/q", base_url="https://x/v1")
    assert r.source == "mock-sim"
    rr = IN.route("sum 1..n", "normal", None, force=True, provider="openai_compat",
                  model="qwen/q", base_url="https://x/v1")
    assert rr.kind in ("code", "chat", "ask")
    print("PASS test_s0_runtime_provider_threading")


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


def test_incremental_smt_decision_identical():
    """STAGE 1.2: solver reuse returns the SAME verdicts as fresh per-goal solving (incl. a REFUTED)."""
    import z3_adapter as Z
    import incremental_smt as IS
    vt = {"a": "Int", "b": "Int"}
    P = Z.parse_predicate
    shared = [P("a>=0", vt), P("b>=0", vt), P("a<=10", vt), P("b<=10", vt)]
    goals = [P("a+b>=0", vt),   # PROVEN
             P("a*a>=0", vt),   # PROVEN
             P("a>=1", vt),     # REFUTED (a=0 is allowed) — proves it isn't vacuously proving all
             P("a<=100", vt)]   # PROVEN
    inc = IS.prove_batch_incremental(shared, goals, vt)
    fresh = IS.prove_batch_fresh(shared, goals, vt)
    assert inc == fresh, f"incremental disagreed with fresh: {inc} vs {fresh}"
    assert inc[2] == "REFUTED" and inc[0] == inc[1] == inc[3] == "PROVEN", inc
    print(f"PASS test_incremental_smt_decision_identical ({inc})")


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
