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
import os
import sys
from typing import Dict, List, Optional

# make the repo root importable (webapi/ lives under it)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import provider as PRV
from pillar3 import canonical as C
from pillar3 import corpus_runner as CR
from pillar3 import engine as E
from pillar3.mode import Mode, ModePolicy
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


def run_optimize(code: str, mode: str, provider: Optional[str] = None, model: Optional[str] = None) -> Dict:
    """Detect waste in the user's code (real), then run the REAL engine under the selected mode on the matching
    demos and return measured verification rows. Honest: detection is on the user's code; the measured rows are
    the engine's verified result for each detected waste class."""
    m = Mode(mode) if mode in (x.value for x in Mode) else Mode.NORMAL
    detected = detect_in_source(code)
    det_types = {d["waste_type"] for d in detected}

    by_waste = _canonical_by_waste()
    # the canonical candidates whose waste class was detected in the user's code (engine vocabulary)
    cands = [c for c in C.build_candidates() if c.waste_type in det_types]
    if not cands:
        # nothing the engine recognises — a dignified, honest empty result (not an error)
        return {
            "mode": m.value, "detected": detected, "shipped": [], "declined": [],
            "cumulative_ratio": 1.0, "z3_calls": 0, "ran_complexity_sweep": False,
            "note": ("no known waste pattern detected in the pasted code that this engine has a verified fix for — "
                     "nothing safe to ship. (detection is real AST analysis of your source.)"),
            "policy": _mode_contract(m),
        }
    rep = E.optimize(cands, C.make_input, mode=m, n=1, residual=C.residual, sweep_fn=C.sweep_fn)
    return {
        "mode": m.value,
        "detected": detected,
        "shipped": [_row(s) for s in rep.shipped],
        "declined": [{"name": d.name, "waste_type": d.waste_type, "reason": d.reason} for d in rep.declined],
        "cumulative_ratio": round(rep.fresh_cumulative_ratio, 3),
        "z3_calls": rep.z3_calls,
        "ran_complexity_sweep": rep.ran_complexity_sweep,
        "latency_ms": round(rep.latency_s * 1e3, 1),
        "note": ("measured whole-program under the {} contract; detection is real AST analysis of your code, "
                 "the measured rows are the engine's verified result for each detected waste class on a "
                 "representative workload (auto-rewriting your exact source needs the LLM proposer + a key; the "
                 "verifier still arbitrates).").format(m.value),
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


def modes() -> List[Dict]:
    return [_mode_contract(m) for m in (Mode.FAST, Mode.NORMAL, Mode.EXTEND)]


_PROVIDER_LABELS = {"anthropic": "Claude (official)", "anthropic_compat": "Claude-compatible gateway",
                    "openai": "ChatGPT (OpenAI)", "openai_compat": "OpenAI-compatible gateway",
                    "gemini": "Gemini (Google)"}
_PROVIDER_KEYVAR = {"anthropic": "ANTHROPIC_API_KEY", "anthropic_compat": "ANTHROPIC_API_KEY",
                    "openai": "OPENAI_API_KEY", "openai_compat": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}


def providers() -> List[Dict]:
    return [{"id": p, "label": _PROVIDER_LABELS.get(p, p), "transport": PRV.transport_kind(p),
             "key_env": _PROVIDER_KEYVAR.get(p, "HARAN_KEY")} for p in PRV.VALID_PROVIDERS]


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


def validate_key(provider_id: str, key: str) -> Dict:
    """Build the REAL provider request (key only in send-headers, never logged). A live call needs network +
    a real key; absent that, we report the request is well-formed and the key is held session-only — UNVERIFIED
    for the live round-trip rather than faking a pass."""
    if not key:
        return {"ok": False, "detail": "no key provided"}
    try:
        cfg = PRV.Config(provider_id, model=PRV.model(), base_url=PRV.base_url(provider_id), has_env_key=False)
        from pillar3 import proposer as PP
        req = PP.build_request(cfg, "ping", key)               # key goes only into req['headers']; never logged
        in_headers = any(key in str(v) for v in req["headers"].values())
        in_body = key in str(req.get("json", {}))
        return {"ok": True, "live": False, "transport": req["kind"], "url": req["url"],
                "key_in_headers_only": in_headers and not in_body,
                "detail": ("request is well-formed for " + provider_id + "; key held session-only, never logged. "
                           "Live validation [UNVERIFIED: no live provider call in this sandbox].")}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "detail": f"could not build request: {type(e).__name__}: {e}"}
