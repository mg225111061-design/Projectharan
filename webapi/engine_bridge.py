"""
webapi/engine_bridge.py — the bridge from the web API to the REAL pillar3 engine.
=================================================================================
Every number this returns is produced by the actual engine (pillar3.engine / canonical / corpus_runner /
studio_gen / mode / provider) — measured whole-program, carrying its hotspot fraction and Amdahl ceiling,
graded by the real ADT, ratio ≤ ceiling by construction. No hand-written numbers, no invented wins.

For a user's PASTED code we do REAL AST detection of waste patterns in their source, then report the engine's
REAL measured result for each detected waste class (run under the selected ModePolicy). We never auto-rewrite
arbitrary user code (that needs the LLM proposer + a key; the verifier still arbitrates), so the measured rows
are honestly labelled as the engine's verified result for the detected waste class on a representative workload.
"""
from __future__ import annotations

import ast
import json as _json
import os
import sys
import urllib.error as _urlerr
import urllib.parse as _urlparse
import urllib.request as _urlreq
from typing import Dict, List, Optional, Tuple

# make the repo root importable (webapi/ lives under it)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import provider as PRV
from pillar3 import canonical as C
from pillar3 import corpus_runner as CR
from pillar3 import engine as E
from pillar3.mode import Mode, ModePolicy
import mode_budget as MB
import pillar3_studio_gen as STUDIO
from corpus import ai_todo_app, log_analyzer, csv_stats, template_render, json_pipeline


# ── AST waste detection on the user's PASTED source (real; no exec) ────────────────────────────────────
_FETCH = ("fetch", "get", "query", "load", "find", "select", "read", "lookup")


def detect_in_source(src: str) -> List[Dict]:
    """Walk the user's source AST and report waste patterns actually present (mapped to the engine's vocabulary).
    Pure AST — the pasted code is never executed."""
    found: List[Dict] = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"waste_type": "syntax_error", "evidence": f"could not parse: {e}", "line": getattr(e, "lineno", 0)}]

    def add(wt, ev, line):
        if not any(f["waste_type"] == wt for f in found):
            found.append({"waste_type": wt, "evidence": ev, "line": line})

    list_names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, (ast.List, ast.ListComp)):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    list_names.add(t.id)
    for n in ast.walk(tree):
        if isinstance(n, (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            for s in ast.walk(n):
                if isinstance(s, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in s.ops):
                    c = s.comparators[0]
                    if isinstance(c, ast.Name) and c.id in list_names:
                        add("list_as_set", f"`x in {c.id}` (a list) inside a loop → O(n) membership",
                            getattr(s, "lineno", 0))
                if isinstance(s, ast.Call):
                    nm = (s.func.attr if isinstance(s.func, ast.Attribute)
                          else s.func.id if isinstance(s.func, ast.Name) else "")
                    low = nm.lower()
                    if any(low.startswith(p) or low.endswith(p) or ("_" + p) in low for p in _FETCH) and nm not in ("get",):
                        add("n_plus_1", f"`{nm}(...)` (a per-item fetch) inside a loop → N+1", getattr(s, "lineno", 0))
                if isinstance(s, ast.Assign) and isinstance(s.value, ast.BinOp) and isinstance(s.value.op, ast.Add) \
                        and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name):
                    tgt = s.targets[0].id
                    if tgt in {x.id for x in ast.walk(s.value) if isinstance(x, ast.Name)}:
                        add("accidental_quadratic", f"`{tgt} = {tgt} + …` inside a loop → O(n²) build",
                            getattr(s, "lineno", 0))
                if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute) and s.func.attr == "count":
                    add("accidental_quadratic", "`.count()` inside a loop → O(n²)", getattr(s, "lineno", 0))
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow) and isinstance(n.right, ast.Constant) \
                and isinstance(n.right.value, int) and 2 <= n.right.value <= 4:
            add("algo_replace", f"`x ** {n.right.value}` → strength-reducible", getattr(n, "lineno", 0))
        # nested pure-arithmetic loop with math.* → vectorizable / algorithmic
        if isinstance(n, (ast.ListComp, ast.GeneratorExp, ast.For)):
            if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                   and c.func.attr in ("sin", "cos", "sqrt", "exp", "log") for c in ast.walk(n)):
                add("simd_offload", "scalar math.* over each element → SIMD/vectorizable", getattr(n, "lineno", 0))
    return found


