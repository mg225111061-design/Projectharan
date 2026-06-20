"""
Pillar 3 · PHASE P — the LLM proposer (five providers) that is NEVER the arbiter (Constitution Rule 5).
=======================================================================================================
With a provider + key, a real LLM (Claude / ChatGPT / Gemini / any Anthropic- or OpenAI-shaped gateway)
PROPOSES a fix for a profiler-located, detector-classified hotspot. The verifier still ARBITRATES — every
proposal goes through differential testing + (tier-gated) certificate + a measured whole-program win, all under
the active ModePolicy. Without a key, the proposer falls back to the deterministic structural detector from
PHASE M (more trustworthy here) — tagged honestly.

Key safety (LEVEL-1): the key is only ever a per-call argument placed into a request header for sending. It is
never logged, never stored, never returned in a ProposedFix, never phoned home. The live network path is not
auto-executed in this sandbox (arbitrary LLM code is not exec'd) ⇒ it is tagged UNVERIFIED and excluded from
auto-apply; the deterministic and the (test) mock-transport paths are the measured ones.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

import kernel_verdict as KV
import provider as PRV
from pillar3 import record as RC
from pillar3 import verifier as V
from pillar3.fixers.pipeline import apply_and_grade
from pillar3.mode import Mode, ModePolicy


@dataclass
class Hotspot:
    """A profiler-located, detector-classified hotspot handed to the proposer (the proposer proposes a WHAT;
    the profiler already decided the WHERE)."""
    name: str
    slow_fn: Callable
    waste_type: str
    deterministic_fix: Optional[Callable] = None     # the PHASE-M structural fix (no-LLM fallback)
    prove_fn: Optional[Callable] = None              # Z3 proof factory, if the swap is provable
    exact_justification: Optional[str] = None        # by-construction EXACT, if applicable
    fraction: float = 0.9


@dataclass
class ProposedFix:
    fast_fn: Optional[Callable]                       # the proposed faster implementation (None ⇒ not runnable here)
    source: str                                      # "llm:openai" | "llm:gemini" | "deterministic:<waste>"
    waste_type: str
    rationale: str = ""
    prove_fn: Optional[Callable] = None
    exact_justification: Optional[str] = None
    transport_kind: str = ""                         # which wire protocol would carry the live call
    verified_path: str = "MEASURED"                  # MEASURED | "UNVERIFIED [...]" — never a faked win
    # NOTE: a ProposedFix NEVER carries the API key.


# ── request building (the transport is SELECTED per provider; bodies match each vendor's API) ──────────
def build_request(cfg: "PRV.Config", prompt: str, key: str) -> Dict[str, Any]:
    """Build the HTTP request for the chosen provider (PHASE P). The key goes ONLY into the send-headers; it is
    never logged. Returns a dict {kind,url,headers,json} ready for a transport to POST. No network here."""
    kind = PRV.transport_kind(cfg.provider)
    base = (cfg.base_url or "").rstrip("/")
    if kind == "openai_chat":                                    # native OpenAI + every openai_compat gateway
        return {"kind": kind, "url": f"{base}/chat/completions",
                "headers": {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                "json": {"model": cfg.model, "messages": [
                    {"role": "system", "content": "You optimise code; output only an equivalent faster version."},
                    {"role": "user", "content": prompt}]}}
    if kind == "gemini_generate":                                # native Gemini
        return {"kind": kind, "url": f"{base}/models/{cfg.model}:generateContent",
                "headers": {"x-goog-api-key": key, "Content-Type": "application/json"},
                "json": {"contents": [{"parts": [{"text": prompt}]}]}}
    return {"kind": "anthropic_sdk", "url": (base or "anthropic-sdk-default"),    # Anthropic Messages API
            "headers": {"x-api-key": key, "anthropic-version": "2023-06-01"},
            "json": {"model": cfg.model, "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]}}


def _build_prompt(h: Hotspot, mode: Mode) -> str:
    floor = ("It MUST be provably equivalent (an algorithmic rewrite a verifier can prove); differential-only "
             "rewrites will be rejected." if mode == Mode.EXTEND else
             "It must be behaviourally equivalent on the recorded inputs.")
    return (f"Hotspot `{h.name}` has waste type `{h.waste_type}`. Propose a faster, equivalent implementation. "
            f"{floor} Return only the function body.")


def propose_fix(hotspot: Hotspot, mode: Mode, *, provider_cfg: "Optional[PRV.Config]" = None,
                key: Optional[str] = None, transport: Optional[Callable[[Dict], Dict]] = None) -> ProposedFix:
    """Propose a fix. With provider+key+transport: the LLM proposes (the transport is the injectable network
    call; in tests it is mocked). Without a key: the deterministic PHASE-M structural fix, tagged honestly. The
    proposer NEVER decides acceptance — that is the verifier's job (see `arbitrate`)."""
    cfg = provider_cfg or PRV.config()
    kind = PRV.transport_kind(cfg.provider)
    if key and transport is not None:
        req = build_request(cfg, _build_prompt(hotspot, mode), key)
        resp = transport(req)                                    # the mock returns a runnable fix; live returns code text
        fast = resp.get("fast_fn")                               # present only on the (test) mock / materialised path
        if fast is None:
            return ProposedFix(None, f"llm:{cfg.provider}", hotspot.waste_type,
                               rationale=resp.get("rationale", "live LLM proposal (code text)"),
                               transport_kind=kind,
                               verified_path="UNVERIFIED [live LLM code not auto-executed in sandbox]")
        return ProposedFix(fast, f"llm:{cfg.provider}", hotspot.waste_type,
                           rationale=resp.get("rationale", "LLM-proposed fix"),
                           prove_fn=resp.get("prove_fn"), exact_justification=resp.get("exact_justification"),
                           transport_kind=kind, verified_path="MEASURED")
    # no key ⇒ deterministic structural detector proposes (Rule 5 — more trustworthy here)
    return ProposedFix(hotspot.deterministic_fix, f"deterministic:{hotspot.waste_type}", hotspot.waste_type,
                       rationale="no LLM key — deterministic structural detector (PHASE M)",
                       prove_fn=hotspot.prove_fn, exact_justification=hotspot.exact_justification,
                       transport_kind=kind,
                       verified_path="MEASURED" if hotspot.deterministic_fix else "UNVERIFIED [no fix available]")


