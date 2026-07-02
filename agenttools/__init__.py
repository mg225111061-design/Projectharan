"""
agenttools — the agent tool-calling framework (10H directive, Task 1).
=======================================================================
A tool CATALOG (registry.py) that can grow to hundreds of entries (Task 2), a ROUTER (router.py) that
exposes only a small task-matched subset per request (never the whole catalog — dumping 300 tools at a
model measurably reduces tool-call reliability, per the directive's own web-verified research), an
EXECUTOR (executor.py) that runs a tool call and never lets it crash the caller, a CAPABILITY gate
(capability.py) that live-checks whether the chosen Ollama model actually supports tool-calling before
ever exposing tools to it, and the execution-feedback LOOP (toolcall.py) that ties all four together.

★ RF-5 (tool count ≠ fold-acceleration count) ★: every registered tool carries exactly one tier tag —
  FOLD-ELIGIBLE (genuine numeric/structural core; delegates to an existing recognizer/fold engine),
  ACCEL-ELIGIBLE (not fold, but legitimately fast via caching/parallelization; delegates to accel/),
  PLAIN (I/O-bound — file/git/subprocess/grep-class tools; normal, not an acceleration target, nothing
  to be ashamed of). Mislabeling a PLAIN tool as FOLD/ACCEL is itself a false-EXACT-class error — the
  registry enforces the tag is always one of the three, but a WRONG tag on a true PLAIN tool is a human
  authoring error the registry cannot catch; every tool added under FOLD/ACCEL in this package must name
  the real engine it delegates to (see catalog_fold.py / catalog_accel.py's docstrings for the mapping).

This package is wired into the existing agentic pipeline as an OPT-IN (`enable_tools=False` by default)
so zero existing caller/test changes behavior — see agentic.py::_claude_model_fn.

Reached from `webapi/engine_dispatch.py::agenttools_reach()` (engine_inventory.py's repo-wide gap=0 audit
requires every top-level package to be production-reachable — see `_WIRED_PACKAGES`), which calls this
module's own `adversarial_battery()` below, matching the convention every other wired package uses
(newengine/newengine5/newengine3/metakernel/qmkernel).
"""
from __future__ import annotations


def adversarial_battery() -> dict:
    """Self-check reached by webapi.engine_dispatch.agenttools_reach: registry tier validation (RF-5),
    router exposure cap (Prime Directive 1 — never the whole catalog), provider wire-shape split (mirrors
    claude_agent.claude_generate's own anthropic-vs-everything-else split), executor never-crash, and the
    Ollama capability gate's fail-safe default are each proven LIVE here, not just importable."""
    from agenttools import capability as CAP
    from agenttools import executor as EX
    from agenttools import registry as REG
    from agenttools import router as RT

    cases = {}
    try:
        REG.Tool("_adv_bad_tier", "d", {"type": "object", "properties": {}}, lambda: 1, "NOT_A_TIER")
        cases["registry_rejects_unknown_tier"] = False
    except ValueError:
        cases["registry_rejects_unknown_tier"] = True
    try:
        REG.Tool("_adv_bad_fold", "d", {"type": "object", "properties": {}}, lambda: 1, REG.FOLD_ELIGIBLE)
        cases["registry_requires_delegate_for_fold"] = False
    except ValueError:
        cases["registry_requires_delegate_for_fold"] = True

    big = [REG.Tool(f"_adv_filler_{i}", "d", {"type": "object", "properties": {}}, lambda: 1, REG.PLAIN)
          for i in range(40)]
    cases["router_caps_exposure"] = len(RT.select_tools("anything", max_tools=5, catalog=big)) == 5

    probe = REG.Tool("_adv_probe_tool", "d", {"type": "object", "properties": {}}, lambda: "ok", REG.PLAIN)
    native = RT.to_wire_shape([probe], "anthropic")
    wrapped = RT.to_wire_shape([probe], "ollama_local")
    cases["wire_shape_split_correct"] = ("input_schema" in native[0]) and ("function" in wrapped[0])

    # register()/unregister() bracket the executor check — TEMPORARY, so this self-test never permanently
    # inflates the live catalog's measured count (that count is asserted exactly elsewhere; a leaked probe
    # tool would silently drift it every time this battery runs).
    REG.register(probe)
    try:
        cases["executor_unknown_tool_safe"] = EX.execute("_adv_tool_does_not_exist", {}).ok is False
        cases["executor_executes_valid_tool"] = EX.execute("_adv_probe_tool", {}).output == "ok"
    finally:
        REG.unregister("_adv_probe_tool")

    cases["capability_failsafe_unreachable"] = CAP.ollama_supports_tools("x", host="http://localhost:1") is False

    failed = [k for k, v in cases.items() if not v]
    return {"cases": cases, "all_ok": not failed, "failed": failed}


# Populate the catalog (Task 2) on any `agenttools` import — a router with an empty catalog can't route
# anything. Each import is a module-level side effect (register() calls), matching catalog/__init__.py's
# own "importing the pass modules registers their transforms" convention elsewhere in this repo.
from agenttools import catalog_accel, catalog_explore, catalog_fold, catalog_plain  # noqa: F401,E402