# ── map detected waste → the engine's runnable demo (canonical candidates carry real slow/fast pairs) ───
def _canonical_by_waste() -> Dict[str, "E.Candidate"]:
    return {c.waste_type: c for c in C.build_candidates()}


def _proposer_block(provider: Optional[str], model: Optional[str], key: Optional[str],
                    detected: List[Dict], mode: Mode) -> Dict:
    """Route to the chosen LLM proposer when a key is given (a REAL provider call), else the deterministic
    structural detectors. The proposer is NEVER the arbiter: even a live LLM proposal is not auto-applied
    (Rule 6 — arbitrary LLM code isn't executed here), so the MEASURED, applied result is always the
    verifier-arbitrated structural fix. The key is header-only and never logged."""
    if not key or not provider or provider not in PRV.VALID_PROVIDERS:
        return {"used": False, "mode": "deterministic",
                "note": "LLM 키 없음 — 결정론적 구조 디텍터(측정·적용 경로)로 실행합니다. "
                        "무료 Groq/Gemini 키를 넣으면 LLM 재작성 제안도 받을 수 있습니다."}
    waste = detected[0]["waste_type"] if detected else "general hotspot"
    mdl = (model or "").strip() or PRV.default_model_for(provider)
    prompt = (f"Optimize this Python for the waste pattern `{waste}` while preserving behavior. "
              f"Return only the faster function. Mode: {mode.value}.")
    kind, url, headers, body = _provider_request(provider, mdl, key, prompt, 256)
    status, text = _http_post(url, headers, body)
    if status == 200:
        snippet = _extract_text(kind, text)[:280]
        return {"used": True, "live": True, "provider": provider, "model": mdl, "transport": kind,
                "status": "llm-consulted", "applied": "verifier-arbitrated structural fix",
                "rationale": snippet,
                "note": ("LLM이 재작성을 제안했습니다. Rule 6에 따라 LLM이 내놓은 코드는 여기서 자동 실행되지 않으므로, "
                         "아래 출하된 행은 검증기가 판정한 구조적 수정입니다 (제안자 ≠ 심판).")}
    cls = _classify(provider, kind, mdl, status, text)
    reason = "이 샌드박스에서 송신(egress) 차단됨" if cls.get("blocked") else "키 거부됨/연결 불가"
    return {"used": False, "live": cls.get("live", False), "provider": provider, "model": mdl, "transport": kind,
            "status": "llm-unavailable", "detail": cls["detail"],
            "note": f"LLM 제안자: {reason}; 결정론적 구조 디텍터(측정 경로)로 폴백했습니다."}


def _extract_text(kind: str, text: str) -> str:
    """Best-effort pull of the model's reply text from a provider response (never raises)."""
    try:
        d = _json.loads(text)
        if kind == "gemini_generate":
            return d["candidates"][0]["content"]["parts"][0].get("text", "").strip()
        if kind == "openai_chat":
            return d["choices"][0]["message"].get("content", "").strip()
        return "".join(b.get("text", "") for b in d.get("content", [])).strip()   # anthropic
    except Exception:                                                              # noqa: BLE001
        return "(model replied; could not parse a text snippet)"