def arbitrate(proposed: ProposedFix, hotspot: Hotspot, *, make_args: Callable[[], tuple], n: int,
              oracle, mode: Mode, eq: Optional[Callable] = None, floor: float = 1.05) -> KV.Verdict:
    """THE VERIFIER ARBITRATES — regardless of who proposed. Differential FIRST (a wrong LLM fix ⇒ DECLINE),
    then measure the whole-program win, then grade; in extend the EXACT-or-DECLINE floor holds OVER the LLM too
    (a correct-but-only-differential LLM fix ⇒ DECLINE). The proposer's confidence is irrelevant here."""
    policy = ModePolicy.for_mode(mode)
    if proposed.fast_fn is None:                                 # nothing runnable (live LLM not exec'd / no fix)
        return KV.decline(f"{proposed.source}: {proposed.verified_path} — not auto-applied (Rule 6)",
                          proposed.waste_type)
    # differential + measure + base grade (Stage-1 pipeline). exact_justification only honoured if present.
    v = apply_and_grade(hotspot.slow_fn, proposed.fast_fn, make_args, n=n, hotspot_fraction=hotspot.fraction,
                        oracle=oracle, waste_type=proposed.waste_type, eq=eq, floor=floor,
                        exact_justification=proposed.exact_justification)
    if v.status == KV.DECLINE:
        return v
    # try to earn EXACT under the mode's verifier tier (extend=FULL_CERT will; fast=MICRO will not)
    if v.status == KV.PROBABILISTIC and proposed.prove_fn is not None:
        attempted, proven, info = V.attempt_certificate(policy.verifier_tier, proposed.prove_fn,
                                                        region_size=getattr(hotspot, "region_size", 1))
        if attempted and proven:
            rep = v.report
            cert = KV.Cert(KV.EXACT, "z3_bounded_translation_validation", passed=True, check_cost="Z3 bounded",
                           detail="Z3 proved output equivalence on symbolic inputs (proposer-agnostic)")
            v = KV.exact(proposed.fast_fn, proposed.waste_type, str(rep), cert)
            v.report = rep
        elif attempted and info and "counterexample" in str(info):
            return KV.decline(f"Z3 REFUTED the {proposed.source} proposal ({info}) ⇒ DECLINE", proposed.waste_type)
    # the mode grade floor holds over the LLM (extend rejects PROBABILISTIC)
    if not policy.grade_acceptable(v.status):
        rep = getattr(v, "report", None)
        d = KV.decline(f"{v.status} below {mode.value} floor {sorted(policy.acceptable_grades)} "
                       f"(proposer={proposed.source}) ⇒ DECLINE", proposed.waste_type)
        d.report = rep
        return d
    return v
