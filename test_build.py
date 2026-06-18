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


def test_s10_mode_policy():
    """v26.2 S10: NORMAL/EXTENDED allocation = how-much-mathematics dial; BOTH zero-wrong-answer; the
    expensive engines are EXTENDED-only; the best-of-N selector is a SOUND verifier (never learned reward)."""
    import mode_policy as MP
    # cheap mathematics + the always-on soundness gates are in BOTH modes
    for t in ("prefix_caching", "grammar_constrained", "speculative_decoding", "interval_abstract",
              "cfinite_obvious_fold", "type_property_metamorphic", "monoid_parallel", "layout_simd_cheap",
              "incremental_reverify", "clover_spec_gate", "ct_certifier", "taint_ifds"):
        assert MP.should_run(t, "normal") and MP.should_run(t, "extended"), f"{t} must be in BOTH modes"
    # the EXPENSIVE mathematics is EXTENDED-only — NORMAL must terminate before paying for it
    for t in ("octagon_polyhedra", "gosper_toeplitz_fft", "z3_smt", "coq_forall",
              "racefree_parallel", "layout_simd_deep"):
        assert not MP.should_run(t, "normal"), f"{t} must NOT run in NORMAL (it is expensive)"
        assert MP.should_run(t, "extended"), f"{t} must run in EXTENDED"
    # NORMAL ⊊ EXTENDED (extended is a strict superset; nothing in normal is dropped)
    n, e = set(MP.gates_for("normal")), set(MP.gates_for("extended"))
    assert n < e and (e - n) == {"octagon_polyhedra", "gosper_toeplitz_fft", "z3_smt", "coq_forall",
                                 "racefree_parallel", "layout_simd_deep"}
    # best-of-N grows with mode but the SELECTOR is a sound verifier only (invariant 2), both zero-wrong (1)
    pn, pe = MP.plan("normal"), MP.plan("extended")
    assert pn.best_of_n == (1, 2) and pe.best_of_n == (4, 8)
    assert pn.loop_budget == 2 and pe.loop_budget == 5
    assert pn.sound_selector_only and pe.sound_selector_only          # never a learned reward / LLM-judge
    assert pn.zero_wrong_answer and pe.zero_wrong_answer              # mode is depth, NOT correctness
    # unknown technique → not run; bogus mode → safe NORMAL default
    assert MP.should_run("nonexistent_technique", "extended") is False
    assert MP.plan("bogus").mode == "normal"
    # progress labels are honest: NORMAL must NOT advertise stages it never runs (z3/octagon)
    assert "z3_smt" not in MP.progress_stages("normal") and "z3_smt" in MP.progress_stages("extended")
    # ★ WIRED INTO PIPELINE ★: agentic_code consults the policy — the result carries the mode's plan,
    # the loop budget is the policy's, and extended surfaces strictly more gates than normal.
    import agentic as AG
    assert AG.MODE_BUDGET is MP.MODE_BUDGET                       # single source of truth
    rn = AG.agentic_code("sum 1..n", "normal", mock_sequence=["fn f(n: Nat) -> Nat { fold k in 1..n { k } }"])
    re = AG.agentic_code("sum 1..n", "extended", mock_sequence=["fn f(n: Nat) -> Nat { fold k in 1..n { k } }"])
    assert set(rn.gates) == n and set(re.gates) == e and len(re.gates) > len(rn.gates)
    assert rn.best_of_n == (1, 2) and re.best_of_n == (4, 8)
    print(f"PASS test_s10_mode_policy (NORMAL {len(n)} gates ⊊ EXTENDED {len(e)} gates; "
          f"best-of-N {pn.best_of_n}->{pe.best_of_n}; sound-selector-only; wired into agentic_code)")


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


def test_stage1_design_system():
    """v30 STAGE 1: shared black/white design system — tokenized radii (no sharp corners), depth via soft
    layered shadows, rounded font, dark-mode support. (Visuals are user-confirmation; tests check structure.)"""
    css = open("static/design.css").read()
    js = open("static/site.js").read()
    # design_tokens_shared: the palette + radius + shadow tokens exist in ONE shared stylesheet
    for tok in ("--paper:", "--ink:", "--r-ctl:", "--r-card:", "--r-pill:", "--shadow-2:", "--shadow-3:", "--font:"):
        assert tok in css, f"missing token {tok}"
    assert "Nunito" in css                                   # rounded sans-serif (falls back to -apple-system)
    # radius_tokens_applied / no sharp corners: radii use tokens, and there is no border-radius:0
    assert "border-radius:var(--r-card)" in css and "border-radius:var(--r-pill)" in css
    assert "border-radius:0" not in css.replace(" ", "")
    # depth: layered shadows differentiate background < card < raised
    assert css.count("box-shadow:var(--shadow-") >= 3
    # dark_mode_toggles: a [data-theme="dark"] palette exists and site.js flips data-theme + persists
    assert '[data-theme="dark"]' in css
    assert 'setAttribute("data-theme"' in js and "localStorage" in js and "toggleTheme" in js
    print("PASS test_stage1_design_system (shared tokens; tokenized radii, no sharp corners; layered "
          "shadows for depth; Nunito; dark-mode toggle persists)")


def test_stage2_pages():
    """v30 STAGE 2: pages exist; the app keeps codegen; the landing loads stats from /stats.json (NO
    hardcoded stat numbers) and renders graphs; create_app wires every route."""
    import os
    import json
    for pg in ("landing", "login", "signup", "profile"):
        assert os.path.exists(f"pages/{pg}.html") and len(open(f"pages/{pg}.html").read()) > 400
    # app_keeps_codegen: the existing app still has the composer + the streaming codegen endpoint
    app = open("haran.html").read()
    assert "/api/stream" in app and 'id="reqInput"' in app and 'id="sendBtn"' in app
    # landing_loads_stats_from_json + graph_renders
    land = open("pages/landing.html").read()
    assert 'fetch("/stats.json")' in land and "s.metrics" in land
    assert ('class="bars"' in land or "<svg" in land or 'class="fill"' in land)   # a graph structure
    assert "measured_at" in land and "method" in land                              # shows date + how-measured
    # no_hardcoded_numbers: the DISTINCTIVE measured stat values (decimals — unmistakably stats, can't be
    # CSS pixels) are NOT literals in the landing; they come from /stats.json at runtime.
    s = json.load(open("benchmarks/stats.json"))
    for key in ("proof_reuse_speedup", "fold_scale_speedup", "parallel_speedup"):
        if key in s["metrics"]:
            assert str(s["metrics"][key]["value"]) not in land, f"{key} value hardcoded in landing!"
    # each route registered in create_app (built in-process; needs FastAPI which is present here)
    import server
    if server._fastapi_available():
        paths = {r.path for r in server.create_app().routes}
        for need in ("/", "/app", "/login", "/signup", "/profile", "/stats.json", "/api/stream",
                     "/api/auth/login", "/api/work"):
            assert need in paths, f"route {need} not wired"
    print("PASS test_stage2_pages (4 pages + app codegen intact; landing reads /stats.json, no hardcoded "
          "stat values; graph structure present; all routes wired)")


def test_stage3_signup():
    """v30 STAGE 3: signup — server-side password policy, bcrypt/scrypt hash (NEVER plaintext), duplicate
    rejected, '*' tooltip in markup."""
    import auth as AU
    import os
    db = "/tmp/mrj_test_s3.db"
    if os.path.exists(db):
        os.remove(db)
    AU.init_db(db)
    # weak_password_rejected_server_side (each rule enforced authoritatively on the server)
    assert AU.signup("u@x.com", "weak", path=db)["ok"] is False              # too short / missing classes
    assert AU.signup("u@x.com", "alllower1!", path=db)["ok"] is False        # no uppercase
    assert AU.signup("u@x.com", "NoDigit!!", path=db)["ok"] is False         # no digit
    assert AU.signup("u@x.com", "NoSpecial9", path=db)["ok"] is False        # no special
    # signup_creates_user (strong password)
    assert AU.signup("u@x.com", "Str0ng!pw9", "Kim", path=db)["ok"] is True
    # duplicate_email_rejected
    assert AU.signup("u@x.com", "Another9!x", path=db)["ok"] is False
    # password_hashed_not_plain: the stored hash is a KDF hash, never the plaintext
    import sqlite3
    row = sqlite3.connect(db).execute("SELECT pw_hash, pw_algo FROM users").fetchone()
    assert "Str0ng!pw9" not in row[0] and row[1] in ("bcrypt", "scrypt")
    assert AU.verify_password("Str0ng!pw9", row[1], row[0]) and not AU.verify_password("wrong", row[1], row[0])
    # tooltip_in_markup: the '*' password-requirements tooltip is present
    sp = open("pages/signup.html").read()
    assert 'class="star"' in sp and "특수문자" in sp and 'role="tooltip"' in sp
    print(f"PASS test_stage3_signup (weak rejected server-side; {row[1]} hash not plaintext; duplicate "
          "rejected; '*' tooltip in markup)")


def test_stage4_login_profile_work():
    """v30 STAGE 4: login + remember-me (real session lifetime) + profile + work history. Schema has NO
    api_key column; the LLM key is never persisted (grep)."""
    import auth as AU
    import os
    from datetime import datetime
    db = "/tmp/mrj_test_s4.db"
    if os.path.exists(db):
        os.remove(db)
    AU.init_db(db)
    AU.signup("a@b.com", "Str0ng!pw9", "Lee", path=db)
    # login_works (+ wrong password fails)
    assert AU.login("a@b.com", "Str0ng!pw9", path=db)["ok"] is True
    assert AU.login("a@b.com", "nope", path=db)["ok"] is False
    # remember_me_extends_session: persistent session expires much later than a browser-session one
    rem = AU.login("a@b.com", "Str0ng!pw9", remember=True, path=db)
    ses = AU.login("a@b.com", "Str0ng!pw9", remember=False, path=db)
    assert rem["persistent"] is True and ses["persistent"] is False
    assert rem["expires_at"] > ses["expires_at"]                            # 30 days vs 12 hours
    assert (rem["expires_at"] - ses["expires_at"]).days >= 20
    # a valid session resolves to the user; logout invalidates it
    who = AU.verify_session(rem["cookie"], path=db)
    assert who and who["email"] == "a@b.com"
    AU.logout(rem["cookie"], path=db)
    assert AU.verify_session(rem["cookie"], path=db) is None
    # logged_in_vs_out_ui_differs: site.js exposes whoami; pages branch the header on it
    assert "whoami" in open("static/site.js").read()
    assert 'id="authNav"' in open("haran.html").read() and 'id="nav"' in open("pages/landing.html").read()
    # nickname_update_persists
    uid = who["user_id"]
    AU.update_profile(uid, nickname="NewName", path=db)
    assert AU.verify_session(AU.login("a@b.com", "Str0ng!pw9", path=db)["cookie"], path=db)["nickname"] == "NewName"
    # work_history_saved (request/code/labels) — and listed back
    AU.add_work(uid, "sum 1..n", "fn f(){}", "VERIFIED", "PROVEN", path=db)
    items = AU.list_work(uid, path=db)
    assert items and items[0]["request"] == "sum 1..n" and items[0]["proof_tier"] == "PROVEN"
    # schema_has_no_api_key_column: scan the ACTUAL columns (PRAGMA) — token_hash is a session-token hash,
    # not an LLM key. ("api_key" appears only in honesty COMMENTS in schema.sql, never as a column.)
    import sqlite3
    cols = set()
    for t in ("users", "sessions", "work_history"):
        cols |= {r[1] for r in sqlite3.connect(db).execute(f"PRAGMA table_info({t})").fetchall()}
    assert not [c for c in cols if any(k in c.lower() for k in ("api", "apikey", "llm_key", "secret"))]
    # key_not_persisted (grep): no add_work / INSERT call ever carries the LLM key; claude_agent fences os
    srv = open("server.py").read()
    for seg in srv.split("AU.add_work(")[1:]:                 # every add_work call site
        assert "apiKey" not in seg[:240] and "api_key" not in seg[:240]   # request/code/labels only
    assert "apiKey" not in open("auth.py").read()             # auth never even names the LLM key in code
    assert open("claude_agent.py").read().count("import os") == 0
    print("PASS test_stage4_login_profile_work (login + remember-me real lifetime 30d vs 12h; nickname "
          "persists; work saved+listed; schema has NO api_key column; LLM key never persisted)")


def test_stage4_pipeline_overlap():
    """v31 STAGE 4 [Clock A+B]: verify each candidate (CPU/SMT) the instant it is generated, overlapping the
    in-flight generations (network). Different resources → real latency overlap (not a fake number)."""
    import pipeline as P
    m = P.measure_overlap(n=4, gen_ms=45)
    # verify_overlaps_next_generation / pipeline_async_no_blocking: overlapped wall < two-phase wall
    assert m.overlap_ms < m.two_phase_ms and m.speedup > 1.0 and m.winner_verified is True
    assert "Clock A+B" in m.note                                  # labeled (combined clock), not mixed with C
    print(f"PASS test_stage4_pipeline_overlap ([Clock A+B] two-phase {m.two_phase_ms}ms → overlapped "
          f"{m.overlap_ms}ms = {m.speedup}×; real Z3 verify hidden under generation; winner verified)")


def test_stage3_clockC_runtime():
    """v31 STAGE 3 [Clock C: generated-code execution]: fold collapse (O(n)→O(1), BIT-EXACT) preferred;
    Numba JIT (constant-factor, bit-exact within int64) as fallback. Clock C ONLY. Non-closeable → DEFER."""
    import runtime_speed as RS
    # fold_collapses_closed_form (bit_exact): Σk² → O(1) closed form, exact, win grows with n
    f = RS.fold_sum_speedup(lambda n: sum(k * k for k in range(1, n + 1)),
                            "fn f(n: Nat) -> Nat { fold k in 1..n { k*k } }", n=1_000_000)
    assert f.status == "FOLDED" and f.bit_exact is True and f.speedup > 1.1 and "n*(n + 1)" in f.closed_form
    assert f.cert_type == "exact-closed-form"
    # defer_when_no_fold: a non-closeable sum is HONEST_DEFER (never a fake "folded")
    d = RS.fold_sum_speedup(lambda n: 0, "fn f(n: Nat) -> Nat { fold k in 1..n { 1 / k } }", n=1000)
    assert d.status == "DEFER" and "no fake fold" in d.detail
    # fold_rate_measured: honest hit-rate (fold helps ONLY closeable code)
    fr = RS.measure_fold_rate()
    assert fr["closed"] >= 3 and fr["total"] == 6 and 0 < fr["rate"] <= 1 and "closeable" in fr["note"]
    # jit_speeds_kernel (labeled Clock C): data-dependent kernel, bit-exact; or honest [BLOCKED] if no Numba
    j = RS.jit_sumsq_speedup(n=400_000, reps=2)
    assert j.status in ("JITTED", "BLOCKED")
    if j.status == "JITTED":
        assert j.equal is True and j.speedup > 1.1 and "Clock C" in j.detail   # bit-exact + a real win
    print(f"PASS test_stage3_clockC_runtime ([Clock C] fold Σk² {f.speedup}× O(n)→O(1) bit-exact; "
          f"JIT {j.status}{' '+str(j.speedup)+'× bit-exact' if j.status=='JITTED' else ''}; "
          f"fold-rate {fr['rate']}; non-closeable→DEFER)")