def run_optimize(code: str, mode: str, provider: Optional[str] = None, model: Optional[str] = None,
                 key: Optional[str] = None) -> Dict:
    """Detect waste in the user's code (real), optionally consult the chosen LLM proposer (real provider call
    when a key is given), then run the REAL engine under the selected mode and return measured verification rows.
    The verifier arbitrates; the LLM never decides. Invalid/missing key ⇒ honest deterministic fallback."""
    m = Mode(mode) if mode in (x.value for x in Mode) else Mode.NORMAL
    detected = detect_in_source(code)
    det_types = {d["waste_type"] for d in detected}
    proposer = _proposer_block(provider, model, key, detected, m)
    collapse = _loop_collapse(code)                            # §2/§4: PROVEN collapse (decide-only, fork-safe)

    # the canonical candidates whose waste class was detected in the user's code (engine vocabulary)
    cands = [c for c in C.build_candidates() if c.waste_type in det_types]
    if not cands:
        # nothing the engine recognises — a dignified, honest empty result (not an error)
        return {
            "mode": m.value, "detected": detected, "shipped": [], "declined": [],
            "cumulative_ratio": 1.0, "z3_calls": 0, "ran_complexity_sweep": False, "proposer": proposer,
            "budget": _budget_info(m, 0.0, "WITHIN_BUDGET"), "collapse": collapse,
            "note": ("이 엔진이 검증된 수정을 가진 알려진 낭비 패턴을 붙여넣은 코드에서 찾지 못했습니다 — "
                     "안전하게 출하할 게 없습니다. (탐지는 당신 소스에 대한 진짜 AST 분석입니다.)"),
            "policy": _mode_contract(m),
        }
    # ★ §1: run the REAL engine UNDER the mode's ENFORCED wall-clock budget (fast ~1s / normal ~30s / extend
    # ~8min BOUNDED). The hard watchdog (mode_budget → latency_budget.run_with_budget, daemon thread) means the
    # call never hangs past budget; on overrun we return the best CERTIFIED result reached, never a faked one. ★
    def _work(budget, partial):
        rep = E.optimize(cands, C.make_input, mode=m, n=1, residual=C.residual, sweep_fn=C.sweep_fn)
        partial.offer(rep, "shipped")          # the engine closed; each shipped row is individually certified
        return rep
    run = MB.run_under_mode_budget(m, _work)
    rep = run.result                            # None only if the engine was abandoned at the budget (no fake)
    if run.deferred and rep is None:
        return {
            "mode": m.value, "detected": detected, "shipped": [], "declined": [], "cumulative_ratio": 1.0,
            "z3_calls": 0, "ran_complexity_sweep": False, "latency_ms": round(run.elapsed_s * 1e3, 1),
            "proposer": proposer, "budget": _budget_info(m, run.elapsed_s, run.status), "collapse": collapse,
            "note": ("{} 예산(~{:.0f}s) 안에 닫지 못했습니다 — 정직한 부분 결과입니다 (시간을 채우려고 결과를 위조하지 "
                     "않고, 빨리 가려고 등급을 낮추지도 않습니다). 더 깊은 티어로 올리거나 다시 시도하세요.").format(
                m.value, MB.budget_for_mode(m)),
            "policy": _mode_contract(m),
        }
    return {
        "mode": m.value,
        "detected": detected,
        "shipped": [_row(s) for s in rep.shipped],
        "declined": [{"name": d.name, "waste_type": d.waste_type, "reason": d.reason} for d in rep.declined],
        "cumulative_ratio": round(rep.fresh_cumulative_ratio, 3),
        "z3_calls": rep.z3_calls,
        "ran_complexity_sweep": rep.ran_complexity_sweep,
        "latency_ms": round(rep.latency_s * 1e3, 1),
        "proposer": proposer,
        "budget": _budget_info(m, run.elapsed_s, run.status),
        "collapse": collapse,
        "note": ("{} 계약 아래 전체 프로그램을 ~{:.0f}s 예산 안에서 실측했습니다. 탐지는 당신 코드에 대한 진짜 AST "
                 "분석이며, 측정된 행은 탐지된 각 낭비 유형에 대해 대표 워크로드에서 엔진이 검증한 결과입니다. "
                 "LLM은(키가 설정된 경우) 제안만 하고, 판정은 검증기가 합니다.").format(m.value, MB.budget_for_mode(m)),
        "policy": _mode_contract(m),
    }


def _row(s) -> Dict:
    import math
    return {
        "name": s.name, "waste_type": s.waste_type, "grade": s.grade.lower(),
        "ratio": math.floor(s.ratio * 1000) / 1000,
        "ceiling": (math.ceil(s.ceiling * 100) / 100 if s.ceiling != float("inf") else None),
        "hotspot_fraction": round(s.hotspot_fraction, 3),
    }


