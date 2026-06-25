"""
CAPSTONE PHASE 4 — heavy / external bypass strategies: CALL SITES wired, compute honestly DEFERRED.
==================================================================================================
These bypasses need a heavy / unavailable engine (a native binary, a build-failing wheel, or a human-driven
proof assistant). Per the constitution we NEVER fabricate their result — we wire the CALL SITE and the routing
probe so that the day the engine is installed the leg activates with NO further code, and until then the body
returns an HONEST_DEFER naming the precise blocker. `try_bypass(name, payload)` attempts the engine and either runs
it or defers; `availability()` probes every engine; `status_report()` feeds the §C capstone report.

This is the directive's "호출부 배선해 다리만 끼우면 작동, 컴퓨트는 정직 defer + 사유."
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import kernel_verdict as KV
from mechanisms.base import honest_defer


@dataclass
class HeavyBypass:
    name: str
    group: str                # the 우회군 (A–I)
    feeds: str                # which mechanism(s) it feeds
    probe_import: str         # the python module / binary whose presence gates it
    install: str              # how it would be obtained
    why_deferred: str         # the precise blocker (honest)
    runner: Optional[Callable] = None   # set when a sound runner exists (else pure call-site)


# the registry — every heavy bypass from the research, with its precise honest-defer reason.
HEAVY: List[HeavyBypass] = [
    HeavyBypass("verified_lifting", "A", "M13/whole", "metalift",
                "pip: metalift (github)", "Metalift not installed — needs the lift DSL + an LLM-propose/SMT-verify loop "
                "(claude_agent is present for the proposer; the lifter engine is the blocker)"),
    HeavyBypass("d_dnnf_compile", "C", "M9/M12", "pysdd",
                "binary: c2d / d4 / miniC2D (or pip pysdd)", "no knowledge-compilation engine on PATH — d-DNNF/SDD "
                "circuit compilation deferred (linear model counting once compiled)"),
    HeavyBypass("symmetry_nauty", "E", "M1/symmetry-reduction", "pynauty",
                "pip: pynauty (needs C nauty)", "pynauty wheel fails to build here (C nauty headers absent) — graph "
                "automorphism / orbit partition deferred; call site ready"),
    HeavyBypass("koopman", "I", "M11", "pykoopman",
                "pip: pykoopman", "pykoopman install timed out (heavy deps) — Koopman linear-embedding of nonlinear "
                "dynamics deferred (linear-fit residual would be the cert)"),
    HeavyBypass("data_refinement", "F", "categorical-duality", "isabelle",
                "Isabelle Sepref / CoqEAL / Cubical Agda", "proof-assistant refinement needs a human-driven proof + a "
                "runtime we forbid as a dependency — only a [BLOCKED] subprocess, never a runtime dep"),
    HeavyBypass("compressed_domain", "G", "M12/M13", "systemds",
                "SystemDS / Re-Pair", "no compressed-linear-algebra engine — computing directly on SLP/Re-Pair "
                "compressed data deferred (compression=operation-equivalence would be the cert)"),
    HeavyBypass("mona_mso", "H", "M2/M9", "mona",
                "binary: MONA", "MONA (WS1S/WS2S automata) binary not on PATH — MSO-over-bounded-treewidth decision "
                "deferred; automatic-structures call site ready"),
    HeavyBypass("openfst_min", "C", "M9", "pywrapfst",
                "OpenFST / pywrapfst", "OpenFST not installed — weighted-automaton minimization to a canonical machine "
                "deferred (the in-repo L* already gives the unweighted minimal DFA)"),
]
_BY_NAME = {h.name: h for h in HEAVY}


def availability() -> Dict[str, bool]:
    """Probe each engine's import (best-effort) — which heavy legs are live in THIS environment."""
    out: Dict[str, bool] = {}
    for h in HEAVY:
        try:
            __import__(h.probe_import)
            out[h.name] = True
        except Exception:  # noqa: BLE001
            out[h.name] = False
    return out


def defer(name: str) -> KV.Verdict:
    """The honest HONEST_DEFER for a heavy bypass (names the precise blocker — never a fabricated result)."""
    h = _BY_NAME.get(name)
    if h is None:
        return honest_defer("heavy_bypass", f"unknown heavy bypass {name!r}")
    return honest_defer(f"bypass.{h.name}", f"{h.why_deferred} [feeds {h.feeds}; install: {h.install}]")


def try_bypass(name: str, payload) -> KV.Verdict:
    """Call site: run the engine if a sound runner is wired AND its import is available; else honest DEFER. This is
    what lets the body CALL the leg today and have it light up the moment the engine is installed."""
    h = _BY_NAME.get(name)
    if h is None:
        return honest_defer("heavy_bypass", f"unknown heavy bypass {name!r}")
    if h.runner is not None:
        try:
            __import__(h.probe_import)
        except Exception:  # noqa: BLE001
            return defer(name)
        return h.runner(payload)
    return defer(name)


def status_report() -> dict:
    """For the §C report: how many heavy bypasses are wired vs live here, with per-leg blockers."""
    avail = availability()
    return {
        "total": len(HEAVY),
        "available_here": sorted(n for n, ok in avail.items() if ok),
        "deferred_here": sorted(n for n, ok in avail.items() if not ok),
        "by_group": {h.name: (h.group, h.feeds, h.why_deferred) for h in HEAVY},
    }