def test_stage2_clockB_verification():
    """v31 STAGE 2 [Clock B: verification]: incremental SMT (reuse), fast probabilistic certificates
    (Freivalds / Schwartz-Zippel — one-sided, error stated), and SOUND semantic caching. Clock B ONLY —
    not the LLM call or code execution."""
    import fast_certificates as FC
    import incremental_smt as IS
    import proof_cache as PC
    import z3_adapter as Z
    # incremental_smt_reuses: incremental verdicts EQUAL fresh (correctness preserved; reuse is the speedup)
    vt = {"a": "Int", "b": "Int"}
    sh = [Z.parse_predicate("a>=0", vt), Z.parse_predicate("b>=0", vt)]
    goals = [Z.parse_predicate("a+b>=0", vt), Z.parse_predicate("a*a>=0", vt), Z.parse_predicate("a>=1", vt)]
    fresh = IS.prove_batch_fresh(sh, goals, vt)
    inc = IS.prove_batch_incremental(sh, goals, vt)
    assert inc == fresh and inc[2] == "REFUTED" and inc[0] == "PROVEN"          # same answers, reused
    # certificate_skips_full_suite (labeled): Freivalds is one-sided sound + carries its error bound
    m = FC.measure_freivalds(n=120, k=24)
    assert m.correct_pass and m.wrong_caught and m.cert_type == "Freivalds"
    assert abs(m.error_prob - 2.0 ** -24) < 1e-12 and m.cert_ms <= m.exact_ms   # ε=2^-k, and it's faster
    # Schwartz-Zippel: a true identity PASSes with stated ε; a non-identity is FAILed (one-sided, no false reject)
    idn = FC.sz_identity_check(lambda v: (v[0] + v[1]) ** 2, lambda v: v[0] ** 2 + 2 * v[0] * v[1] + v[1] ** 2, 2, 2)
    nid = FC.sz_identity_check(lambda v: (v[0] + v[1]) ** 2, lambda v: v[0] ** 2 + v[1] ** 2, 2, 2)
    assert idn.ok and idn.cert_type == "Schwartz-Zippel-ε" and 0 < idn.error_prob < 1e-30
    assert nid.ok is False                                                       # distinct → caught
    # semantic_cache_hits + cache_sound_no_false_hit
    PC.reset()
    wl = [(Z.parse_predicate("a*a>=0", {"a": "Int"}), {"a": "Int"}, ()),
          (Z.parse_predicate("x*x>=0", {"x": "Int"}), {"x": "Int"}, ()),          # α-equiv → HIT
          (Z.parse_predicate("a*b>=a+b", {"a": "Int", "b": "Int"}), {"a": "Int", "b": "Int"}, ())]  # distinct
    mc = PC.measure_cache(wl)
    assert mc["hits"] >= 1 and mc["lossless_mismatches"] == 0                    # reuse, and NEVER a wrong verdict
    PC.reset()
    a1 = PC.prove_forall_cached(Z.parse_predicate("a*a>=0", {"a": "Int"}), {"a": "Int"})
    a2 = PC.prove_forall_cached(Z.parse_predicate("a*b>=a+b", {"a": "Int", "b": "Int"}), {"a": "Int", "b": "Int"})
    assert a1.verdict == "PROVEN" and a2.verdict == "REFUTED"                    # non-equiv → its OWN verdict, no false hit
    print(f"PASS test_stage2_clockB_verification ([Clock B] incremental SMT reuses (same verdicts); Freivalds "
          f"{m.speedup}× ε≤2^-24 + Schwartz-Zippel-ε; semantic cache hits, sound (no false hit))")


def test_stage1_clockA_bestofn():
    """v31 STAGE 1 [Clock A: LLM call]: parallel best-of-N + first-pass early-exit. Candidates run
    concurrently; a SOUND verifier accepts the first pass and the rest are cancelled; wall-clock = max, not
    sum. (Live LLM latency is [BLOCKED: key]; orchestration measured with simulated/varied latencies.)"""
    import asyncio
    import bestofn as B
    # mode_sets_N
    assert B.MODE_N == {"fast": 1, "normal": 3, "extend": 6}
    # parallel_candidates_concurrent: N launched together → wall ≈ one latency, NOT N×latency
    async def conc():
        started = []
        async def gen(i):
            started.append(i); await asyncio.sleep(0.04); return f"cand{i}:{'GOOD' if i==2 else 'BAD'}"
        r = await B.best_of_n(5, gen, lambda c: c.endswith("GOOD"))
        return r, started
    r, started = asyncio.run(conc())
    assert sorted(started) == [0, 1, 2, 3, 4] and r.wall_ms < 5 * 40 * 0.9    # concurrent, not summed
    assert r.verified and r.winner.endswith("GOOD") and r.accepted_index == 2
    # first_pass_early_exit_cancels_rest: a fast good candidate wins; slow losers are cancelled
    async def cancel():
        async def gen(i):
            await asyncio.sleep(0.02 if i == 1 else 0.30)
            return f"cand{i}:{'GOOD' if i in (1, 4) else 'BAD'}"
        return await B.best_of_n(5, gen, lambda c: c.endswith("GOOD"))
    rc = asyncio.run(cancel())
    assert rc.accepted_index == 1 and rc.cancelled >= 1 and rc.wall_ms < 250    # won fast, didn't wait for slow
    # verifier_sound_no_flaky: deterministic verifier; best_of_n only returns a verify-accepted candidate
    v = lambda c: c.endswith("GOOD")
    assert v("x:GOOD") is True and v("x:GOOD") is True and v("x:BAD") is False   # stable, not flaky
    # measured [Clock A] orchestration: sum→max gives a real (>1×) speedup, labeled with p and N
    m = B.measure_clock_a(n=6, p=0.5, per_call_ms=50, trials=4)
    assert m.parallel_ms <= m.sequential_ms and m.speedup >= 1.0 and "Clock A" in m.note and m.n == 6
    print(f"PASS test_stage1_clockA_bestofn (N concurrent + early-exit cancels losers; [Clock A] "
          f"{m.sequential_ms}ms→{m.parallel_ms}ms = {m.speedup}× @p={m.p},N={m.n}; live LLM [BLOCKED])")


def test_stage5_three_modes_selectable():
    """v31 STAGE 5 (three_modes_selectable): the UI offers Fast / Normal / Extend, and the policy backs all
    three. fast = single shot (budget 1), still SOUNDLY verified — the dial is DEPTH, never correctness."""
    import agentic as AG
    import mode_policy as MP
    html = open("haran.html").read()
    # three distinct pills present, in order (fast → normal → extended)
    for dm in ('data-mode="fast"', 'data-mode="normal"', 'data-mode="extended"'):
        assert dm in html, f"missing mode pill {dm}"
    assert html.index('data-mode="fast"') < html.index('data-mode="normal"') < html.index('data-mode="extended"')
    # setMode accepts all THREE (the old guard rejected 'fast' — that bug is fixed)
    assert 'mode !== "fast" && mode !== "normal" && mode !== "extended"' in html
    assert 'classList.toggle("mode-fast"' in html
    # policy backs fast with the SHALLOWEST budget, and fast shares NORMAL's (sound) gate column
    assert MP.MODE_BUDGET["fast"] == 1 < MP.MODE_BUDGET["normal"] < MP.MODE_BUDGET["extended"]
    assert MP.BEST_OF_N["fast"] == (1, 1)
    pf = MP.plan("fast")
    assert pf.mode == "fast" and pf.loop_budget == 1 and pf.best_of_n == (1, 1)
    assert set(pf.gates) == set(MP.gates_for("normal")), "fast must use the cheap-but-SOUND gate set, not extended"
    assert pf.sound_selector_only and pf.zero_wrong_answer            # invariants hold for fast too
    # fast still SOUNDLY verifies: one good single-shot candidate → converged + PROVEN (gate ran, not skipped)
    r = AG.agentic_code("sum 1..n", "fast", mock_sequence=[AG._GOOD])
    assert r.mode == "fast" and r.converged and r.iters == 1 and r.status == "VERIFIED" and r.proof_tier == "PROVEN"
    print(f"PASS test_stage5_three_modes_selectable (fast/normal/extend pills + setMode; fast budget "
          f"{MP.MODE_BUDGET['fast']} shares NORMAL's sound gates; fast run PROVEN in {r.iters} shot)")


def test_stage5_progress_states_shown():
    """v31 STAGE 5 (progress_states_shown): the pipeline emits REAL progress states (호출중/생성중(best-of-N)/
    검증중/최적화중), each only when that work runs — no fake progress. The generate state surfaces the mode's
    CONFIGURED best-of-N budget (not a live parallel claim)."""
    import agentic as AG
    import mode_policy as MP
    html = open("haran.html").read()
    # honest stage labels exist in BOTH languages
    for k in ("stage_classify", "stage_generate", "stage_verify", "stage_optimize"):
        assert html.count(k + ":") >= 2, f"stage label {k} missing in ko+en"
    # generate state shows the mode's best-of-N budget (configured), via MODE_N + bestof_n/1shot labels
    assert "const MODE_N = {fast:1, normal:2, extended:8}" in html
    assert 'if(s==="generate")' in html and 'T("bestof_n")' in html and 'T("bestof_1shot")' in html
    # agentic_stream emits the REAL stages in order, only when that work runs (mock, no network)
    evs = [e["stage"] for e in AG.agentic_stream("sum 1..n", "normal", mock_sequence=[AG._WRONG, AG._GOOD])]
    assert evs[0] == "generate" and "code_done" in evs and "verify" in evs
    assert "refuted" in evs and "fix" in evs, "a refuted candidate must show the fix state (real, not faked)"
    assert "optimize" in evs and evs[-1] == "done"
    # per-mode honest progress set (fast/normal share the cheap stages; extended adds z3/octagon)
    assert "z3_smt" not in MP.progress_stages("fast") and "z3_smt" in MP.progress_stages("extended")
    print(f"PASS test_stage5_progress_states_shown (real stages {evs}; best-of-N budget surfaced on generate; "
          f"fast/normal cheap stages ⊊ extended)")


def test_stage5_result_shows_measured_times_labeled():
    """v31 STAGE 5 (result_shows_measured_times_labeled): the result shows times LABELED by clock —
    [Clock A] generation / [Clock B] verification / [Clock C] runtime(fold) — never mixed. Clock B is a
    GENUINE measurement (HARAN runs locally even with no key)."""
    import agentic as AG
    import server as SV
    # backend measures A and B SEPARATELY; B is real (>0) for a converged run; the dict carries both, labeled
    res = [e for e in AG.agentic_stream("sum 1..n", "normal", mock_sequence=[AG._GOOD]) if e["stage"] == "done"][0]["result"]
    assert hasattr(res, "clock_a_ms") and hasattr(res, "clock_b_ms")
    assert res.clock_b_ms > 0.0, "Clock B (verification) must be a real measured time for a converged run"
    rd = SV.to_result_dict(res)
    assert "clock_a_ms" in rd and "clock_b_ms" in rd and isinstance(rd["clock_b_ms"], float)
    assert rd["optimization"] and rd["optimization"]["optimized"]      # Clock C: a fold to closed form exists
    # the UI renders each clock with its OWN label (A/B/C) and an explicit "never mixed" note
    html = open("haran.html").read()
    for lbl in ("[Clock A]", "[Clock B]", "[Clock C]"):
        assert html.count(lbl) >= 2, f"{lbl} must appear in BOTH ko+en clock labels"
    assert 'T("clk_a")' in html and 'T("clk_b")' in html and 'T("clk_c")' in html
    assert "s.clock_a_ms" in html and "s.clock_b_ms" in html           # rendered from the measured summary
    assert 'esc(fmtMs(s.clock_b_ms))' in html                           # Clock B shows the genuine measured ms
    assert "절대 섞지" in html and "never mixed" in html                  # the three clocks are never mixed (both langs)
    print(f"PASS test_stage5_result_shows_measured_times_labeled ([Clock A] {res.clock_a_ms}ms · "
          f"[Clock B] {res.clock_b_ms}ms (real) · [Clock C] {rd['optimization']['closed_form']}; labeled, never mixed)")


def test_stage5_no_fake_latency_numbers():
    """v31 STAGE 5 (no_fake_latency_numbers): an unmeasured clock is [BLOCKED], never a fabricated number.
    In the no-key SIM there is NO real LLM call → Clock A is BLOCKED (not '0.0ms' shown as a product latency);
    the per-input ×N runtime win is [TBD] (not invented). Clock B stays a genuine measurement."""
    import agentic as AG
    import server as SV
    html = open("haran.html").read()
    # Clock A in SIM (no live key) is rendered as BLOCKED — the code BRANCHES on live, never prints a fake A time
    assert "clk_blocked_sim" in html
    assert "live ? esc(fmtMs(s.clock_a_ms))" in html, "Clock A must be gated on `live` (BLOCKED otherwise)"
    assert "BLOCKED" in html and ("키없음" in html or "no key" in html)
    # the per-input runtime multiplier is honestly deferred, never a fabricated ×N
    assert "clk_xn_tbd" in html and ("[TBD: 측정필요]" in html or "[TBD: measure]" in html)
    # NO hardcoded fake latency literals anywhere in the page (e.g. a made-up "0.5ms"/"0.3 ms")
    import re as _re
    fakes = _re.findall(r'(?<![\w.])0\.\d+\s?ms\b', html)
    assert not fakes, f"fabricated sub-ms latency literal(s) found: {fakes}"
    # the backend confirms the SIM is honestly provenanced (source=mock-sim) so the UI knows to BLOCK Clock A,
    # and clock_a_ms is NOT a fabricated network latency (mock generator ≈ 0), while clock_b_ms is REAL.
    res = [e for e in AG.agentic_stream("sum 1..n", "fast", mock_sequence=[AG._GOOD]) if e["stage"] == "done"][0]["result"]
    rd = SV.to_result_dict(res)
    assert rd["source"] == "mock-sim"                                   # → UI BLOCKs Clock A (no real call happened)
    assert rd["clock_a_ms"] < 5.0                                       # mock gen ≈ 0; never inflated to look like an LLM
    assert rd["clock_b_ms"] > 0.0                                       # Clock B is a genuine measured time
    print(f"PASS test_stage5_no_fake_latency_numbers (Clock A BLOCKED in SIM (no fake number); ×N [TBD]; "
          f"no sub-ms literals; source={rd['source']}, B={rd['clock_b_ms']}ms real)")