def _mode_contract(m: Mode) -> Dict:
    p = ModePolicy.for_mode(m)
    return {
        "mode": m.value, "primary_clock": p.primary_clock, "verifier_tier": p.verifier_tier.name,
        "detectors": len(p.enabled_detectors), "acceptable_grades": sorted(g.lower() for g in p.acceptable_grades),
        "max_hotspots": p.max_hotspots, "runs_complexity_sweep": p.runs_complexity_sweep,
        "latency_budget_s": p.latency_budget_s, "risk_posture": p.risk_posture, "stop_condition": p.stop_condition,
    }


def _budget_info(m: Mode, elapsed_s: float, status: str) -> Dict:
    """The ENFORCED tier+budget this run executed under — the live line the UI (§3) renders ('extend · 0:03 /
    8:00'). extend is BOUNDED ~8 min, never unlimited; `status` is WITHIN_BUDGET or DEFERRED_PARTIAL (honest)."""
    b = MB.budget_for_mode(m)

    def _fmt(sec: float) -> str:
        sec = int(max(0.0, sec))
        return f"{sec // 60}:{sec % 60:02d}"

    return {
        "tier": m.value, "budget_s": b, "elapsed_s": round(elapsed_s, 3), "status": status, "bounded": True,
        "label": MB.tier_label(m), "display": f"{m.value} · {_fmt(elapsed_s)} / {_fmt(b)}",
    }


def _loop_collapse(code: str) -> Optional[Dict]:
    """The PROVEN algorithmic collapse for an accumulation/recurrence loop in the user's code, if any — the §2/§4
    decision the canonical-fix engine does NOT cover: a Σ-loop → O(1) closed form (or a PROVEN-irreducible loop),
    or a C-finite state-update loop → O(log n) companion form. None when no collapse is proven (honest — never a
    fabricated one). Each carries its grade + certificate, sound/conservative.

    ★ DECIDE-ONLY (synchronous, fork-safe) ★: this DECIDES the collapse (sample → fit → held-out verify) WITHOUT
    timing the user's loop — so it is fast and spawns NO threads (timing under a daemon-thread watchdog could leave
    a thread alive and deadlock a later multiprocessing.fork). The MEASURED ratio is shown in the live trace (§3),
    a single deliberate step — not here, where this runs on every optimize call. Soundness is unchanged: the
    held-out companion≡loop verification gate is kept."""
    try:
        import structure_recognizer as SR                      # noqa: PLC0415
        d = SR.decide_loop(code)
        if d is not None and d.status == "CLOSED_FORM":
            return {"kind": "sum", "status": "CLOSED_FORM", "closed_form": d.closed_form,
                    "complexity": "O(n) → O(1)", "grade": d.verdict.status, "certificate": d.certificate}
        if d is not None and d.status == "NO_CLOSED_FORM":
            return {"kind": "sum", "status": "NO_CLOSED_FORM", "complexity": "irreducible (proven)",
                    "grade": d.verdict.status, "certificate": d.certificate}
        if d is None:                                          # not a single Σ for-loop (Gosper) → other collapses
            fn = SR._first_fn(code, None)                      # decide-only; the recognizer gates are BOUNDED (no hang)
            nst = SR._nested_acc(fn) if fn is not None else None
            if nst is not None:                                # a RECOGNIZED double-nested accumulation
                nd = SR._offload_nested(code, fn, nst)
                if nd.status == "OFFLOADED":                   # CAS-proposed + differential-equivalence gated (honest)
                    return {"kind": "nested_sum", "status": "CLOSED_FORM", "closed_form": nd.closed_form,
                            "complexity": nd.complexity.replace("O(1) (was ", "").rstrip(")") + " → O(1)",
                            "grade": "EXACT", "certificate": nd.certificate}
                # Recognized as nested but did NOT collapse ⇒ honest NONE. Do NOT fall through to the recurrence
                # detector: a double-nested accumulation is never a single-state C-finite recurrence, and the
                # recurrence detector SAMPLES the loop by executing it — for an explosive inner bound (e.g.
                # range(1, 2**i)) that would run an unbounded loop and hang. (Sound + no-hang.)
                return None
            # OTHER fold-shaped loops → an O(1) closed form (BETTER than the O(log n) recurrence form): a counter-
            # `while`, a sum/prod comprehension, a linear self-recursion, a functools.reduce fold, or a modular-
            # FILTERED sum. The recognizer is synchronous + fork-safe, its gate is BOUNDED (no hang), it rejects
            # non-structured code in <1ms, and it is gate-verified EXACT like the recurrence collapse. Tried BEFORE
            # the recurrence detector so a polynomial sum (which IS C-finite) surfaces as O(1), not O(log n).
            sd = SR.dispatch(code)
            if sd.status == "OFFLOADED" and sd.closed_form:
                return {"kind": "code_shape", "status": "CLOSED_FORM", "closed_form": sd.closed_form,
                        "complexity": (sd.complexity or "O(1)"), "grade": "EXACT", "certificate": sd.certificate}
            # a genuine state-update recurrence loop (Fibonacci-like — dispatch can't fold it) → O(log n) companion
            import loop_recurrence as LR                       # noqa: PLC0415
            rc = LR.decide_recurrence_collapse(code, measure=False)       # decide-only: fast, no timing, no threads
            if rc.status == "COLLAPSED":
                return {"kind": "recurrence", "status": "COLLAPSED", "order": rc.order, "c": rc.c,
                        "complexity": "O(n) → O(log n)", "grade": rc.verdict.status,
                        "certificate": rc.verdict.certificate.detail}
            mc = LR.decide_modular_recurrence_collapse(code, measure=False)  # the genuine-win modular case
            if mc.status == "COLLAPSED":
                return {"kind": "modular_recurrence", "status": "COLLAPSED", "order": mc.order, "c": mc.c,
                        "complexity": "O(n) → O(log n) (mod M)", "grade": mc.verdict.status,
                        "certificate": mc.verdict.certificate.detail}
    except Exception:                                          # noqa: BLE001 — analysis must never break the response
        return None
    return None


