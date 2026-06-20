"""
PHASE U — MR.JEFFREY Studio data generator (REAL engine output; mode contracts + providers + a live run).
==========================================================================================================
Serialises everything the studio UI binds to, all from the real engine: the three mode CONTRACTS (straight
from ModePolicy), the five PROVIDERS (from provider.py), a real canonical run through each mode (shipped /
declined / ratio / z3_calls / latency), and the verification-panel rows from the real corpus. No hand-edited
numbers. The API key is never part of this data — it is a session-only field in the browser.
"""
from __future__ import annotations

import json
import math
import os

import provider as PRV
from pillar3 import canonical as C
from pillar3 import corpus_runner as CR
from pillar3 import engine as E
from pillar3.mode import Mode, ModePolicy
from corpus import ai_todo_app, log_analyzer, csv_stats, template_render, json_pipeline


_PROVIDER_LABELS = {"anthropic": "Claude (official)", "anthropic_compat": "Claude-compatible gateway",
                    "openai": "ChatGPT (OpenAI)", "openai_compat": "OpenAI-compatible gateway",
                    "gemini": "Gemini (Google)"}


def _mode_contract(m: Mode) -> dict:
    p = ModePolicy.for_mode(m)
    return {
        "mode": m.value,
        "primary_clock": p.primary_clock,
        "verifier_tier": p.verifier_tier.name,
        "detectors": len(p.enabled_detectors),
        "acceptable_grades": sorted(p.acceptable_grades),
        "max_hotspots": p.max_hotspots,
        "runs_complexity_sweep": p.runs_complexity_sweep,
        "latency_budget_s": p.latency_budget_s,
        "risk_posture": p.risk_posture,
        "stop_condition": p.stop_condition,
    }


def _run(m: Mode) -> dict:
    cands = C.build_candidates()
    r = E.optimize(cands, C.make_input, mode=m, n=1, residual=C.residual, sweep_fn=C.sweep_fn)
    return {
        "mode": m.value,
        # round ratio DOWN and ceiling UP so the displayed ratio ≤ displayed ceiling by construction (the engine
        # already guarantees ratio ≤ ceiling; this keeps display rounding from inverting it on tight rows)
        "shipped": [{"name": s.name, "waste_type": s.waste_type, "grade": s.grade,
                     "ratio": math.floor(s.ratio * 1000) / 1000,
                     "ceiling": (math.ceil(s.ceiling * 100) / 100 if s.ceiling != float("inf") else "∞"),
                     "hotspot_fraction": round(s.hotspot_fraction, 3)} for s in r.shipped],
        "declined": [{"name": d.name, "reason": d.reason[:90]} for d in r.declined],
        "cumulative_ratio": round(r.fresh_cumulative_ratio, 3),
        "z3_calls": r.z3_calls,
        "latency_ms": round(r.latency_s * 1e3, 1),
        "ran_complexity_sweep": r.ran_complexity_sweep,
    }


def _panel_rows() -> list:
    repos = [
        CR.CorpusRepo("ai_todo_app", ai_todo_app.ARCHETYPE, ai_todo_app, exact_justification=ai_todo_app.EXACT_JUSTIFICATION),
        CR.CorpusRepo("log_analyzer", log_analyzer.ARCHETYPE, log_analyzer),
        CR.CorpusRepo("csv_stats", csv_stats.ARCHETYPE, csv_stats),
        CR.CorpusRepo("json_pipeline", json_pipeline.ARCHETYPE, json_pipeline, exact_justification=json_pipeline.EXACT_JUSTIFICATION),
        CR.CorpusRepo("template_render", template_render.ARCHETYPE, template_render),
    ]
    rep = CR.run_corpus(repos)
    return [{"name": r.name, "archetype": r.archetype, "detected": r.detected, "grade": r.grade,
             "ratio": r.ratio, "ceiling": r.ceiling, "hotspot_fraction": r.hotspot_fraction,
             "note": r.note} for r in rep.rows]


def build() -> dict:
    return {
        "engine": "MR.JEFFREY — the Whole-Program Verified Speedup Engine",
        "generated_by": "pillar3_studio_gen.py — real engine runs; no hand-edited numbers",
        "modes": [_mode_contract(m) for m in (Mode.FAST, Mode.NORMAL, Mode.EXTEND)],
        "providers": [{"id": p, "label": _PROVIDER_LABELS.get(p, p), "transport": PRV.transport_kind(p)}
                      for p in PRV.VALID_PROVIDERS],
        "runs": [_run(m) for m in (Mode.FAST, Mode.NORMAL, Mode.EXTEND)],
        "panel_rows": _panel_rows(),
        "key_policy": "API key is session-only: held in the browser for the request, never logged, never stored, "
                      "never committed, never phoned home.",
        "scope_note": "Self-contained studio artifact. The full React+TS build (live provider calls, CI visual/"
                      "a11y/perf gates) needs a frontend toolchain absent in this sandbox [BLOCKED: toolchain]; "
                      "the data binding here is real and tested, visual quality → human review.",
    }


def main():
    data = build()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pillar3_studio_data.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"wrote {out}: {len(data['modes'])} mode contracts, {len(data['providers'])} providers, "
          f"{len(data['runs'])} mode runs, {len(data['panel_rows'])} panel rows "
          f"(grades {sorted({r['grade'] for r in data['panel_rows']})})")


if __name__ == "__main__":
    main()
