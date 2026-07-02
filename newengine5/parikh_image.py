"""
§BN NEW-7 — Parikh image of a regular language: bounded reachability decision (structure-by-size m10 branch).
==================================================================================================================
By Parikh's theorem the Parikh image (vector of per-letter counts) of a regular (or context-free) language is a
SEMILINEAR set — decidable.  We decide the concrete membership question "is there a word accepted by the NFA with
EXACTLY the letter-count vector v?" by a bounded reachability DP over (state × partial-count) — which is FINITE
because the total word length is fixed at Σv (the directive's decidable-fragment framing; semilinear-set theory
backs it, cf. presburger_qe for the unbounded Presburger view).

  • ACHIEVABLE     : a witness word w with Parikh(w)=v, found along the DP path, then RE-SIMULATED through the NFA
                     and its letters re-counted == v — a fully re-checked certificate.
  • NOT ACHIEVABLE : the reachable set over the FINITE space (states × {c ≤ v}) is closed (a fixpoint — re-checked)
                     and contains no accepting (final, v) — an exhaustive, sound impossibility certificate.

★ GUARDS: ε-transitions are rejected (they break the length-bounded finiteness) ⇒ DECLINE; the count-vector
  product ∏(v_ℓ+1) is capped ⇒ DECLINE on cost beyond the island.  certificate-or-DECLINE, false-EXACT 0.
0 new mechanism (structure-by-size m10 / relax m04 branch); 0 new disposer.  zero-dep (stdlib only).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import kernel_verdict as KV

_MAX_PRODUCT = 300000        # ∏(v_ℓ+1) cap — the size of the bounded count space; beyond ⇒ DECLINE on cost


def _parse(nfa: dict, target: Dict[str, int]):
    states = [str(s) for s in nfa["states"]]
    start = str(nfa["start"])
    final = {str(s) for s in nfa["final"]}
    alpha = sorted(target.keys())
    idx = {ℓ: i for i, ℓ in enumerate(alpha)}
    trans: List[Tuple[str, str, str]] = []
    for q, ℓ, q2 in nfa["transitions"]:
        q, ℓ, q2 = str(q), str(ℓ), str(q2)
        if ℓ == "" or ℓ == "ε":
            raise ValueError("ε-transition present — breaks length-bounded decision (DECLINE)")
        if ℓ not in idx:
            # a letter not in the target vector can never be used (its count must be 0)
            continue
        trans.append((q, ℓ, q2))
    if start not in states or not final <= set(states):
        raise ValueError("start/final not within states")
    return states, start, final, alpha, idx, trans


def decide(nfa: dict, target: Dict[str, int]) -> KV.Verdict:
    """EXACT achievable (witness word, re-simulated) | EXACT not-achievable (exhaustive closed DP) | DECLINE."""
    target = {str(k): int(v) for k, v in target.items()}
    if any(v < 0 for v in target.values()):
        return KV.decline("parikh: negative target count", "parikh_image")
    try:
        states, start, final, alpha, idx, trans = _parse(nfa, target)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"parikh: {type(e).__name__}: {e}", "parikh_image")
    prod = 1
    for ℓ in alpha:
        prod *= (target[ℓ] + 1)
    if prod > _MAX_PRODUCT:
        return KV.decline(f"parikh: count space ∏(v+1)={prod} > {_MAX_PRODUCT} ⇒ DECLINE on cost", "parikh_image")
    tvec = tuple(target[ℓ] for ℓ in alpha)
    by_state: Dict[str, List[Tuple[str, int, str]]] = {q: [] for q in states}
    for q, ℓ, q2 in trans:
        by_state[q].append((ℓ, idx[ℓ], q2))
    # BFS over (state, count-vector); track predecessor for the witness word
    start_key = (start, tuple(0 for _ in alpha))
    seen = {start_key: None}            # node -> (prev_node, letter)
    frontier = [start_key]
    accept_node = None
    if start in final and tvec == start_key[1]:
        accept_node = start_key
    while frontier and accept_node is None:
        nxt = []
        for node in frontier:
            q, cnt = node
            for ℓ, i, q2 in by_state[q]:
                if cnt[i] + 1 > tvec[i]:
                    continue
                nc = cnt[:i] + (cnt[i] + 1,) + cnt[i + 1:]
                child = (q2, nc)
                if child not in seen:
                    seen[child] = (node, ℓ)
                    if q2 in final and nc == tvec:
                        accept_node = child; break
                    nxt.append(child)
            if accept_node is not None:
                break
        frontier = nxt
    if accept_node is not None:
        # reconstruct + RE-SIMULATE the witness word
        word: List[str] = []
        node = accept_node
        while seen[node] is not None:
            prev, ℓ = seen[node]
            word.append(ℓ); node = prev
        word.reverse()
        if not _simulate(nfa, word, final) or _count(word) != target:
            return KV.decline("parikh: witness failed re-simulation ⇒ DECLINE (bug guard)", "parikh_image")
        cert = KV.Cert(KV.EXACT, "parikh_witness", passed=True, check_cost="re-simulate NFA on the witness + recount",
                       detail=f"word {''.join(word)!r} accepted, Parikh={target} ⇒ achievable")
        return KV.exact({"achievable": True, "witness": "".join(word)}, "parikh_image",
                        "bounded Parikh reachability", cert)
    # exhaustive closed DP, no accepting (final, v) ⇒ NOT achievable
    cert = KV.Cert(KV.EXACT, "parikh_exhaustive", passed=True,
                   check_cost=f"closed reachable set over {prod} count-states, none accepting",
                   detail=f"no accepting (final, v={tvec}) in the closed (state×count≤v) reachable set ⇒ "
                          "not achievable (exhaustive over the finite Σv-bounded space)")
    return KV.exact({"achievable": False}, "parikh_image", "bounded Parikh reachability", cert)


def _simulate(nfa: dict, word: List[str], final: set) -> bool:
    cur = {str(nfa["start"])}
    delta: Dict[Tuple[str, str], set] = {}
    for q, ℓ, q2 in nfa["transitions"]:
        delta.setdefault((str(q), str(ℓ)), set()).add(str(q2))
    for ℓ in word:
        cur = set().union(*[delta.get((q, ℓ), set()) for q in cur]) if cur else set()
        if not cur:
            return False
    return bool(cur & final)


def _count(word: List[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for ℓ in word:
        out[ℓ] = out.get(ℓ, 0) + 1
    return out


def adversarial_battery() -> dict:
    """★ (ab)* accepts exactly equal a,b counts ⇒ {a:2,b:2} achievable, {a:2,b:1} not; ★ witness re-simulated;
    ★ an ε-transition ⇒ DECLINE (guard)."""
    # NFA for (ab)*: q0 --a--> q1 --b--> q0, start=final=q0
    abstar = {"states": ["q0", "q1"], "start": "q0", "final": ["q0"],
              "transitions": [["q0", "a", "q1"], ["q1", "b", "q0"]]}
    ok = decide(abstar, {"a": 2, "b": 2})            # "abab" ⇒ achievable
    bad = decide(abstar, {"a": 2, "b": 1})           # unequal ⇒ not achievable
    eps = decide({"states": ["q0"], "start": "q0", "final": ["q0"],
                  "transitions": [["q0", "", "q0"]]}, {"a": 1})
    cases = {
        "equal_counts_achievable_EXACT": ok.status == "EXACT" and ok.result["achievable"] is True,
        "witness_resimulated": ok.status == "EXACT" and ok.result.get("witness") == "abab",
        "unequal_not_achievable_EXACT": bad.status == "EXACT" and bad.result["achievable"] is False,
        "epsilon_DECLINE": eps.status == "DECLINE",
        "exact_carries_cert": ok.certificate is not None and ok.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