def dispatch_engines(code: str, lang: str = "python") -> Optional[Dict]:
    """§BK — reach the full engine TIER from production: route `code` to its engine (freivalds proposer-verifier /
    chc_solve·ic3_pdr loop-safety / extract catalog / the §BJ structure→engine dispatcher) via the central
    `webapi.engine_dispatch`, with the §BK whole-pipeline FoldCache (Clock B → 0 on a warm hit). ★ ADDITIVE +
    GUARDED: any failure ⇒ None, never breaks the /api/optimize response; every disposition is the engine's own
    gated grade (Freivalds PROBABILISTIC, chc independent re-verify) — wiring preserves verification, never bypasses
    it. The live end-to-end run is author-validated on Render (sandbox blocks the server)."""
    try:
        from webapi import engine_dispatch as ED                # noqa: PLC0415
    except Exception:                                          # noqa: BLE001 — robust to a flat load path
        try:
            import engine_dispatch as ED                        # type: ignore  # noqa: PLC0415
        except Exception:                                      # noqa: BLE001
            return None
    try:
        return ED.dispatch(code, lang)
    except Exception:                                          # noqa: BLE001
        return None


def engines_reached() -> Dict:
    """§BK production-reach meter: how many of the previously-unwired engines the dispatcher now reaches (gap → 0).
    Surfaceable on a /health route; honest about any engine that fails to reach."""
    try:
        from webapi import engine_dispatch as ED                # noqa: PLC0415
        return ED.production_reach()
    except Exception as e:                                      # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}", "gap_remaining": None}


def modes() -> List[Dict]:
    return [_mode_contract(m) for m in (Mode.FAST, Mode.NORMAL, Mode.EXTEND)]


_PROVIDER_LABELS = {"anthropic": "Claude (official)", "anthropic_compat": "Claude-compatible gateway",
                    "openai": "ChatGPT (OpenAI)", "openai_compat": "OpenAI-compatible gateway",
                    "gemini": "Gemini (Google)", "groq": "Groq", "mistral": "Mistral", "cohere": "Cohere",
                    "deepseek": "DeepSeek", "xai": "Grok (xAI)", "together": "Together AI",
                    "fireworks": "Fireworks AI", "openrouter": "OpenRouter", "perplexity": "Perplexity"}
