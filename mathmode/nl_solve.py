"""
PHASE 1 — natural-language MATH pipeline (symbolic-first, LLM-assisted, HONESTLY graded).
=========================================================================================
Order of operations, with the constitution's honesty:
  1. SYMBOLIC FIRST (no key, no network): run the robust parser. If it routes, solve it — the computation is EXACT
     and needs NO LLM. The interpretation is echoed (how the input was read) for the user to sanity-check.
  2. NL FALLBACK (only if symbolic parse fails AND an LLM sender is provided): the LLM translates the prose into a
     STRUCTURED problem; we ECHO that interpretation tagged UNVERIFIED (the LLM may misread — that step is NOT
     trusted), then the engine computes the structured problem EXACTLY and the checker grades it.
  3. OFFLINE (symbolic fails, no LLM / egress blocked): honest — NL understanding is [BLOCKED: needs the provider
     API]; symbolic notations still work without a key. A precise parse-DECLINE, never a fabricated answer.

§X honesty: NL understanding is UNVERIFIED (echo the interpretation); only the COMPUTATION is EXACT. Symbolic
input needs no key; only NL needs the LLM. MR.JEFFREY WRAPS the LLM — the LLM proposes the interpretation, the
tools + checker arbitrate the answer.
"""
from __future__ import annotations

import json
from typing import Callable, Optional

import kernel_verdict as KV
from mathmode import solver as S


def solve_nl(text: str, llm_sender: Optional[Callable] = None, model: str = "claude-opus-4-8") -> S.MathSolution:
    """Solve a possibly-natural-language MATH query. Symbolic-first (key-free); LLM only for prose it can't parse,
    with the interpretation echoed UNVERIFIED. Returns a MathSolution whose trace shows the interpretation step."""
    # 1) SYMBOLIC FIRST — no key, no network
    problem = S.parse_problem(text)
    if "_parse_error" not in problem and problem:
        sol = S.solve_in_mode(problem, "extend")
        sol.reasoning.insert(0, S.Step("interpret", f"parsed SYMBOLICALLY (no LLM): {json.dumps(problem, default=str)[:120]}", None))
        return sol

    # 2) NL FALLBACK — needs an LLM sender (provider API). Echo the interpretation UNVERIFIED.
    if llm_sender is not None:
        try:
            structured = _nl_to_structured(text, llm_sender, model)
        except Exception as e:  # noqa: BLE001
            structured = None
        if structured:
            sol = S.solve_in_mode(structured, "extend")
            sol.reasoning.insert(0, S.Step("interpret",
                f"LLM interpreted the prose as: {json.dumps(structured, default=str)[:140]} «UNVERIFIED — the LLM "
                f"may misread; the COMPUTATION below is exact»", None))
            return sol

    # 3) OFFLINE — honest [BLOCKED] for NL; symbolic still works without a key
    hint = problem.get("_parse_error", "could not parse")
    v = KV.decline(f"nl: {hint}. Natural-language understanding needs the provider API "
                   f"[BLOCKED here: no key / egress]; symbolic notations (e.g. sum(k^2,k,1,100), 2^50 mod 97, "
                   f"fibonacci(100) mod 1e9+7) work with NO key.", "mathmode.nl")
    sol = S.MathSolution(v, [S.Step("interpret", "symbolic parse failed; LLM NL path [BLOCKED: no sender]", KV.DECLINE)],
                         inner_mode="extend")
    return sol


def _nl_to_structured(text: str, llm_sender: Callable, model: str) -> Optional[dict]:
    """Ask the LLM (via the §4 router) to translate prose → a structured MATH problem dict. The sender does the
    actual network call (in the sandbox it is a mock / injected double — live is UNVERIFIED, egress-blocked)."""
    import provider as P
    import llm_router as R
    cfg = P.Config(provider="anthropic", model=model, base_url=None, has_env_key=False)
    sys_prompt = ("Translate the user's math question into ONE JSON object the HARAN solver accepts. Use exactly "
                  "these shapes: {\"kernel\":\"modexp\",\"a\":..,\"b\":..,\"m\":..} | "
                  "{\"kernel\":\"fib\",\"n\":..,\"m\":..} | {\"kernel\":\"faulhaber\",\"p\":..,\"N\":..} | "
                  "{\"kernel\":\"lucas_lehmer\",\"p\":..} | {\"kernel\":\"collatz\",\"n\":..} | "
                  "{\"sum\":\"<summand in k>\"} | {\"domain\":\"number_theory\",\"op\":\"is_prime\",\"n\":..}. "
                  "Output ONLY the JSON, no prose.")
    res = R.route(cfg, text, system=sys_prompt, mode="live", sender=llm_sender)
    if res.status != "OK" or not res.text:
        return None
    try:
        obj = json.loads(res.text)
        return obj if isinstance(obj, dict) else None
    except Exception:  # noqa: BLE001
        return None


def live_status() -> dict:
    """Honest posture: symbolic always works (no key); NL needs the provider API (UNVERIFIED while egress-blocked)."""
    return {"symbolic": "WORKS (no key, EXACT)", "natural_language": "UNVERIFIED [egress-blocked: needs provider API]",
            "echo_interpretation": True, "computation_grade": "EXACT (the checker arbitrates, not the LLM)"}