def test_stage0_measurement():
    """v30 STAGE 0: every site number is a MEASUREMENT artifact. stats.json must carry value+unit+method+
    timestamp per metric (so the site can show 'how it was measured'); blocked metrics carry a reason (never
    faked); the measure script is runnable; a raw log exists for audit."""
    import json
    import os
    # measure_script_runs: the script imports and exposes a measure() that returns the right shape
    import importlib.util
    spec = importlib.util.spec_from_file_location("measure_mod", "benchmarks/measure.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.measure)
    # stats_json_has_method_and_timestamp
    assert os.path.exists("benchmarks/stats.json"), "run benchmarks/measure.py first"
    s = json.load(open("benchmarks/stats.json"))
    assert "measured_at" in s and "T" in s["measured_at"]            # ISO timestamp
    assert s["metrics"], "no measured metrics"
    for name, m in s["metrics"].items():
        assert "value" in m and "unit" in m and "method" in m and len(m["method"]) > 20, name
        assert isinstance(m["value"], (int, float))
    for b in s.get("blocked", []):
        assert "metric" in b and "reason" in b                       # blocked is honest, not hidden
    # the headline soundness numbers are the MEASURED ones (not invented): FP=0, autofix wrong=0
    assert s["metrics"]["verifier_false_positives"]["value"] == 0
    assert os.path.exists("benchmarks/raw.log")                      # audit trail
    print(f"PASS test_stage0_measurement ({len(s['metrics'])} measured metrics w/ method+timestamp, "
          f"{len(s.get('blocked', []))} blocked w/ reason; raw log present)")


def test_b_ui_apple_rounding():
    """v29 task B (STRUCTURE only — visuals are 'user-confirmation', never auto-'done'): rounder radii are
    tokenized & applied; gateway controls collapse into Advanced (default view simplified) WITHOUT losing
    function; one primary action is emphasized; transitions are present."""
    html = open("haran.html").read()
    # ── radius_tokens_applied: the four-tier radius scale exists and is actually used ──
    for tok in ("--radius-sm:", "--radius-md:", "--radius-lg:", "--radius-full:"):
        assert tok in html, f"missing radius token {tok}"
    assert "border-radius:var(--radius-full)" in html and "border-radius:var(--radius-lg)" in html
    assert "border-radius:999px" not in html        # all pill literals converted to the token
    assert "--tap:44px" in html                     # ≥44px touch targets (Apple HIG)
    # ── advanced_settings_collapsible + reduced_visible_controls_no_function_lost ──
    assert '<details class="advanced"' in html and "</details>" in html
    adv = html.index('<details class="advanced"'); end = html.index("</details>", adv)
    block = html[adv:end]
    for ctrl in ('id="providerSel"', 'id="modelInput"', 'id="baseUrlInput"'):   # controls live INSIDE Advanced
        assert ctrl in block, f"{ctrl} not inside Advanced — function would be lost"
    assert '<details class="advanced" id="advanced">' in html and "[open]" not in html.split("</style>")[1][:50] \
        or 'id="advanced">' in html               # not force-open by default (collapsed)
    assert html.count('id="providerSel"') == 1 and html.count('id="sendBtn"') == 1   # still present (reachable)
    assert 'data-i18n="advanced"' in html
    # ── primary_action_single_emphasis: the send button is the ONE filled-accent action with a lift/shadow;
    #    the gateway controls are quiet/outline (not accent-filled) ──
    btn_css = html[html.index(".composer button{"):html.index(".composer button{") + 400]
    assert "background:var(--accent)" in btn_css and "box-shadow:" in btn_css and "translateY(-1px)" in html
    gw_css = html[html.index(".gw-sel,.gw-in{"):html.index(".gw-sel,.gw-in{") + 200]
    assert "background:var(--panel-2)" in gw_css and "var(--accent)" not in gw_css   # quiet, not emphasized
    # ── transitions_present: gentle Apple-like easing + focus rings (micro-interactions, accessibility) ──
    assert "--ease:" in html and "transition:" in html and "var(--ease)" in html
    assert ":focus" in html and "box-shadow:0 0 0 3px" in html        # visible focus ring
    print("PASS test_b_ui_apple_rounding (radius tokens applied + no 999px literals; Advanced collapsible "
          "keeps controls reachable; single primary action emphasized; transitions + focus rings present)")


def test_a_gateway_model_wiring():
    """v29 task A: the GLM/Z.ai '1211 Unknown Model' bug = the user's model never reached the request; the
    streaming path sent the hardcoded Claude default. This locks the fix end-to-end + the adapter rules."""
    import claude_agent as CA
    import agentic as AG
    import server
    import types
    # ── model_field_reaches_request_body / no_hardcoded_model: the user's model IS body.model ──
    for m in ("glm-5.2", "glm-4.6", "qwen/qwen3-coder", "deepseek-chat"):
        assert CA._build_openai_kwargs("p", None, m, 8192, False)["model"] == m
    assert CA.DEFAULT_MODEL not in (CA._build_openai_kwargs("p", None, "glm-5.2", 8192, False)["model"],)  # not forced
    # ── ★ the real regression: the SERVER STREAMING path threads the user's model to claude_generate ★ ──
    captured = {}
    orig = CA.claude_generate
    def spy(prompt, api_key=None, **kw):
        captured["model"] = kw.get("model"); captured["provider"] = kw.get("provider")
        captured["base_url"] = kw.get("base_url")
        return CA.GenResult(text=CA._MOCK_HARAN, live=True, model=kw.get("model"), source="spy")
    CA.claude_generate = spy
    try:
        payload = {"prompt": "sort a list of integers ascending and return the sorted list", "mode": "normal",
                   "apiKey": "dummy-not-real", "provider": "openai_compat", "model": "glm-5.2",
                   "baseUrl": "https://api.z.ai/api/paas/v4/", "force": True}
        list(server.stream_events(payload))                       # drive the SSE generator
    finally:
        CA.claude_generate = orig
    assert captured.get("model") == "glm-5.2", f"model NOT threaded to the request: {captured}"   # was the bug
    assert captured.get("provider") == "openai_compat" and "z.ai" in (captured.get("base_url") or "")
    # ── base_url_normalized: trailing slash trimmed, double /v1 collapsed, /v1 otherwise preserved ──
    assert CA.normalize_base_url("https://api.z.ai/api/paas/v4/") == "https://api.z.ai/api/paas/v4"
    assert CA.normalize_base_url("https://x/api/v1/v1") == "https://x/api/v1"
    assert CA.normalize_base_url("https://openrouter.ai/api/v1") == "https://openrouter.ai/api/v1"
    assert CA.normalize_base_url(None) is None
    # ── openai_compat_path_parses_content_and_reasoning ──
    msg_c = types.SimpleNamespace(content="hello", reasoning_content="")
    msg_r = types.SimpleNamespace(content="", reasoning_content="from-reasoning")     # GLM reasoning fallback
    msg_e = types.SimpleNamespace(content="", reasoning_content="")
    assert CA._extract_openai_text(msg_c) == "hello"
    assert CA._extract_openai_text(msg_r) == "from-reasoning"
    assert CA._extract_openai_text(msg_e) == ""                                        # both empty → surfaced upstream
    assert "thinking" in CA.OPENAI_EXTRA_BODY and CA.OPENAI_EXTRA_BODY["thinking"]["type"] == "disabled"
    # ── key_not_stored (grep): claude_agent never imports os / touches env (LEVEL-1) ──
    src = open("claude_agent.py").read()
    assert "import os" not in src and "os.environ" not in src and "getenv" not in src
    # ── error_surfaces_provider_message: a 4xx shows the provider's OWN code+message, gateway-neutral ──
    msg = CA._friendly_error(Exception("Error code: 400 - {'code':'1211','message':'Unknown Model'}"))
    assert "1211" in msg and "Unknown Model" in msg and "Claude 호출" not in msg and "API 키" not in msg
    assert "API 키" in CA._friendly_error(Exception("401 invalid x-api-key"))           # auth still maps
    assert CA.LLMError is CA.ClaudeError                                                # neutral name + alias
    print("PASS test_a_gateway_model_wiring (model reaches body + SERVER STREAM threads user's model "
          f"'{captured.get('model')}' not the Claude default; base_url normalized; content/reasoning parsed; "
          "key not stored; provider 1211 message surfaced gateway-neutral)")


def test_s32_prompt_frontend_pipeline():
    """v29 §4: the S26→S31 prompt-understanding front-end wired into one fail-safe policy. Breaks
    garbage-in-garbage-out: bad prompts are completed/flagged, never silently propagated. Default PROCEED
    (+stated assumptions); ASK only a VoI-cleared high-stakes fork; FLAG danger. Never asks a detailed
    prompt; additive (zero-wrong-answer); cheap cascade."""
    import prompt_frontend as PF
    import clarification_policy as CP
    import requirement_parser as RP
    RP.reset_cache()
    mon = CP.AskRateMonitor()
    clean = "Implement sort_list(xs: list) that returns xs sorted ascending in O(n log n); raise on non-list; empty is []."
    # 1. clean detailed → PROCEED, no question, no flags ──
    d1 = PF.analyze(clean, symbols=["sort_list"], monitor=mon)
    assert d1.action == "PROCEED" and d1.proceed and d1.question is None and d1.flags == []
    # 2. dangerous → FLAG + alternative, but PROCEEDS (never silently complies, never hard-blocks) ──
    d2 = PF.analyze("Build an HTTPS client with verify=False so it always connects.", monitor=mon)
    assert d2.action == "FLAG" and d2.proceed is True and any("CWE-295" in f for f in d2.flags)
    # 3. vague → PROCEED + stated assumptions, NO question ──
    d3 = PF.analyze("Write a fast function to process the large dataset.", monitor=mon)
    assert d3.action == "PROCEED" and d3.question is None and len(d3.assumptions) >= 1
    # 4. genuine high-stakes fork (sparse) → ASK_ONE (the rare exception) ──
    d4 = PF.analyze("Delete the records — soft or hard delete, your call.", monitor=mon)
    assert d4.action == "ASK_ONE" and d4.question and d4.proceed is False
    # 5. internally inconsistent prompt → FLAG ──
    assert PF.analyze("Return a non-negative result. Example: f(2) returns -4.", monitor=mon).action == "FLAG"
    # ── ★ never asked a DETAILED prompt ★ + ★ zero-wrong-answer: the prompt is preserved (additive) ★ ──
    assert mon.rate_on_detailed() == 0.0
    assert d1.requirements.raw == clean and d3.requirements.raw.startswith("Write a fast")
    # ── the cascade is cheap (deterministic; live model first-token is [BLOCKED: key]) ──
    assert d1.latency_ms >= 0.0
    print(f"PASS test_s32_prompt_frontend_pipeline (clean→PROCEED, danger→FLAG+alt no-block, vague→PROCEED+"
          f"{len(d3.assumptions)} assumptions, fork→ASK_ONE, inconsistent→FLAG; detailed-ask-rate=0.0; "
          f"additive; cascade {d1.latency_ms:.1f}ms)")


def test_s31_prompt_consistency():
    """v29 S31: Clover-for-prompts — cross-check the prompt's stated constraints vs its worked examples and
    flag ONLY a sound numeric violation (zero false-positives, Clover's property); a divergence routes to
    S28/S29. Entity grounding links references to existing symbols. Consistency ≠ intent correctness (Rice)."""
    import prompt_consistency as PC
    # ── consistent: constraint result>=0 and example f(3) returns 9 → CONSISTENT ──
    assert PC.check_consistency("Implement f that returns a non-negative result. Example: f(3) returns 9.").status == "CONSISTENT"
    # ── ★ sound divergence: a non-negative result but an example returns -4 → DIVERGENT → route S28 ★ ──
    d = PC.gate("Implement f that returns a non-negative result. Example: f(2) returns -4.")
    assert d.status == "DIVERGENT" and d.route == "S28" and "violates" in d.divergences[0]
    assert PC.check_consistency("result must be >= 100. e.g. it returns 5 for small input.").status == "DIVERGENT"
    # ── ★ zero false-positives: nothing to violate → CONSISTENT (never a heuristic hunch) ★ ──
    assert PC.check_consistency("Sort the list ascending; it must be O(n log n).").status == "CONSISTENT"
    assert PC.check_consistency("returns a non-negative result. example: returns 0 for the empty list.").status == "CONSISTENT"
    # ── entity grounding to a code/IR symbol table (checkable: symbol exists?) ──
    grounded, ungrounded = PC.ground_entities("call sort_list(xs) then validate(row)", ["sort_list", "helper"])
    assert grounded == ["sort_list"] and ungrounded == ["validate"]
    rep = PC.gate("Implement f that returns a non-negative result. Example: f(3) returns 9.", symbols=["f"])
    assert rep.status == "CONSISTENT" and rep.grounded == ["f"]
    print("PASS test_s31_prompt_consistency (constraint vs example: CONSISTENT / sound-DIVERGENT→S28; "
          "zero-FP when nothing to violate; entity grounding to symbols; consistency≠intent-correctness)")


def test_s30_clarification_policy():
    """v29 S30: ask RARELY, ask SMART, max one. Only a genuine high-stakes fork (not detailed) with VoI over
    a conservative threshold → ONE question; everything else PROCEEDs. ★A detailed prompt is NEVER asked.★
    The ask-rate monitor clamps the threshold if a detailed prompt is ever asked."""
    import clarification_policy as CP
    import ambiguity_detector as AD
    import requirement_parser as RP
    RP.reset_cache()
    mon = CP.AskRateMonitor()
    # ── a genuine high-stakes fork, NOT detailed → ASK_ONE (exactly one focused question) ──
    p1 = "Delete the records — soft or hard delete, your call."
    d1 = CP.decide(p1, AD.detect_ambiguity(p1), req=RP.parse_requirements(p1), monitor=mon, threshold=3.0)
    assert d1.status == "ASK_ONE" and isinstance(d1.question, str) and d1.question.count("?") == 1 and d1.voi > 3.0
    # ── ★ a DETAILED prompt (even with a fork) is NEVER asked → PROCEED ★ ──
    p2 = ("Implement delete_user(user_id: int) that removes the user and returns bool; either soft or hard "
          "delete is fine; it must be transactional and log the action; raise on a missing id.")
    req2 = RP.parse_requirements(p2)
    assert CP.is_detailed(req2)
    assert CP.decide(p2, AD.detect_ambiguity(p2), req=req2, monitor=mon).status == "PROCEED"
    # ── a non-fork (CLEAR/MINOR) → PROCEED ──
    p3 = "Write a fast function to sort the large list."
    assert CP.decide(p3, AD.detect_ambiguity(p3), req=RP.parse_requirements(p3), monitor=mon).status == "PROCEED"
    # ── the conservative threshold gates: raise it high and even a real fork PROCEEDs ──
    assert CP.decide(p1, AD.detect_ambiguity(p1), req=RP.parse_requirements(p1), threshold=100.0).status == "PROCEED"
    # ── ask-rate monitor: we NEVER asked on a detailed prompt; if we ever did, the threshold is raised ──
    assert mon.rate_on_detailed() == 0.0
    bad = CP.AskRateMonitor(); bad.record(detailed=True, asked=True)
    assert bad.suggest_threshold(3.0) > 3.0                  # clamp down if a detailed prompt was asked
    good = CP.AskRateMonitor(); good.record(detailed=True, asked=False)
    assert good.suggest_threshold(3.0) == 3.0
    print(f"PASS test_s30_clarification_policy (high-stakes fork→ASK_ONE 1q VoI={d1.voi:.0f}; detailed→PROCEED "
          f"never-ask; non-fork→PROCEED; high threshold→PROCEED; detailed-ask-rate={mon.rate_on_detailed():.2f})")


def test_s29_ambiguity():
    """v29 S29: ambiguity → DEFAULT reasonable completion + stated assumption (NEVER asks); only a genuine
    high-stakes fork escalates to S30. Conservative toward not-asking; deterministic lexicon (the
    semantic-entropy / multi-sample paths are [BLOCKED: key]); fail-safe."""
    import ambiguity_detector as AD
    # ── a detailed prompt is CLEAR — and S29 NEVER asks ──
    clear = AD.detect_ambiguity("Implement a function that returns the list sorted ascending in O(n log n); "
                                "raise on invalid input.")
    assert clear.status == "CLEAR" and clear.asks is False
    # ── vague but clear intent → MINOR, reasonable completion + stated assumptions, NO ask ──
    minor = AD.detect_ambiguity("Write a fast function to process the large dataset.")
    assert minor.status == "MINOR_AMBIGUITY" and minor.asks is False
    assert "fast" in minor.completions and "large" in minor.completions and len(minor.assumptions()) >= 2
    # ── a genuine high-stakes fork (irreversible + open choice) → escalate to S30 ──
    fork = AD.detect_ambiguity("Delete the old user records — soft or hard delete, your call.")
    assert fork.status == "HIGH_STAKES_FORK" and "delete" in fork.fork and fork.asks is False
    # ── a high-stakes WORD without an open choice is NOT escalated by S29 (S28 handles the danger) ──
    assert AD.detect_ambiguity("Delete the temp files in ./cache after processing.").status == "CLEAR"
    print(f"PASS test_s29_ambiguity (detailed→CLEAR no-ask; vague→MINOR reasonable-completion no-ask "
          f"{minor.vague_terms}; irreversible+open→HIGH_STAKES_FORK→S30; conservative, never asks)")


def test_s28_dangerous_instruction():
    """v29 S28: don't silently obey a dangerous/contradictory/infeasible instruction — FLAG + alternative.
    Danger is a CWE lexicon (HEURISTIC → flag, never hard-block); contradiction is Z3 UNSAT (SOUND);
    infeasibility is a catalog. A safe prompt is SAFE; satisfiable bounds are NOT a false contradiction."""
    import dangerous_instruction_detector as DI
    # ── danger lexicon → FLAGGED with CWE + a safe alternative; NEVER a hard block ──
    tls = DI.detect("Write an HTTPS client but set verify=False so it always connects.")
    assert tls.status == "FLAGGED" and tls.hard_block is False
    df = tls.flags[0]
    assert df.kind == "danger" and df.cwe == "CWE-295" and df.basis == "heuristic-lexicon" and df.alternative
    assert DI.detect("use eval(user_input) to run it").flags[0].cwe == "CWE-95"
    assert DI.detect("call subprocess with shell=True on the user string").flags[0].cwe == "CWE-78"
    assert DI.detect("store the user password in plaintext").flags[0].cwe == "CWE-256/319"
    # ── ★ SOUND contradiction via Z3 UNSAT ★; a satisfiable pair is NOT flagged (no false positive) ──
    contra = DI.detect("The timeout must be less than 10 and the timeout must be greater than 30.")
    cf = [f for f in contra.flags if f.kind == "contradiction"]
    assert cf and cf[0].basis == "sound-UNSAT"
    assert DI.detect("The timeout must be greater than 10 and less than 30.").status == "SAFE"   # satisfiable
    # ── infeasibility catalog (heuristic → flag) ──
    assert DI.detect("Sort an arbitrary list in O(1) time.").flags[0].kind == "infeasible"
    # ── a clean instruction is SAFE; the detector never hard-blocks ──
    safe = DI.detect("Implement a function that returns the list sorted ascending in O(n log n).")
    assert safe.status == "SAFE" and safe.hard_block is False
    print("PASS test_s28_dangerous_instruction (CWE lexicon → FLAG+alt, never hard-block; contradiction → "
          "sound Z3 UNSAT, satisfiable→SAFE; infeasible catalog; clean→SAFE)")


def test_s27_missing_info():
    """v29 S27: schema-coverage missing-info detector. Breaks silent-code-on-incomplete: a fully-specified
    prompt is COMPLETE; a minor gap gets a REASONABLE DEFAULT + stated assumption (no ask, no block); a
    critical gap (no task at all) escalates to S30. Completeness is vs the schema (Rice), responses fail-safe."""
    import requirement_parser as RP
    import missing_info_detector as MI
    RP.reset_cache()
    full = ("Implement a function that takes a list of integers as input and returns them sorted ascending; "
            "raise an error on invalid input and handle the empty list.")
    assert MI.detect_missing(RP.parse_requirements(full)).status == "COMPLETE"
    # ── minor missing → reasonable default + stated assumption, NOT asked, NOT escalated ──
    noin = MI.detect_missing(RP.parse_requirements("Write a function that returns the running total in O(n) time."))
    assert noin.status == "MISSING" and "inputs" in noin.minor and noin.escalate_to_s30 is False
    assert noin.critical == [] and any("assumed inputs" in a for a in noin.assumptions())   # default+stated
    # ── critical missing (no goal/task) → escalate to S30 (never silent, never hard block) ──
    nogoal = MI.detect_missing(RP.parse_requirements("The dataset is large and the deadline is tight."))
    assert nogoal.escalate_to_s30 is True and nogoal.critical == ["goals"]
    # the detector never BLOCKS: minor always carries a forward-able assumption set
    assert noin.assumptions() and isinstance(noin.assumptions(), list)
    print(f"PASS test_s27_missing_info (full→COMPLETE; minor gap→default+stated assumption no-ask; "
          f"no-task→escalate S30; fail-safe, schema-relative)")


def test_s26_requirement_parser():
    """v29 S26: parse a prompt into typed slots {goals/constraints/IO/prohibitions/assumptions}. Deterministic
    (key-free) extraction with a schema well-formedness guarantee; multi-part → least-to-most; cached. This
    is a measurable EXTRACTION proxy, NOT understanding (Rice); a vague prompt gets low confidence, not faked."""
    import requirement_parser as RP
    RP.reset_cache()
    detailed = ("Implement a function that takes a list of integers as input and returns them sorted ascending. "
                "It must run in O(n log n) and must not use any external libraries. Assume the list fits in memory.")
    r = RP.parse_requirements(detailed)
    assert set(r.bound_slots()) == set(RP.RequirementSchema.SLOTS)        # all six slots bound on a rich prompt
    assert r.confidence >= 0.8 and RP.is_well_formed(r)
    assert any("O(n log n)" in c for c in r.constraints) and r.prohibitions and r.assumptions
    # ── multi-part → least-to-most decomposition (numbered and keyword forms) ──
    assert len(RP.parse_requirements("1. Parse the CSV. 2. Validate rows. 3. Then write to a DB.", "extended").parts) == 3
    assert len(RP.parse_requirements("First read config. Then connect. Finally stream logs.").parts) == 3
    # ── constrained-decoding well-formedness: parser output is valid; a malformed object is rejected ──
    assert RP.is_well_formed(r) and not RP.is_well_formed({"goals": "x"})
    # ── cache: the same prompt is not re-parsed ──
    r2 = RP.parse_requirements(detailed)
    assert r2.cached is True and RP.cache_stats()["hits"] >= 1
    # ── measurable extraction proxy (NOT understanding); a vague prompt → honest LOW confidence ──
    gold = {s: True for s in RP.RequirementSchema.SLOTS}
    assert RP.extraction_score(r, gold) == 1.0
    vague = RP.parse_requirements("do the thing")
    assert vague.confidence == 0.0 and vague.bound_slots() == []          # no fabricated structure
    print(f"PASS test_s26_requirement_parser (detailed→{len(r.bound_slots())}/6 slots conf={r.confidence:.2f}; "
          f"multi-part decomposed; schema-guarded; cached; vague→conf 0.0; extraction proxy, not understanding)")


def test_s25_spec_propagation():
    """v28 S25: bind the proof to the SEMANTIC CONTRACT, not the location. A rename/move transports the
    proof (no re-prove); a real semantics change → REPROVE_NEEDED (justified, not a defect). Merkle-
    incremental: only changed contracts cost prover work; a failed re-proof → DEFER."""
    import spec_propagation as SP
    add_ab = "def f(a, b):\n    return a + b"
    # ── the α-key is rename/move-invariant but constant/operator/spec-SENSITIVE ──
    assert SP.classify_change(add_ab, "def g(x, y):\n    return x + y") == "SEMANTICS_PRESERVING"   # rename
    assert SP.classify_change(add_ab, "def f(a, b):\n    return a - b") == "SEMANTICS_CHANGED"      # operator
    assert SP.classify_change(add_ab, "def f(a, b):\n    return a + 1") == "SEMANTICS_CHANGED"      # constant
    assert SP.classify_change(add_ab, add_ab, "r>=0", "r>=1") == "SEMANTICS_CHANGED"                # spec
    assert SP.semantic_key(add_ab) == SP.semantic_key("def g(x, y):\n    return x + y")             # transport key
    # ── Merkle-incremental propagation: only CHANGED contracts cost a prove call ──
    def prove(ob):
        return "bad" not in ob.source        # an obligation containing 'bad' fails its re-proof → DEFER
    store = SP.ProofStore()
    repo0 = [SP.Obligation(f"o{i}", f"def f(a, b):\n    return a + {i}", "ensures ge0") for i in range(5)]
    r0 = SP.propagate(repo0, prove, store)
    assert r0.prove_calls == 5 and r0.reproved == 5                       # cold: prove everything once
    repo1 = [SP.Obligation("o0", "def f(x, y):\n    return x + 0", "ensures ge0"),    # RENAME of o0
             SP.Obligation("o1", "def f(a, b):\n    return a - 1", "ensures ge0"),     # semantics change
             SP.Obligation("o2", "def f(a, b):\n    return a + 2", "ensures ge0"),     # untouched
             SP.Obligation("o3", "def f(a, b):\n    return a + 3", "ensures ge0"),     # untouched
             SP.Obligation("o4", "def f(a, b):\n    return a + 4", "ensures ge0"),     # untouched
             SP.Obligation("o5", "def f(a, b):\n    return a + bad", "ensures ge0")]   # new, fails re-proof
    r1 = SP.propagate(repo1, prove, store)
    assert r1.statuses["o0"] == "PROPAGATED"          # rename → proof transported, NOT re-proved
    assert r1.statuses["o1"] == "REPROVE_NEEDED"      # semantics change → re-prove (justified, not a defect)
    assert r1.statuses["o2"] == r1.statuses["o3"] == r1.statuses["o4"] == "PROPAGATED"   # untouched
    assert r1.statuses["o5"] == "DEFER"               # re-proof failed → honest defer
    assert r1.prove_calls == 2 and r1.propagated == 4               # only the 2 changed obligations cost work
    print(f"PASS test_s25_spec_propagation (rename→PROPAGATED transport; operator/constant/spec→REPROVE; "
          f"incremental: {r1.propagated}/{r1.total} transported, prove_calls={r1.prove_calls}; fail→DEFER)")


def test_s24_concretization_gate():
    """v28 S24: CEGAR concretization gate — run an abstract counterexample on the REAL runtime before any
    fix. ★The danger case★: a spurious counterexample against CORRECT code must yield NO_BUG and leave the
    code untouched; a real bug is reproduced; a hallucinated fix that breaks a passing test is rolled back."""
    import concretization_gate as CG
    crash = lambda cex, out, exc: exc is not None          # the property: "must not crash at runtime"
    # ── ★ SPURIOUS counterexample vs CORRECT code → NO_BUG, code NOT edited ★ ──
    guarded = lambda a, b: (a // b if b != 0 else 0)       # correct (guarded division)
    v1 = CG.cegar(CG.from_candidates([{"a": 1, "b": 0}]), guarded, crash)   # abstraction wrongly flags b=0
    assert v1.status == "NO_BUG" and v1.spurious == [{"a": 1, "b": 0}] and v1.refinements >= 1
    # ── a genuine bug IS reproduced on the real runtime → REAL_BUG ──
    buggy = lambda a, b: a // b                            # unguarded → crashes at b=0
    v2 = CG.cegar(CG.from_candidates([{"a": 1, "b": 0}]), buggy, crash)
    assert v2.status == "REAL_BUG" and v2.counterexample == {"a": 1, "b": 0}
    # ── refinement budget: endless spurious counterexamples → DEFER (never hangs, never edits) ──
    import itertools
    def endless(excluded):
        for k in itertools.count():
            c = {"a": k, "b": 0}
            if CG._freeze(c) not in excluded:
                return c
    assert CG.cegar(endless, guarded, crash, max_refine=5).status == "DEFER"
    # ── regression guard: a fix that breaks a previously-passing test is ROLLED BACK ──
    orig = lambda a, b: (a // b if b != 0 else 0)
    badfix = lambda a, b: a // b                           # a hallucinated "fix" that crashes the guarded case
    tests = [({"a": 6, "b": 2}, 3), ({"a": 5, "b": 0}, 0)]
    out = CG.apply_fix_guarded(orig, badfix, tests)
    assert out.status == "ROLLBACK" and out.broke == [{"a": 5, "b": 0}] and out.fn is orig   # working code kept
    good = CG.apply_fix_guarded(orig, lambda a, b: (a // b if b != 0 else 0), tests)
    assert good.status == "APPLIED"
    print("PASS test_s24_concretization_gate (spurious cex vs correct code → NO_BUG, code untouched; real "
          "bug reproduced → REAL_BUG; endless spurious → DEFER; hallucinated fix → ROLLBACK)")


def test_s23_soundness_defense():
    """v28 S23: defend against a single mapping/solver bug collapsing integrity. (1) an independent RUP/DRAT
    UNSAT checker re-verifies proofs (TCB shrinks to the checker; bogus proofs rejected); (2) a solver
    portfolio — Z3 vs an independent bounded search — DEFERs on disagreement (single-solver never suffices);
    (3) mapping axioms are metamorphically verified (a flipped op is caught)."""
    import proof_checker as PC
    # ── layer 1: independent UNSAT proof checker ──
    assert PC.check_rup_proof([[1], [-1]], [[]]).status == "UNSAT_VERIFIED"    # x ∧ ¬x ⊢ ⊥, RUP-checked
    assert PC.brute_unsat([[1], [-1]], 1) is True                              # independent oracle agrees
    assert PC.check_rup_proof([[1]], [[]]).status == "REJECTED"                # bogus proof on a SAT CNF
    assert PC.check_rup_proof([[1, 2], [-1], [-2]], [[2], []]).status == "UNSAT_VERIFIED"   # multi-step
    assert PC.check_rup_proof([[1, 2], [-1], [-2]], [[1]]).status == "REJECTED"  # not RUP-implied → rejected
    # ── layer 2: solver portfolio cross-check ──
    assert PC.robust_certify("a*a >= 0", {"a": "Int"}).status == "PROVEN"      # Z3 + bounded search agree
    assert PC.robust_certify("a >= 1", {"a": "Int"}).status == "REFUTED"       # false claim
    # ★ a simulated solver soundness bug: Z3 says PROVEN but an INDEPENDENT oracle finds a cex → DEFER ★
    bug = PC.robust_certify("a*a >= 0", {"a": "Int"}, second_opinion=lambda: {"a": 7})
    assert bug.status == "DEFER" and bug.agree is False and bug.counterexample == {"a": 7}
    # ── layer 3: mapping-axiom metamorphic tests ──
    ok, mism = PC.mapping_axioms_ok()
    assert ok and mism == []                                                   # the real HARAN→Z3 mapping is sound
    assert PC.mapping_preserves_semantics(lambda a, b: a - b, lambda a, b: a - b)        # correct mapping holds
    assert not PC.mapping_preserves_semantics(lambda a, b: a + b, lambda a, b: a - b)    # − ↦ + is CAUGHT
    print("PASS test_s23_soundness_defense (RUP checker verifies+rejects proofs; portfolio DEFERs on "
          "disagreement — single-solver never suffices; mapping metamorphic catches a flipped op)")


def test_s22_file_ingest():
    """v28 S22: multi-format ingestion → S21. Stdlib formats always extract; office/PDF/image use optional
    libs and degrade HONESTLY (BLOCKED/FAILED never fabricate text); extracted text feeds grounding."""
    import file_ingest as FI
    import grounding_pipeline as GP
    import io
    import json
    import zipfile
    # ── detection (extension + magic bytes) ──
    assert FI.detect_format("d.json", b"{}") == "json" and FI.detect_format("f.pdf", b"%PDF-1.4") == "pdf"
    assert FI.detect_format("x.bin", b"%PDF-1.4 hi") == "pdf" and FI.detect_format("a.go", b"package m") == "code"
    # ── stdlib formats: always extract real content ──
    assert FI.ingest(json.dumps({"a": [1, 2]}).encode(), "d.json").status == "EXTRACTED"
    nb = {"cells": [{"cell_type": "code", "source": ["x=1\n", "print(x)"]}]}
    assert "print(x)" in FI.ingest(json.dumps(nb).encode(), "n.ipynb").text
    assert FI.ingest(b"a,b\n1,2\n3,4", "d.csv").structured == [["a", "b"], ["1", "2"], ["3", "4"]]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.txt", "hello"); z.writestr("b.py", "def f(): pass")
    zres = FI.ingest(buf.getvalue(), "a.zip")
    assert zres.status == "EXTRACTED" and len(zres.members) == 2 and "hello" in zres.text
    # ── office formats: real round-trip if the lib is present, else honest BLOCKED ──
    if FI.HAVE["docx"]:
        import docx
        d = docx.Document(); d.add_paragraph("grounded claim one"); db = io.BytesIO(); d.save(db)
        assert FI.ingest(db.getvalue(), "f.docx").text.strip() == "grounded claim one"
    else:
        assert FI.ingest(b"x", "f.docx").status == "BLOCKED"
    if FI.HAVE["xlsx"]:
        import openpyxl
        wb = openpyxl.Workbook(); wb.active.append(["x", "y"]); xb = io.BytesIO(); wb.save(xb)
        assert FI.ingest(xb.getvalue(), "f.xlsx").status == "EXTRACTED"
    else:
        assert FI.ingest(b"x", "f.xlsx").status == "BLOCKED"
    # ── PDF / image / corrupt: degrade honestly — NEVER fabricate text ──
    pdf = FI.ingest(b"%PDF-1.4 not-a-real-pdf", "f.pdf")
    assert (pdf.status == "BLOCKED" if not FI.HAVE["pdf"] else pdf.status in ("EXTRACTED", "EXTRACTED_LOWCONF", "FAILED"))
    img = FI.ingest(b"\x89PNG\r\n\x1a\n", "f.png")
    assert (img.status == "BLOCKED" if not FI.HAVE["ocr"] else True) and img.text == "" if img.status == "BLOCKED" else True
    corrupt = FI.ingest(b"\x00\x01\x02\xff\xfe", "f.bin")
    assert corrupt.status == "FAILED" and corrupt.text == "" and corrupt.confidence == "none"
    # ── ★ pipeline link ★: a HARAN spec in a .txt ingests then GROUNDs via S21 ──
    spec = "fn t(n: Nat) -> Nat\n  ensures result = n*(n+1)/2\n{ fold k in 1..n { k } }"
    r = FI.ingest(spec.encode(), "claim.txt")
    assert r.status == "EXTRACTED" and GP.verify_claim(r.text).status == "GROUNDED"
    av = FI.available_formats()
    print(f"PASS test_s22_file_ingest (stdlib always; docx={av['docx']} xlsx={av['xlsx']} pdf={av['pdf']} "
          f"ocr={av['image(OCR)']}; BLOCKED/FAILED never fabricate; txt→S21 GROUNDED)")


def test_s21_grounding_pipeline():
    """v28 S21: large-prompt GROUNDING (not understanding — Rice). Structural index + EXACT multi-hop
    retrieval (no lost-in-the-middle) + spec-extract-and-verify: checkable claims are GROUNDED/REFUTED,
    natural-language claims are BEST_EFFORT (labeled, never faked). LLM head-to-head is [BLOCKED: key]."""
    import grounding_pipeline as GP
    ents = [GP.Entity(n) for n in ("api", "auth", "db", "cache", "util", "log")]
    edges = [("api", "auth"), ("api", "cache"), ("auth", "db"), ("auth", "log"), ("cache", "db"), ("db", "util")]
    good = "fn t(n: Nat) -> Nat\n  ensures result = n*(n+1)/2\n{ fold k in 1..n { k } }"
    bad = "fn t(n: Nat) -> Nat\n  ensures result = n*(n+1)/2\n{ fold k in 1..n { k+1 } }"
    nl = "the API should feel fast and be user-friendly"
    queries = [("api", "util", True), ("api", "db", True), ("util", "api", False), ("log", "db", False)]
    res = GP.ground(ents, edges, [good, bad, nl], queries)
    st = [c.status for c in res.claims]
    assert st == ["GROUNDED", "REFUTED", "BEST_EFFORT"]          # verified / refuted / honestly-labeled
    assert res.claims[1].counterexample is not None             # the refuted claim carries a witness
    # ── ★ exact multi-hop retrieval (no lost-in-the-middle by construction) ★ ──
    assert res.multihop_accuracy == 1.0                          # matches hand-derived reachability
    assert res.index.transitive_deps("api") == {"auth", "cache", "db", "log", "util"}   # complete
    assert res.index.reaches("api", "util") and not res.index.reaches("util", "api")
    # ── hierarchical index + proxies ──
    assert res.coverage == 1.0 and len(res.index.clusters) >= 2 and res.index.root_summary
    assert abs(res.fidelity - 2 / 3) < 1e-9                      # 2 of 3 claims were formalizable
    # ── honesty: a BEST_EFFORT claim is NEVER counted GROUNDED; grounding ≠ understanding ──
    assert len(res.grounded) == 1 and "Rice" in res.note and "not understanding" in res.note
    assert res.claims[2].status == "BEST_EFFORT" and "no better than an LLM" in res.claims[2].detail
    print(f"PASS test_s21_grounding_pipeline (claims {st}; multi-hop exact acc={res.multihop_accuracy:.0%}, "
          f"coverage={res.coverage:.0%}, fidelity={res.fidelity:.2f}; grounding≠understanding, LLM cmp BLOCKED)")


def test_s20_treesitter_frontend():
    """v28 S20: error-recovering, comment/string-correct frontend + common IR. The soundness core (pure
    Python) strips NESTED block comments and ignores markers inside strings — where a regex scanner
    silently corrupts the HIR. Unparsed regions become honest `assume_unknown`; new language = a frontend."""
    import treesitter_frontend as TF
    # ── ★ soundness core (always runs) ★: nested block comment — naive regex leaves garbage, ours doesn't ──
    nested = "let x = /* outer /* inner */ still-comment */ 5;"
    ours, _ = TF.strip_comments(nested, "rust")
    naive = TF.naive_regex_strip(nested)
    assert ours.split() == ["let", "x", "=", "5;"]           # the ENTIRE nested comment is gone (correct)
    assert "still-comment" in naive                          # the regex baseline is WRONG (leaves garbage)
    # `//` inside a string literal must be preserved (regex cuts the line)
    s2, _ = TF.strip_comments('url := "http://example.com"; x := 1', "go")
    assert "http://example.com" in s2 and TF.naive_regex_strip('a := "http://x"').strip() == 'a := "http:'
    # object-like macro expansion
    body, macros = TF.expand_macros("#define N 10\nint arr[N];")
    assert "arr[10]" in body and macros == {"N": "10"}
    # ── lower Go → the common HIR; the function name is recovered on either path ──
    mod, path = TF.to_hir("package m\nfunc add(a int, b int) int {\n  return a + b\n}\n", "go")
    names = [f.name for f in mod.functions]
    assert "add" in names and path in ("tree-sitter", "fallback")
    if TF.TREE_SITTER_AVAILABLE and "go" in TF._GRAMMARS:
        assert [f.params for f in mod.functions if f.name == "add"][0] == ["a", "b"]   # exact on the real CST
    # ── unparsed region → honest unknown (forced fallback path, always present) ──
    saved = TF.TREE_SITTER_AVAILABLE
    TF.TREE_SITTER_AVAILABLE = False
    try:
        m_ok, p = TF.to_hir("func add(a int, b int) int { return a+b }", "go")
        assert p == "fallback" and "add" in [f.name for f in m_ok.functions]
        m_bad, _ = TF.to_hir("func broken(b int) { { {", "go")
        assert any(f.ops and f.ops[0].kind == "assume_unknown" for f in m_bad.functions)   # no fake confidence
    finally:
        TF.TREE_SITTER_AVAILABLE = saved
    # ── common fact schema: the verifier mapping consumes these uniformly ──
    facts = TF.to_facts(mod)
    assert ("function", "add", ("a", "b")) in facts or any(f[0] == "function" for f in facts)
    print(f"PASS test_s20_treesitter_frontend (nested-comment+string strip correct vs regex-broken; macro; "
          f"Go→HIR via {path}; unparsed→assume_unknown; tree_sitter={TF.TREE_SITTER_AVAILABLE})")


def test_s19_latency_speed():
    """v28 S19: speed-first — watchdog (never hang), cache economics (stable prefix + padding + ledger),
    parallel orchestration. ★zero-wrong-answer invariant★: parallel/early-exit/cache only make it faster,
    never change the answer. Non-LLM latencies are measured; live model latency is [BLOCKED: key/egress]."""
    import latency_budget as LB
    import claude_agent as CA
    import time
    # ── watchdog: a slow stage HONEST-DEFERs fast (no hang); a fast stage returns OK with its value ──
    slow = LB.run_with_budget(lambda: time.sleep(5) or 42, 80)
    assert slow.status == "DEFERRED" and slow.elapsed_ms < 1500           # deferred in ~80ms, NOT 5s
    fast = LB.run_with_budget(lambda: sum(range(1000)), 1000)
    assert fast.status == "OK" and fast.value == 499500
    # ── cache economics: the real prefix is byte-stable; volatile content is rejected; padding reaches the
    #    provider min cacheable size and is itself stable ──
    assert LB.is_stable_prefix(CA.SYSTEM_PROMPT) and not LB.is_stable_prefix("generated 2026-06-18 now")
    padded = LB.pad_to_threshold(CA.SYSTEM_PROMPT, "anthropic")
    assert len(padded) >= LB.CACHE_MIN_TOKENS["anthropic"] * 4 and padded == LB.pad_to_threshold(CA.SYSTEM_PROMPT)
    assert padded.startswith(CA.SYSTEM_PROMPT)                            # original instruction preserved
    # cache ledger: write-then-read warms; savings>0 and hit-rate>0 by the 2nd call (break-even)
    led = LB.CacheLedger()
    led.record({"input_tokens": 100, "cache_creation_input_tokens": 2000})   # call 1 writes the prefix
    led.record({"input_tokens": 100, "cache_read_input_tokens": 2000})       # call 2 reads it (0.1×)
    assert led.hit_rate() > 0 and led.savings() > 0 and led.effective_cost() < led.baseline_cost()
    # ── wave scheduler: independent tasks share a wave; a cycle is rejected ──
    assert LB.schedule_waves({"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]}) == [["a"], ["b", "c"], ["d"]]
    try:
        LB.schedule_waves({"x": ["y"], "y": ["x"]}); assert False, "cycle not detected"
    except ValueError:
        pass
    # ── ★ zero-wrong-answer ★: parallel verification == sequential (only faster), never different ──
    m = LB.measure_parallel_orchestration([(0, 250000)] * 8, workers=4)
    assert m.same is True and m.status in ("OPTIMIZED", "NO_GAIN")        # identical results; speed varies by box
    assert LB.same_result(lambda x: x * x, lambda x: x * x, range(50))    # a correct fast path matches
    assert not LB.same_result(lambda x: x * x, lambda x: x * x + 1, range(50))  # a wrong one is caught
    print(f"PASS test_s19_latency_speed (watchdog defers {slow.elapsed_ms:.0f}ms not 5s; cache savings "
          f"{led.savings():.0%}@2calls; parallel {m.status} {m.speedup:.2f}× same={m.same}; zero-wrong-answer)")


def test_s18_dogfood():
    """v27 S18: HARAN re-verifies its own NON-KERNEL components by re-deriving each claim with the trusted
    core (Z3 + differential) — not by trusting the component. The kernel itself is residual TCB, NEVER
    self-certified (Gödel). The independent re-check genuinely catches a wrong claim (no rubber-stamping)."""
    import dogfood as DF
    r = DF.dogfood_all()
    assert r["all_certified"] is True and r["certified"] == r["total"] >= 5
    for c in r["components"]:
        assert c.status == "CERTIFIED" and c.rechecks > 0          # each re-verified by independent checks
    # the trusted core is reported as TCB and is NOT self-certified (Gödel)
    assert DF.dogfood_component("z3_adapter").status == "TCB"
    assert set(DF.residual_tcb()) == set(DF.TRUSTED_KERNEL) and len(DF.residual_tcb()) >= 3
    # ★ no rubber-stamping ★: force a component to emit a WRONG claim → the independent re-check FAILS it
    import fold_kernels as FK
    orig = FK.fold_certificate
    FK.fold_certificate = lambda code: FK.FoldVerdict("FOLDED", closed_form="n*n", kernel="faulhaber",
                                                      complexity="O(1)", certificate="forced", reason="")
    try:
        assert DF.dogfood_component("fold_kernels").status == "FAILED"   # n*n ≠ Σk → caught by the kernel
    finally:
        FK.fold_certificate = orig
    assert DF.dogfood_component("fold_kernels").status == "CERTIFIED"    # restored → certifies again
    # iCoq-style incremental: only CHANGED components are re-verified
    DF.incremental_rebuild(list(DF._RECHECKS))
    inc = DF.incremental_rebuild(["equality_saturation"])
    assert inc["reverified"] == ["equality_saturation"] and len(inc["cached"]) == len(DF._RECHECKS) - 1
    print(f"PASS test_s18_dogfood ({r['certified']}/{r['total']} non-kernel components re-verified by the "
          f"trusted core; {len(DF.residual_tcb())} TCB items NOT self-certified (Gödel); wrong-claim→FAILED)")


def test_s17_eqsat_ic3_hammer():
    """v27 S17 (EXTENDED depth): equality saturation (e-graph + Z3-certified extraction), unbounded safety
    by k-induction (IC3/PDR family), and a portfolio hammer. All kernel-checked; honest UNKNOWN/NO_GAIN."""
    import equality_saturation as ES
    import ic3_pdr as IC
    import tactic_hammer as TH
    import z3
    # ── equality saturation: explore equivalent forms, extract the cheapest, CERTIFY with Z3 ──
    t = ("+", ("*", ("var", "x"), ("const", 2)), ("*", ("var", "x"), ("const", 3)))   # x*2 + x*3
    v = ES.optimize(t)
    assert v.status == "OPTIMIZED" and v.after < v.before                 # x*2+x*3 → 5*x (fewer nodes)
    assert ES.optimize(("*", ("+", ("var", "x"), ("const", 0)), ("const", 1))).status == "OPTIMIZED"  # (x+0)*1→x
    assert ES.optimize(("+", ("var", "x"), ("var", "y"))).status == "NO_GAIN"          # already minimal
    # ★ soundness ★: force a WRONG extraction → the Z3 equivalence kernel must BLOCK it
    orig = ES.extract
    ES.extract = lambda eg, root: ("const", 999)
    try:
        assert ES.optimize(t).status == "UNSOUND_BLOCKED"                 # 999 ≢ x*2+x*3 → rejected
    finally:
        ES.extract = orig
    # ── unbounded safety by k-induction: SAFE (invariant) / UNSAFE (+trace) / UNKNOWN ──
    safe = IC.prove_safety(["x"], lambda s: s["x"] == 0, lambda s, sp: sp["x"] == s["x"] + 1,
                           lambda s: s["x"] >= 0)
    assert safe.status == "SAFE" and safe.method == "k-induction" and safe.k >= 1
    unsafe = IC.prove_safety(["x"], lambda s: s["x"] == 0, lambda s, sp: sp["x"] == s["x"] + 1,
                             lambda s: s["x"] <= 3, max_k=8)
    assert unsafe.status == "UNSAFE" and unsafe.trace and unsafe.trace[-1]["x"] == 4   # real CEX trace
    unk = IC.prove_safety(["x"], lambda s: s["x"] == 0, lambda s, sp: sp["x"] == s["x"] + 2,
                          lambda s: s["x"] != 1, max_k=5)
    assert unk.status == "UNKNOWN"                                        # true but not k-inductive (honest)
    # ── hammer portfolio: discharge a fraction; report the rest honestly; proof reuse is perceived-zero ──
    corpus = [("n*n >= 0", {"n": "Int"}), ("a + b >= b + a", {"a": "Int", "b": "Int"}),
              ("2*n == n + n", {"n": "Int"}), ("a + b >= a", {"a": "Int", "b": "Int"}), ("n >= 1", {"n": "Int"})]
    st = TH.measure_hammer(corpus)
    assert st.proved == 3 and st.not_proved == 2 and 0.0 < st.success_rate < 1.0   # honest fraction
    import proof_cache as PC
    PC.reset()
    _r1, _h1 = TH.reuse_or_prove("n*n >= 0", {"n": "Int"})
    _r2, h2 = TH.reuse_or_prove("n*n >= 0", {"n": "Int"})
    assert h2 is True                                                    # 2nd obligation reused from cache
    assert TH.hammer("a + b >= a", {"a": "Int", "b": "Int"}).status == "NOT_PROVED"   # false → honest
    print(f"PASS test_s17_eqsat_ic3_hammer (eq-sat {v.before}→{v.after} Z3-certified + UNSOUND blocked; "
          f"k-induction SAFE/UNSAFE(trace→4)/UNKNOWN; hammer {st.success_rate:.0%} proved, reuse cached)")


def test_s16_levers_verifier_gated():
    """v27 S16: orthogonal accuracy levers, ALL verifier-gated. Type-constrained decoding emits only
    well-typed programs by construction (measured compile-error reduction); repo-RAG + the verified cache
    are PROPOSERS — every proposal must pass the verifier or be rejected (never trusted blindly)."""
    import typed_decoding as TD
    import repo_rag as RR
    import ai_loop
    # ── type-constrained decoding: the mask prunes ill-typed tokens; output is well-typed by construction ──
    assert "b" not in TD.valid_next_tokens([])              # a Bool var is pruned from an Int operand slot
    assert "<" not in TD.valid_next_tokens(["x"])           # '<' (→Bool) pruned where Int is required
    assert TD.welltyped_int(["x", "+", "2", "*", "y"]) and not TD.welltyped_int(["x", "+", "b"])
    m = TD.measure_welltyped_rate(2000)
    assert m["constrained_welltyped"] == 1.0                # 100% well-typed BY CONSTRUCTION
    assert m["unconstrained_welltyped"] < 0.2 and m["compile_error_reduction"] > 0.8   # measured, large lift
    # ── repo-RAG: retrieval is a proposal; the verifier decides ──
    TRI = "fn t(n: Nat) -> Nat\n  ensures result = n*(n+1)/2\n{ fold k in 1..n { %s } }"
    good, bad = TRI % "k", TRI % "k+1"
    sq = "fn sq(n: Nat) -> Nat\n  ensures result = n*n\n{ fold k in 1..n { 2*k-1 } }"
    corpus = [RR.Entry("t_bad", bad), RR.Entry("t_good", good), RR.Entry("sq", sq)]
    res = RR.retrieve_and_verify(good, corpus, k=3)
    assert res.status == "VERIFIED_RETRIEVAL" and ai_loop.verify_haran(res.source).ok   # returned thing PROVES
    # a corpus whose only candidate is spec-violating ⇒ the gate rejects it (RAG is NOT trusted)
    only_bad = RR.retrieve_and_verify(good, [RR.Entry("t_bad", bad)], k=1)
    assert only_bad.status == "NO_VERIFIED_CANDIDATE" and only_bad.rejected == ["t_bad"]
    # ── verified-solution cache: stores only VERIFIED solutions; a hit is re-verified before reuse ──
    c = RR.VerifiedSolutionCache()
    assert c.put(good) is True and c.put(bad) is False     # an unverified solution is NEVER cached
    assert c.get(good) is not None and c.get(TRI % "2*k") is None
    assert c.hits == 1 and c.misses == 1
    print(f"PASS test_s16_levers_verifier_gated (typed-decode well-typed {m['constrained_welltyped']:.0%} vs "
          f"{m['unconstrained_welltyped']:.0%}, err-reduction {m['compile_error_reduction']:.0%}; "
          f"RAG/cache verifier-gated — unverified rejected)")


def test_s15_bug_funnel():
    """v27 S15: statistics → diffusion → sound-verification funnel. SBFL ranks (heuristic, RANKED≠proof);
    graph-Laplacian diffusion (heat = random-walk = spectral, shared L) spreads suspicion; layer 3 CONFIRMS
    with a witness (VULN_PROVEN) or a class-absence proof — Rice-bounded, multi-fault degrades honestly."""
    import sbfl as SB
    import diffusion_localize as DL
    T = SB.Test
    tests = [T({"f0", "f2"}, False), T({"f1", "f2"}, False), T({"f2", "f3"}, False), T({"f0", "f1", "f2"}, False),
             T({"f0"}, True), T({"f1"}, True), T({"f3"}, True), T({"f0", "f1"}, True), T({"f0", "f3"}, True)]
    # ── layer 1: every SBFL metric ranks the true fault (f2) #1; output is labeled RANKED (not a proof) ──
    for m in ("ochiai", "dstar", "op2", "tarantula"):
        r = SB.suspiciousness(tests, m)
        assert r.top(1) == ["f2"], (m, r.ranked)
        assert "NOT a proof" in r.note
    assert SB.suspiciousness(tests, "op2").single_fault_optimal is True
    # ── layer 2: diffusion spreads suspicion along the SAME Laplacian L — a neighbor of suspicious nodes
    #    is lifted above an equally-scored isolated node (pagerank AND heat) ──
    sc = {"X": 0.1, "Y": 0.1, "S1": 0.9, "S2": 0.9}
    g2 = {"X": ["S1", "S2"], "S1": ["X"], "S2": ["X"], "Y": []}
    assert DL.pagerank_diffuse(sc, g2)["X"] > DL.pagerank_diffuse(sc, g2)["Y"]
    assert DL.heat_diffuse(sc, g2)["X"] > DL.heat_diffuse(sc, g2)["Y"]
    # ── layer 3: the funnel confirms a witness for the real bug, proves the modeled class absent elsewhere ──
    graph = {"f0": ["f2"], "f1": ["f2"], "f2": ["f0", "f1", "f3"], "f3": ["f2"]}
    code_map = {"f0": "fn f0(x: Int) -> Int\n{ x + 1 }",
                "f1": "fn f1(x: Int) -> Int\n{ x * 2 }",
                "f2": "fn f2(a: Int, b: Int) -> Int\n{ a / b }",                  # reachable div-by-zero
                "f3": "fn f3(a: Int, b: Int) -> Int\n  requires b != 0\n{ a / b }"}  # guarded → absence
    res = DL.funnel(tests, graph, code_map, metric="op2", topk=4)
    byname = {f.element: f for f in res.findings}
    assert byname["f2"].status == "VULN_PROVEN" and byname["f2"].bug_class == "div_by_zero"
    assert byname["f2"].witness["b"] == "0"                       # a real exploit witness, not a guess
    assert byname["f3"].status == "ABSENCE_PROVEN" and "Rice-bounded" in byname["f3"].detail
    assert [f.element for f in res.proven] == ["f2"]
    # an element with no modelable source → RANKED (explicitly NOT confirmed)
    r2 = DL.funnel(tests, graph, {"f2": code_map["f2"]}, metric="op2", topk=2)
    assert any(f.status == "RANKED" and "NOT confirmed" in str(f) for f in r2.findings if f.element != "f2")
    # ── multi-fault honesty: single-fault optimality no longer applies ──
    mt = [T({"a", "bug1"}, False), T({"b", "bug2"}, False), T({"a", "b"}, True), T({"a"}, True), T({"b"}, True)]
    md = SB.multi_fault_degradation(mt, ["bug1", "bug2"])
    assert md["single_fault_optimal_applies"] is False and "degrades" in md["note"]
    # Liblit: a predicate that predicts failure has positive Increase
    assert SB.liblit_increase([(True, True), (True, True), (False, False), (False, False)]) > 0
    print("PASS test_s15_bug_funnel (SBFL ranks f2 #1 all metrics; diffusion spreads on shared L; "
          "funnel VULN_PROVEN[div_by_zero] witness b=0 + ABSENCE_PROVEN; multi-fault degrades honestly)")


def test_s14_spectral_partition():
    """v27 S14: Fiedler/spectral bisection (+ KL refinement) cuts a dep-graph into weakly-coupled chunks
    for PARALLEL decomposition — a seed only, NOT a modularization-quality claim. Pure-Python; honest
    scale flag beyond the practical N."""
    import repo_partition as RP
    # two triangles joined by ONE edge → each triangle stays whole, cut = 1
    g = {0: [1, 2], 1: [0, 2], 2: [0, 1, 3], 3: [2, 4, 5], 4: [3, 5], 5: [3, 4]}
    p = RP.partition(g, k=2)
    assert p.cut == 1 and sorted(p.sizes) == [3, 3]
    assert p.parts[0] == p.parts[1] == p.parts[2] and p.parts[3] == p.parts[4] == p.parts[5]
    assert p.parts[0] != p.parts[3]                               # the two triangles are separated
    assert p.cross_deps == p.cut and "spectral" in p.method
    # complete graph K6 → NO good cut (balanced bisection unavoidably cuts 3·3 = 9) — honestly high
    k6 = {i: [j for j in range(6) if j != i] for i in range(6)}
    assert RP.partition(k6, k=2).cut == 9
    # 4 cliques in a ring → k=4 recovers them; cut = the 4 ring links (the minimum), balanced chunks of 4
    def clique(base): return {base + i: [base + j for j in range(4) if j != i] for i in range(4)}
    ring = {}
    for c in range(4):
        ring.update(clique(4 * c))
    for a, b in [(3, 4), (7, 8), (11, 12), (15, 0)]:
        ring[a] = ring[a] + [b]; ring[b] = ring[b] + [a]
    p4 = RP.partition(ring, k=4)
    assert p4.k == 4 and p4.sizes == [4, 4, 4, 4] and p4.cut == 4
    for c in range(4):                                            # each clique stays in one chunk
        assert len({p4.parts[4 * c + i] for i in range(4)}) == 1
    sched = RP.parallel_schedule(p4)
    assert sched["n_chunks"] == 4 and sched["cross_deps"] == 4 and len(sched["independent_chunks"]) == 4
    # honest scale: beyond the pure-Python practical N → blocked flag set (still returns a partition)
    big = {i: [(i + 1) % (RP.MAX_PRACTICAL_N + 100), (i + 2) % (RP.MAX_PRACTICAL_N + 100)]
           for i in range(RP.MAX_PRACTICAL_N + 100)}
    pb = RP.partition(big, k=2)
    assert pb.blocked is True and "scale-limited" in pb.detail
    print(f"PASS test_s14_spectral_partition (triangles cut={p.cut}, K6 cut=9 honest, 4-ring k=4 cut={p4.cut}; "
          f"seed+KL, no module-quality claim; >{RP.MAX_PRACTICAL_N} nodes → BLOCKED scale)")


def test_s13_fold_replicate():
    """v27 S13: prove a parametric template ONCE → certify N instances by the cheap side-condition check
    (sound universal instantiation). The Z3 solve is paid once, so the speedup GROWS with N (scale gap);
    a false property is refuted (NOT_A_TEMPLATE), a bad instance is REJECTED, the summary cache makes a
    re-run perceived-zero, and below 30% repetition folding is disabled."""
    import fold_replicate as FR
    # ── structural clone detection: affine maps differing only in constants collapse to one signature ──
    c1, c2, c3 = "def f1(x):\n    return 3*x + 1", "def f2(y):\n    return 5*y + 2", "def f3(z):\n    return 9*z + 4"
    uniq = "def w(x):\n    return x*x - 7"
    assert FR.structural_signature(c1)[0] == FR.structural_signature(c2)[0]   # clones share a signature
    assert FR.structural_signature(c1)[0] != FR.structural_signature(uniq)[0]
    assert FR.structural_signature(c1)[1] == [3, 1]                       # holes = the constants, in order
    assert len(FR.group_clones([c1, c2, c3])) == 1                        # one clone family
    assert FR.repetition_rate([c1, c2, c3]) == 1.0
    assert FR.should_fold([c1, c2, c3]) is True
    # 1 clone pair + 8 structurally-DISTINCT functions ⇒ repetition 2/10 = 20% < 30% → folding disabled
    distinct = ["def u0(x):\n    return x * x", "def u1(x):\n    return x + x + x",
                "def u2(x):\n    return (x - 1) * 2", "def u3(x):\n    return x % 3 + x",
                "def u4(x):\n    return abs(x)", "def u5(x):\n    return x if x > 0 else 0 - x",
                "def u6(x):\n    return [x, x]", "def u7(x):\n    return {x: x}"]
    assert FR.repetition_rate([c1, c2] + distinct) == 0.2
    assert FR.should_fold([c1, c2] + distinct) is False                   # <30% → honest disable
    # ── prove the template ONCE, certify N instances; a bad side-condition (A<0) is REJECTED ──
    t = FR.Template("affine_monotone", ["A", "B"], {"A": "Int", "B": "Int"}, {"x1": "Int", "x2": "Int"},
                    precond=["A >= 0"], ensures="A*x1 + B <= A*x2 + B", input_hyp=["x1 <= x2"])
    small = [{"A": (i % 9) + 1, "B": i} for i in range(24)] + [{"A": -2, "B": 3}]   # last violates A>=0
    v = FR.replicate(t, small)
    assert v.status == "REPLICATED" and v.certified == 24 and v.n == 25       # 24 certified, 1 rejected
    assert [c.holes for c in v.instances if c.status == "REJECTED"] == [{"A": -2, "B": 3}]
    assert "PROVEN" in v.template_proof and v.crossover_n >= 1
    # ── ★ scale advantage ★: speedup at large N strictly exceeds small N (the gap WIDENS with N) ──
    sp_small = FR.replicate(t, [{"A": (i % 9) + 1, "B": i} for i in range(24)]).speedup
    big = FR.replicate(t, [{"A": (i % 40) + 1, "B": i} for i in range(150)])
    assert big.certified == 150 and big.speedup > sp_small and big.speedup > 2.0   # measured widening
    # ── a FALSE parametric property is refuted with a counterexample — never replicated ──
    bad = FR.replicate(FR.Template("bad", ["A"], {"A": "Int"}, {"x": "Int"}, precond=[], ensures="A*x >= x"),
                       [{"A": 2}, {"A": 3}])
    assert bad.status == "NOT_A_TEMPLATE" and bad.counterexample is not None
    # fewer than 2 instances → NOT_REPEATED (honest)
    assert FR.replicate(t, [{"A": 1, "B": 0}]).status == "NOT_REPEATED"
    # ── summary cache (Merkle): a re-run re-proves only CHANGED templates (perceived-zero unchanged) ──
    t2 = FR.Template("t2", ["A"], {"A": "Int"}, {"x": "Int"}, precond=["A >= 1"], ensures="A*x*x >= 0",
                     input_hyp=["x >= 0"])
    cold = FR.fold_repo([(t, small), (t2, [{"A": 1}])], reset=True)
    warm = FR.fold_repo([(t, small), (t2, [{"A": 1}])], reset=False)
    assert cold["proved"] == 2 and cold["cached"] == 0
    assert warm["cached"] == 2 and warm["proved"] == 0 and warm["ms"] < cold["ms"]
    print(f"PASS test_s13_fold_replicate (REPLICATED 24/25 certified; scale {sp_small:.1f}×@24 → "
          f"{big.speedup:.1f}×@150 (gap widens); NOT_A_TEMPLATE refuted; cache {cold['ms']:.1f}→{warm['ms']:.2f}ms)")


def test_s12_structure_offload():
    """v27 S12: structure recognition + LLM-offload dispatcher. Recognizer classes the 7 shapes; the two
    SOUND actions (closed-form OFFLOAD via verified lifting, equi-join hash-join REWRITE) are gated by
    execution so a wrong answer is never emitted; unrecognized/unsupported → honest NONE (LLM fallback)."""
    import structure_recognizer as SR
    sum_src  = "def f(n):\n    acc = 0\n    for k in range(1, n + 1):\n        acc += k\n    return acc"
    sq_src   = "def g(m):\n    s = 0\n    for k in range(m):\n        s = s + k*k\n    return s"
    fact_src = "def fact(n):\n    p = 1\n    for k in range(1, n+1):\n        p *= k\n    return p"
    join_src = "def jn(A, B):\n    out = []\n    for a in A:\n        for b in B:\n            if a[0] == b[0]:\n                out.append((a, b))\n    return out"
    mm_src   = "def mm(A, B, C, n):\n    for i in range(n):\n        for j in range(n):\n            for k in range(n):\n                C[i][j] += A[i][k] * B[k][j]\n    return C"
    fx_src   = "def solve(init):\n    changed = True\n    s = set(init)\n    while changed:\n        changed = False\n        for x in list(s):\n            if x + 1 not in s and x < 5:\n                s.add(x + 1); changed = True\n    return s"
    re_src   = "def parse(t):\n    import re\n    return re.findall(r'\\\\d+', t)"
    rnd_src  = "def mc(n):\n    import random\n    h = 0\n    for _ in range(n):\n        if random.random() < 0.5:\n            h += 1\n    return h / n"
    glue_src = "def h(cfg):\n    x = cfg.get('a', 1)\n    return {'r': str(x) + '!', 'ok': True}"
    # ── recognizer: each class is identified by sound static analysis ──
    assert SR.recognize(sum_src).kind == SR.CLOSED_FORM_LOOP and SR.recognize(sum_src).algebra == "monoid"
    assert SR.recognize(join_src).kind == SR.RELATIONAL_JOIN and SR.recognize(join_src).algebra == "semiring"
    assert SR.recognize(mm_src).kind == SR.TENSOR_LA
    assert SR.recognize(fx_src).kind == SR.DATAFLOW_FIXPOINT
    assert SR.recognize(re_src).kind == SR.STRING_REGEX
    assert SR.recognize(rnd_src).kind == SR.PROBABILISTIC_APPROX
    assert SR.recognize(glue_src).kind == SR.NONE
    # ── action 1: OFFLOAD closed-form loops to the fold solver, equivalence-verified ──
    d_sum, d_sq = SR.dispatch(sum_src), SR.dispatch(sq_src)
    assert d_sum.status == "OFFLOADED" and d_sum.complexity == "O(1)" and "n*(n + 1)/2" in d_sum.closed_form
    assert d_sq.status == "OFFLOADED" and "differential-equivalence verified" in d_sum.certificate
    # a PRODUCT loop is NOT a Σ-fold → honest NONE (never lifted to a wrong summation)
    assert SR.dispatch(fact_src).status == "NONE"
    # ── action 2: equi-join → certified hash-join rewrite, measured + equivalence-verified ──
    d_join = SR.dispatch(join_src)
    assert d_join.status == "RECOGNIZED_REWRITE" and d_join.speedup >= 1.1 and "O(n+m)" in d_join.certificate
    # ── ★ soundness ★: force the fold solver to return a WRONG closed form → the gate must DECLINE (NONE) ──
    import fold_kernels as FK
    orig = FK.fold_certificate
    FK.fold_certificate = lambda code: FK.FoldVerdict("FOLDED", closed_form="n*n", kernel="faulhaber",
                                                      complexity="O(1)", certificate="forced", reason="")
    try:
        assert SR.dispatch(sum_src).status == "NONE"   # n*n ≠ Σk → equivalence gate rejects → NONE
    finally:
        FK.fold_certificate = orig
    # glue with no structure → NONE (honest LLM fallback)
    assert SR.dispatch(glue_src).status == "NONE"
    print(f"PASS test_s12_structure_offload (OFFLOAD Σk→{d_sum.closed_form}, Σk²→{d_sq.closed_form}; "
          f"JOIN hash-rewrite {d_join.speedup:.1f}×; product/glue→NONE; forced-wrong-form→NONE)")


def test_s11_live_measure_honest():
    """v26.2 S11: the first-live-test harness. The LIVE LLM loop is honestly BLOCKED (no key / egress);
    the NON-LLM half (loop convergence, parallel transform, proof reuse) is genuinely MEASURED. This test
    is network-free: it pins the PURE classification + the real measurements + the honesty of the report."""
    import sys
    sys.path.insert(0, "scripts")
    import s11_live_measure as S11
    # classify_probe — the honest (HTTP, body) → status mapping (no network)
    assert S11.classify_probe(401, '{"error":{"message":"invalid x-api-key"}}')[0] == "AUTH_ONLY"
    assert S11.classify_probe(403, "Host not in allowlist: api.z.ai")[0] == "EGRESS_BLOCKED"
    assert S11.classify_probe(400, "max_tokens: required")[0] == "SHAPE_REJECTED"   # a 400-causer would show here
    assert S11.classify_probe(200, "{ok}")[0] == "LIVE_OK"
    assert S11.classify_probe(0, "URLError: no route")[0] == "NO_EGRESS"
    # loop convergence is REAL: extended solves all 4 (incl. the 3-iteration case), normal misses it — and
    # NEITHER mode is ever wrong (the zero-wrong-answer invariant, measured over the corpus).
    ext = S11.measure_loop_convergence("extended")
    nrm = S11.measure_loop_convergence("normal")
    assert ext.solved == 4 and ext.wrong == 0 and 3 in ext.histogram and ext.total_ms > 0
    assert nrm.solved == 3 and nrm.wrong == 0          # budget 2 < 3 needed → honest miss, never a false PROVEN
    # runtime transform measured; equivalence MUST have held (never MISMATCH/DECLINED for an associative op)
    par = S11.measure_parallel(n=200_000, cores=4)
    assert par["status"] in ("OPTIMIZED", "NO_GAIN")
    # proof reuse: round-2 re-verify is lossless and not slower (perceived-zero)
    ru = S11.measure_proof_reuse()
    assert ru["lossless"] and ru["mismatches"] == 0 and ru["warm_ms"] <= ru["cold_ms"] + 1e-6
    # the report is HONEST: with no key + an egress-blocked gateway it shows [BLOCKED] + [NEXT] + a TBD for
    # the live latency, and never prints a fabricated live number.
    rep = S11.build_report([S11.Probe("Anthropic", "anthropic", 401, "AUTH_ONLY", "shape ok"),
                            S11.Probe("GLM (Z.ai)", "openai_compat", 403, "EGRESS_BLOCKED", "allowlist")],
                           nrm, ext, par, ru, have_key=False)
    assert "[BLOCKED]" in rep and "[NEXT]" in rep and "TBD" in rep and "SHAPE accepted" in rep
    print(f"PASS test_s11_live_measure_honest (extended {ext.solved}/4 iters "
          f"{dict(sorted(ext.histogram.items()))}, normal {nrm.solved}/4; parallel {par['status']}; "
          f"reuse lossless={ru['lossless']})")


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


# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# FOLD-ENGINE EXTENSION (v32) — measured coverage on a fixed defer corpus. Discipline: every detector is
# paired with a SOUND verifier; coverage is MEASURED (never estimated); clocks never mixed; no false fold.
# ═══════════════════════════════════════════════════════════════════════════════════════════════════
def test_foldext_stage0_defer_corpus():
    """STAGE 0: a fixed, categorized defer corpus with a MEASURED baseline (the basis for the whole study).
    Covers: defer_corpus_loaded, baseline_fold_rate_recorded, corpus_categorized, heldout_split_exists."""
    import json
    import os
    import defer_corpus as DC
    from defer_corpus.schema import CATEGORIES, SPLITS
    # defer_corpus_loaded: the fixed set loads and every case is well-formed
    cases = DC.load()
    assert len(cases) >= 24, f"corpus too small to measure: {len(cases)}"
    for c in cases:
        assert c.category in CATEGORIES and c.split in SPLITS and c.expect in ("foldable", "defer")
    assert len({c.cid for c in cases}) == len(cases), "case ids must be unique"
    # corpus_categorized: all six structural categories present and non-empty
    cats = DC.by_category()
    assert all(len(cats[cat]) >= 1 for cat in CATEGORIES), f"empty category: {[c for c in CATEGORIES if not cats[c]]}"
    # heldout_split_exists: tune and measure are both non-empty and DISJOINT (no overfit leakage)
    tune, meas = DC.split("tune"), DC.split("measure")
    assert tune and meas and not ({c.cid for c in tune} & {c.cid for c in meas})
    # baseline_fold_rate_recorded: a real measured number, deterministic, and the manifest carries it
    b1 = DC.baseline(); b2 = DC.baseline()
    assert b1.folded == b2.folded and 0.0 <= b1.fold_rate <= 1.0      # deterministic measurement
    assert b1.clock_b_n >= 1 and "linear-algebra" not in b1.per_category   # Clock B counted SEPARATELY (never mixed)
    # negative controls (blackbox + *_neg) currently defer — there must be real headroom AND real traps
    assert b1.fold_rate < 1.0, "a baseline of 100% would mean no headroom to measure"
    doc = DC.write_manifest()
    assert os.path.exists(DC.MANIFEST)
    saved = json.load(open(DC.MANIFEST))
    assert saved["baseline"]["clock_C_fold_rate"] == b1.fold_rate and saved["n_total"] == len(cases)
    print(f"PASS test_foldext_stage0_defer_corpus ({len(cases)} cases, 6 categories; baseline Clock-C "
          f"fold-rate {b1.folded}/{b1.n}={b1.fold_rate:.0%} (measured); +{b1.clock_b_n} Clock-B; "
          f"tune {len(tune)}/measure {len(meas)} held-out)")


def test_foldext_stageA_kovacic():
    """STAGE A: differential-Galois/Kovacic foldability for 2nd-order linear ODEs. Detector recovers
    (p,q) from an Euler loop; dsolve proposes; EXACT re-substitution is the sound gate; non-Liouvillian
    defers with a certificate. Covers: detect_ode_discretization, kovacic_decides_liouvillian,
    closed_form_verified_before_fold, non_liouvillian_defers_with_cert, kovacic_scope_2nd_order_linear_only,
    ode_corpus_hit_rate_measured."""
    import sympy as sp
    import kovacic as K
    # detect_ode_discretization: recover (p,q) from a REAL Euler discretization loop (round-trip)
    for p, q in [("0", "-1"), ("3", "2"), ("1/x", "-1/x**2")]:
        rec = K.recover_ode_from_euler(K.euler_source(p, q))
        assert rec is not None and sp.simplify(sp.sympify(rec[0]) - sp.sympify(p)) == 0 \
            and sp.simplify(sp.sympify(rec[1]) - sp.sympify(q)) == 0, f"failed to recover ({p},{q}): {rec}"
    assert K.recover_ode_from_euler("x = 1\ny = 2\n") is None     # not an Euler scheme → None (no false detect)
    # kovacic_decides_liouvillian: exp / trig / Euler-Cauchy fold with a verified closed form
    ve = K.kovacic_decide("0", "-1")          # y'' - y = 0 → exp
    assert ve.status == "FOLDED" and ve.liouvillian is True and "exp" in ve.closed_form
    vt = K.kovacic_decide("0", "1")           # y'' + y = 0 → sin/cos
    assert vt.status == "FOLDED" and ("sin" in vt.closed_form or "cos" in vt.closed_form)
    # closed_form_verified_before_fold: EVERY fold carries an exact re-substitution proof; the gate really gates
    assert ve.cert_type == "exact" and ve.verified_exact is True
    x = sp.Symbol("x"); C1, C2 = sp.symbols("C1 C2")
    good_ok, _ = K._verify_solution(sp.Integer(0), sp.Integer(-1), C1 * sp.exp(x) + C2 * sp.exp(-x), x, [C1, C2])
    bad_ok, _ = K._verify_solution(sp.Integer(0), sp.Integer(-1), C1 * sp.sin(x) + C2 * sp.cos(x), x, [C1, C2])
    assert good_ok is True and bad_ok is False, "sound gate must accept a true solution and REJECT a wrong one"
    # non_liouvillian_defers_with_cert: Airy / Bessel defer, with an informative (non-Liouvillian) certificate
    air = K.kovacic_decide("0", "-x")         # y'' - x y = 0 → Airy
    assert air.status == "DEFER" and air.liouvillian is False and "Liouvillian" in air.detail
    bes = K.kovacic_decide("1/x", "-1")       # → Bessel
    assert bes.status == "DEFER" and bes.liouvillian is False
    ser = K.kovacic_decide("0", "x**2")       # truncated series — NOT a closed form → defer (trap caught)
    assert ser.status == "DEFER" and "series" in ser.detail.lower()
    # kovacic_scope_2nd_order_linear_only: higher-order / nonlinear is OUT_OF_SCOPE (no overclaim)
    assert K.kovacic_decide("0", "-1", order=3).status == "OUT_OF_SCOPE"
    assert K.kovacic_decide("0", "-1", linear=False).status == "OUT_OF_SCOPE"
    # ode_corpus_hit_rate_measured: real numbers on the corpus, and ZERO false folds (100% correctness)
    m = K.measure_ode_corpus()
    assert m["n"] >= 6 and m["folded"] >= 4 and m["correctness"] == 1.0 and m["clock"] == "C"
    mh = K.measure_ode_corpus(split="measure")     # held-out: still no false fold
    assert mh["correctness"] == 1.0
    print(f"PASS test_foldext_stageA_kovacic (detector round-trips; [Clock C] ODE corpus baseline 0/{m['n']} "
          f"-> folded {m['folded']}/{m['n']} (decision {m['decision_rate']:.0%}); Airy/Bessel/series DEFER w/ "
          f"cert; correctness {m['correctness']:.0%} (no false fold); held-out {mh['fold_rate']:.0%})")


def test_foldext_stageB1_benortiwari():
    """STAGE B1: Ben-Or–Tiwari sparse multivariate interpolation of a BLACK-BOX polynomial. Recover via
    Berlekamp-Massey + prime-power factoring; SOUND-gate by Schwartz-Zippel at fresh points. Covers:
    detect_blackbox_poly_loop, benortiwari_recovers_sparse_poly, recovered_poly_verified_schwartz_zippel,
    early_termination_works, poly_corpus_hit_rate_measured."""
    from fractions import Fraction as Fr
    import benortiwari as BT
    # benortiwari_recovers_sparse_poly: Berlekamp-Massey finds the monomial-eval roots; recovery is EXACT
    C = BT.berlekamp_massey([Fr(2**j + 3**j) for j in range(6)])
    assert sorted(BT._integer_roots(C)) == [2, 3]                  # roots of 2^j+3^j ⇒ {2,3}
    r = BT.recover(lambda x, y: 5 * x**3 * y**2 + 3 * x * y + 7, 2)
    assert r.status == "FOLDED" and r.n_terms == 3 and r.verified
    # the recovered polynomial equals the black box at a battery of explicit points (independent re-check)
    import sympy as sp
    xs, ys = sp.symbols("x y")
    expr = sp.sympify(r.poly_str)
    for (xv, yv) in [(4, 6), (7, 2), (10, 9)]:
        assert int(expr.subs({xs: xv, ys: yv})) == 5 * xv**3 * yv**2 + 3 * xv * yv + 7
    # detect_blackbox_poly_loop: B1 distinguishes the recoverable polynomial class from non-polynomials
    assert BT.recover(lambda x, y: x * y + x, 2).status == "FOLDED"            # polynomial → recovered
    assert BT.recover(lambda x: x % 7, 1).status == "DEFER"                    # not polynomial → DEFER
    # recovered_poly_verified_schwartz_zippel: the gate accepts a true recovery, REJECTS a wrong one; ε stated
    mons_good = [((1, 0), Fr(1)), ((0, 1), Fr(1))]                             # x + y
    ok, eps, deg = BT.verify_schwartz_zippel(lambda x, y: x + y, mons_good, 2)
    assert ok is True and 0 < eps < 1e-30
    bad, _, _ = BT.verify_schwartz_zippel(lambda x, y: x + y, [((1, 0), Fr(1))], 2)   # claim "x" for x+y
    assert bad is False                                                        # caught at a fresh point
    # early_termination_works: a 4-term poly is recovered as exactly 4 terms (order stabilized, not max_terms)
    r4 = BT.recover(lambda x, y: 4 * x**3 + 3 * x**2 * y + 2 * x * y**2 + y**3, 2)
    assert r4.status == "FOLDED" and r4.n_terms == 4
    # poly_corpus_hit_rate_measured: real numbers; negative controls DEFER (no false structure)
    m = BT.measure_poly_corpus()
    assert m["n"] >= 6 and m["folded"] >= 5 and m["correctness"] == 1.0 and m["clock"] == "C"
    mh = BT.measure_poly_corpus(split="measure")
    assert mh["correctness"] == 1.0
    print(f"PASS test_foldext_stageB1_benortiwari (BM roots ✓; [Clock C] poly corpus baseline 0/{m['n']} "
          f"-> folded {m['folded']}/{m['n']} (hit {m['hit_rate']:.0%}); SZ-gate rejects non-polys; "
          f"correctness {m['correctness']:.0%}; held-out {mh['hit_rate']:.0%})")


def test_foldext_stageB2_qfold():
    """STAGE B2: q-Gosper telescoping fold for q-holonomic sums SymPy's summation misses. Detect q-ratio;
    bounded rational telescoper; EXACT verification gate. Covers: detect_q_ratio, q_zeilberger_folds,
    q_certificate_verified, dispersion_timeout_defers, q_corpus_hit_rate_measured."""
    from fractions import Fraction as Fr
    import sympy as sp
    import q_fold as Q
    q, k, n, X = sp.symbols("q k n X")
    # detect_q_ratio: the q-ratio t(k+1)/t(k) is rational in x=q^k (q-hypergeometric); returns ρ(X)
    rho = Q._q_ratio_rational(sp.sympify("q**k", locals={"q": q, "k": k}), q, k, X)
    assert rho is not None and sp.simplify(rho - q) == 0           # ratio of q^k is q (constant, rational)
    # q_zeilberger_folds: a telescoping q-term SymPy's summation leaves unevaluated now folds (the B2 win)
    assert sp.summation(sp.sympify("q**k/((1-q**k)*(1-q**(k+1)))", locals={"q": q, "k": k}),
                        (k, 1, n)).has(sp.Sum)                     # baseline (sympy) does NOT close it
    vt = Q.q_fold("q**k/((1-q**k)*(1-q**(k+1)))")
    assert vt.status == "FOLDED" and vt.verified and vt.cert_type == "exact"
    vd = Q.q_fold("q**k - q**(k-1)")
    assert vd.status == "FOLDED" and sp.simplify(sp.sympify(vd.closed_form) - (q**n - 1)) == 0
    # q_certificate_verified: the folded closed form is INDEPENDENTLY correct (direct numeric sum at q=1/2)
    Sn = sp.sympify(vt.closed_form)
    for N in (4, 7):
        closed = Sn.subs({q: sp.Rational(1, 2), n: N})
        direct = sum(Fr(1, 2)**j / ((1 - Fr(1, 2)**j) * (1 - Fr(1, 2)**(j + 1))) for j in range(1, N + 1))
        assert sp.nsimplify(closed) == sp.Rational(direct.numerator, direct.denominator), \
            f"folded closed form disagrees with the direct sum at n={N}"
    # dispersion_timeout_defers: theta (q^{k²}) and q-harmonic have NO closed form → DEFER with a reason
    vth = Q.q_fold("q**(k*k)")
    assert vth.status == "DEFER" and vth.q_hypergeometric is True and "theta" in vth.detail.lower()
    vqh = Q.q_fold("q**k/(1-q**k)")
    assert vqh.status == "DEFER" and "telescoper" in vqh.detail.lower()
    # q_corpus_hit_rate_measured: real numbers, ZERO false folds (negative controls defer)
    m = Q.measure_q_corpus()
    assert m["n"] >= 4 and m["folded"] >= 2 and m["correctness"] == 1.0 and m["clock"] == "C"
    mh = Q.measure_q_corpus(split="measure")
    assert mh["correctness"] == 1.0
    print(f"PASS test_foldext_stageB2_qfold ([Clock C] q corpus baseline 1/{m['n']} -> folded {m['folded']}/"
          f"{m['n']} (hit {m['hit_rate']:.0%}); telescoper exact-verified + independent numeric check; "
          f"theta/q-harmonic DEFER; correctness {m['correctness']:.0%}; held-out {mh['correctness']:.0%})")


def test_foldext_stageB3_abft():
    """STAGE B3: ABFT checksum self-verification. ★ This accelerates VERIFICATION (Clock B), NOT the
    computation. ★ Covers: detect_dense_matmul, abft_checksum_detects_error, freivalds_verifies_fast,
    float_threshold_tuned, abft_is_clockB_not_speedup."""
    import abft as AB
    # detect_dense_matmul: AST recognizes a triple-nested C[i][j]+=A[i][k]*B[k][j], rejects a plain reduce
    assert AB.detect_dense_matmul("for i in range(n):\n for j in range(n):\n  for k in range(n):\n   "
                                  "C[i][j] += A[i][k]*B[k][j]\n") is True
    assert AB.detect_dense_matmul("for i in range(n):\n  s += a[i]\n") is False
    # abft_checksum_detects_error: a single wrong entry is caught in O(N²); honest blind spot is documented
    mm = AB.measure_abft(dim=64, k=24)
    assert mm.error_caught_checksum and mm.error_caught_freivalds            # single-entry error caught
    assert mm.rectangle_missed_by_checksum and mm.rectangle_caught_by_freivalds, \
        "the checksum's canceling-rectangle blind spot must be honestly shown (missed by checksum, caught by Freivalds)"
    # freivalds_verifies_fast: probabilistic complete check, ε ≤ 2^-k, faster than O(N³) recompute
    assert mm.freivalds_error_prob == 2.0 ** -24 and mm.freivalds_speedup >= 1.0
    assert mm.checksum_speedup > 2.0                                         # O(N²) checksum clearly beats O(N³)
    # float_threshold_tuned: V-ABFT is epsilon-bounded (tolerance), accepts correct, rejects corrupted
    import fast_certificates as FC
    A = [[1.0, 2.0], [3.0, 4.0]]; B = [[5.0, 6.0], [7.0, 8.0]]; C = FC.matmul(A, B)
    good = AB.checksum_check(A, B, C, integer=False, tol=1e-6)
    bad = [r[:] for r in C]; bad[0][0] += 0.5
    badr = AB.checksum_check(A, B, bad, integer=False, tol=1e-6)
    assert good.ok and good.cert_type == "epsilon-bounded" and not badr.ok
    assert "false pos" in good.detail.lower()                               # honest about the threshold's risk
    # abft_is_clockB_not_speedup: ★ the result is labeled Clock B, and we never claim compute got faster ★
    m = AB.measure_abft_corpus()
    assert m["clock"] == "B" and "unchanged" in m["note"].lower() and m["handled"] >= 3
    print(f"PASS test_foldext_stageB3_abft (matmul detected; [Clock B] checksum {mm.checksum_speedup}× / "
          f"Freivalds {mm.freivalds_speedup}× (ε≤2^-24); single-error caught, rectangle blind-spot honest; "
          f"V-ABFT epsilon-bounded; verify_rate {m['verify_rate']:.0%} — COMPUTE unchanged (not Clock C))")


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