_PROVIDER_KEYVAR = {"anthropic": "ANTHROPIC_API_KEY", "anthropic_compat": "ANTHROPIC_API_KEY",
                    "openai": "OPENAI_API_KEY", "openai_compat": "OPENAI_API_KEY",
                    "gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY", "mistral": "MISTRAL_API_KEY",
                    "cohere": "COHERE_API_KEY", "deepseek": "DEEPSEEK_API_KEY", "xai": "XAI_API_KEY",
                    "together": "TOGETHER_API_KEY", "fireworks": "FIREWORKS_API_KEY",
                    "openrouter": "OPENROUTER_API_KEY", "perplexity": "PERPLEXITY_API_KEY"}
_KEY_LABELS = {"gemini": "Google AI Studio API key", "groq": "Groq API key",
               "openai": "OpenAI API key", "anthropic": "Anthropic API key", "xai": "xAI API key",
               "mistral": "Mistral API key", "cohere": "Cohere API key", "deepseek": "DeepSeek API key",
               "together": "Together API key", "fireworks": "Fireworks API key",
               "openrouter": "OpenRouter API key", "perplexity": "Perplexity API key"}


def providers() -> List[Dict]:
    """Every provider with the UI metadata: transport, default model, free-no-card flag, key field label, and a
    'where to get a key' link. Groq + Gemini are free with no credit card — the default way to test the site."""
    out: List[Dict] = []
    for p in PRV.VALID_PROVIDERS:
        out.append({
            "id": p, "label": _PROVIDER_LABELS.get(p, p), "transport": PRV.transport_kind(p),
            "key_env": _PROVIDER_KEYVAR.get(p, "HARAN_KEY"),
            "default_model": PRV.default_model_for(p),
            "free_no_card": PRV.is_free_no_card(p),
            "key_label": _KEY_LABELS.get(p, _PROVIDER_LABELS.get(p, p) + " API key"),
            "get_key_url": PRV.get_key_url(p),
        })
    # surface the free, no-card providers first (the recommended way in)
    out.sort(key=lambda d: (not d["free_no_card"], d["id"]))
    return out


def corpus() -> Dict:
    repos = [
        CR.CorpusRepo("ai_todo_app", ai_todo_app.ARCHETYPE, ai_todo_app, exact_justification=ai_todo_app.EXACT_JUSTIFICATION),
        CR.CorpusRepo("log_analyzer", log_analyzer.ARCHETYPE, log_analyzer),
        CR.CorpusRepo("csv_stats", csv_stats.ARCHETYPE, csv_stats),
        CR.CorpusRepo("json_pipeline", json_pipeline.ARCHETYPE, json_pipeline, exact_justification=json_pipeline.EXACT_JUSTIFICATION),
        CR.CorpusRepo("template_render", template_render.ARCHETYPE, template_render),
    ]
    rep = CR.run_corpus(repos)
    grades = {g: sum(1 for r in rep.rows if r.grade.lower() == g) for g in ("exact", "probabilistic", "decline")}
    return {
        "rows": [{"name": r.name, "archetype": r.archetype, "detected": r.detected, "grade": r.grade.lower(),
                  "ratio": r.ratio, "ceiling": r.ceiling, "hotspot_fraction": r.hotspot_fraction, "note": r.note}
                 for r in rep.rows],
        "grades": grades, "found_nothing": rep.found_nothing(),
    }


def demo() -> Dict:
    """Real per-mode canonical runs + panel rows (reuses the studio_gen real-data generator)."""
    return STUDIO.build()


# ── live provider HTTP (real calls; the key is ONLY ever a request header, never logged/stored/returned) ─
def _provider_request(provider_id: str, model: str, key: str, prompt: str,
                      max_tokens: int) -> "Tuple[str, str, Dict[str, str], Dict]":
    """Single-source the wire shape for every provider (validate + proposer share it). Returns
    (transport_kind, url, headers, json_body). The key lives ONLY in `headers` — callers must never log it."""
    kind = PRV.transport_kind(provider_id)
    base = (PRV.base_url(provider_id) or "").rstrip("/")
    if kind == "gemini_generate":                                       # native Gemini (confirmed reachable)
        return (kind, f"{base}/models/{model}:generateContent",
                {"x-goog-api-key": key, "Content-Type": "application/json"},
                {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": max_tokens}})
    if kind == "openai_chat":                                           # groq + openai + openai_compat gateways
        return (kind, f"{base}/chat/completions",
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens})
    return ("anthropic_sdk", (base or "https://api.anthropic.com") + "/v1/messages",   # raw Anthropic Messages
            {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]})


def _http_post(url: str, headers: Dict[str, str], body: Dict, timeout: float = 12.0) -> "Tuple[Optional[int], str]":
    """POST JSON and return (status, body_text). Only the status + provider response body come back — never the
    request headers (which hold the key). Network/egress failures return (None, reason)."""
    data = _json.dumps(body).encode("utf-8")
    req = _urlreq.Request(url, data=data, headers=headers, method="POST")
    try:
        with _urlreq.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except _urlerr.HTTPError as e:                                      # 4xx/5xx incl. egress-allowlist 403
        try:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception:                                              # noqa: BLE001
            return e.code, ""
    except Exception as e:                                             # noqa: BLE001 — DNS/timeout/egress block
        return None, f"{type(e).__name__}: {e}"


_INVALID_MARKERS = ("api_key_invalid", "api key not valid", "invalid api key", "invalid_api_key",
                    "incorrect api key", "unauthorized", "invalid authentication", "permission_denied",
                    "invalid x-api-key", "authentication_error")


def _classify(provider_id: str, kind: str, model: str, status: "Optional[int]", text: str) -> Dict:
    """Honest classification of a live provider response → an author-ACTIONABLE hint. Never echoes the key.
    ★ The crucial distinctions (directive §4): 401=key, 403=permission, 404=MODEL-name (NOT key), 429=quota,
    network=base_url. So a fake/typo'd model id (404) is never misread as a key problem. Also distinguishes a
    genuine round-trip from this sandbox's egress block."""
    low = (text or "").lower()
    host = _urlparse.urlparse(_provider_request(provider_id, model, "x", "x", 1)[1]).hostname or provider_id
    get_url = PRV.get_key_url(provider_id)
    base = {"transport": kind, "model": model, "provider": provider_id, "key_in_headers_only": True}

    def out(ok, error_class, hint, *, live=True, blocked=False):
        return {**base, "ok": ok, "live": live, "blocked": blocked, "error_class": error_class,
                "status": status, "hint": hint, "detail": hint}

    if status == 200:
        return out(True, "ok", f"key valid — live {provider_id} call returned 200.")
    if status is None or "allowlist" in low:                            # egress blocked (sandbox) or network down
        return out(False, "network", f"network/base_url 오류 — {host} 에 닿지 못함 (this sandbox egress-blocks {host}; "
                   f"on Render add it to the allowlist). base_url 확인. [UNVERIFIED: "
                   f"{'no network response' if status is None else status}]", live=False, blocked=True)
    if status == 401:
        return out(False, "key", f"401 — 키가 틀렸거나 만료. {provider_id} 콘솔에서 재발급. (invalid/expired API key). "
                   f"Get a key: {get_url}")
    if status == 403:
        # 403 can be a rejected key OR a valid key lacking API access — disambiguate by the body markers.
        if any(s in low for s in _INVALID_MARKERS):
            return out(False, "key", f"403 — 키가 거부됨. {provider_id} 콘솔에서 키 확인/재발급. Get a key: {get_url}")
        return out(False, "permission", f"403 — 키는 맞으나 권한/지역 제한 또는 API 미활성. {provider_id} 콘솔에서 "
                   f"API 활성화·결제 확인. (key OK but API not enabled / region / billing).")
    if status == 404:
        return out(False, "model", f"404 — ★모델명 문제(키 아님). '{model}' 모델이 {provider_id} 에 없음 — 모델 칸을 "
                   f"콘솔의 실제 모델명으로 수정. (model not found on this provider; this is NOT a key error).")
    if status == 429:
        return out(False, "quota", f"429 — 무료 쿼터 소진 또는 rate-limit. 잠시 후 재시도 또는 결제. (quota/rate-limited).")
    if status == 400 and any(s in low for s in _INVALID_MARKERS):
        return out(False, "key", f"400 — 키 거부됨. 키 확인. Get a key: {get_url}")
    if status == 400:
        return out(False, "request", f"400 — 요청/모델 파라미터 문제(키 아님일 가능성). 모델명·요청 형식 확인. (bad request "
                   f"— likely the model id or a parameter, not the key).")
    return out(False, "unknown", f"{provider_id} returned HTTP {status} — 응답이 auth-OK가 아님. 모델명·키·base_url 점검.")


def validate_key(provider_id: str, key: str, model: Optional[str] = None) -> Dict:
    """Make a REAL tiny (1-token) test call to the chosen provider with the pasted key and report ok/fail.
    The key is placed ONLY in the request header — never logged, never written to disk, never persisted. With a
    real key + reachable host this is a genuine live validation (e.g. Gemini); when the host is egress-blocked we
    say so honestly rather than faking a pass."""
    if provider_id not in PRV.VALID_PROVIDERS:
        return {"ok": False, "detail": f"unknown provider: {provider_id}"}
    if not key:
        return {"ok": False, "detail": "no key provided", "get_key_url": PRV.get_key_url(provider_id)}
    mdl = (model or "").strip() or PRV.default_model_for(provider_id)
    kind, url, headers, body = _provider_request(provider_id, mdl, key, "ping", 1)
    status, text = _http_post(url, headers, body)
    out = _classify(provider_id, kind, mdl, status, text)
    out["get_key_url"] = PRV.get_key_url(provider_id)
    return out


def _mask_key(k: "Optional[str]") -> str:
    """Mask a key for safe diagnostics — show only a short non-secret prefix (e.g. 'AIza***', 'gsk_***'). NEVER
    the full key. Returns '' for an absent key."""
    if not k:
        return ""
    s = str(k)
    return (s[:4] + "***") if len(s) > 4 else "***"


def health_provider(provider: Optional[str] = None, model: Optional[str] = None,
                    key: Optional[str] = None) -> Dict:
    """`/health/provider` diagnostic (directive §3.2): read the chosen provider/family/base_url/model (env config
    by default — HARAN_PROVIDER/HARAN_MODEL/HARAN_BASE_URL/HARAN_KEY), MASK the key, and, when a key is present,
    make ONE tiny 'ping' on the provider's correct auth family. Returns a key-SAFE JSON shape (key_present +
    key_masked only — the key is NEVER echoed/logged/stored) with an author-actionable hint (401 key / 403
    permission / 404 model / 429 quota / network). Honest: in this sandbox most hosts are egress-blocked, so
    live_call='fail'/error_class='network' is expected here; the author runs it for real on Render."""
    prov = (provider or PRV.provider_name())
    if prov not in PRV.VALID_PROVIDERS:
        return {"ok": False, "provider": prov, "error_class": "unknown",
                "hint": f"unknown provider '{prov}' — pick one of {list(PRV.VALID_PROVIDERS)}"}
    mdl = (model or "").strip() or PRV.default_model_for(prov)
    k = key or PRV.resolve_key_for(prov)                      # env fallback (HARAN_KEY/vendor); used once, dropped
    fam = PRV.transport_kind(prov)
    res = {"provider": prov, "family": fam, "base_url": PRV.base_url(prov), "model": mdl,
           "key_present": bool(k), "key_masked": _mask_key(k)}
    if not k:
        res.update({"ok": False, "live_call": "no_key", "error_class": "key", "status": None,
                    "hint": "키 없음 — Render 환경변수 HARAN_KEY 설정 또는 UI 세션 키 입력 (no key: set HARAN_KEY on "
                            "Render, or paste a session key in the UI).", "get_key_url": PRV.get_key_url(prov)})
        return res
    kind, url, headers, body = _provider_request(prov, mdl, k, "ping", 1)
    status, text = _http_post(url, headers, body)
    cls = _classify(prov, kind, mdl, status, text)
    res.update({"ok": cls["ok"], "live_call": "ok" if cls["ok"] else "fail", "status": status,
                "error_class": cls.get("error_class"), "hint": cls.get("hint"),
                "get_key_url": PRV.get_key_url(prov),
                "sample": _extract_text(kind, text)[:160] if status == 200 else ""})
    return res                                               # k goes out of scope here — never stored/returned
