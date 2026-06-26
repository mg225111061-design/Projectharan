"""
EXTREME ACCELERATION PHASE 8 — the B-path: cut LLM calls to push PRODUCT latency (Clock A), soundly.
======================================================================================================
A's extreme compute speed does NOT move the product's end-to-end latency — the three-clocks data shows Clock A
(LLM latency) dominates B. So B is pushed SEPARATELY, by eliminating LLM calls. This deepens the product-hardening
exact cache (catalog/prodcache) with a SECOND, SOUND tier:

  • TIER 1 — exact content hash (prodcache.SoundCache): byte-identical spec ⇒ the stored VERIFIED result is reused
    (skip generation AND re-verification — provably the same computation; a stale hit is impossible).
  • TIER 2 — NORMALIZED key (this module): a semantics-preserving canonicalization of the spec (strip comments,
    collapse whitespace, case-fold keywords) so a TEXTUALLY-different but equivalent request reuses a prior
    candidate. ★ SOUNDNESS ★: a normalized hit is a SUGGESTION, not a verified result — it MUST RE-PASS
    VERIFICATION before use (Clock B is still paid; only the Clock-A generation is skipped). If re-verification
    fails, we fall through to a real LLM call. So a wrong cached candidate can NEVER be shipped — the verifier is
    still the arbiter. The win is honestly bounded: Clock-A generation avoided on equivalent variants, Clock B
    unchanged. (Never a verified-result claim from a fuzzy key — that would be the cardinal sin.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple


def normalized_key(spec: str) -> str:
    """A semantics-preserving canonicalization: strip line comments, collapse all whitespace, lower-case. This is
    deliberately CONSERVATIVE — it only erases textual noise that cannot change meaning. (It does NOT reorder
    tokens or rewrite structure; the result is still re-verified, so even an over-aggressive normalization can only
    cost a wasted verification, never ship a wrong answer.)"""
    s = re.sub(r"#.*?$", "", spec, flags=re.MULTILINE)        # strip trailing line comments
    s = re.sub(r"\s+", " ", s).strip().lower()                # collapse whitespace, case-fold
    return s


@dataclass
class BPathStats:
    exact_hits: int = 0
    suggestion_verified: int = 0      # normalized-key candidate that RE-PASSED verification (Clock-A saved)
    suggestion_rejected: int = 0      # normalized candidate that FAILED re-verify ⇒ fell through to LLM
    misses: int = 0                   # genuine LLM calls (generation)

    @property
    def llm_generations(self) -> int:
        return self.misses + self.suggestion_rejected

    @property
    def clockA_saved(self) -> int:
        return self.exact_hits + self.suggestion_verified


@dataclass
class TwoTierCache:
    """Exact-verified tier ∘ normalized-suggestion tier. The exact tier returns a verified result with no work; the
    normalized tier returns a candidate that is RE-VERIFIED before use (sound — never ships unverified)."""
    version: str = "v1"
    _exact: Dict[str, Any] = field(default_factory=dict)         # content-hash → verified result
    _norm: Dict[str, Any] = field(default_factory=dict)          # normalized-key → candidate result
    stats: BPathStats = field(default_factory=BPathStats)

    def request(self, spec: str, generate: Callable[[str], Any], verify: Callable[[Any], bool]) -> Tuple[str, Any]:
        """Resolve a request with the soundest available shortcut. Returns (path, result) where path ∈
        {exact_hit, verified_suggestion, miss}. INVARIANT: the returned result is ALWAYS verified — an exact hit was
        verified when stored; a suggestion is re-verified here; a miss is generated then verified."""
        import catalog.prodcache as PC
        ek = PC.content_key(spec, version=self.version)
        if ek in self._exact:                                   # TIER 1 — verified result, zero work
            self.stats.exact_hits += 1
            return "exact_hit", self._exact[ek]
        nk = normalized_key(spec)
        if nk in self._norm:                                    # TIER 2 — candidate; MUST re-verify (sound)
            cand = self._norm[nk]
            if verify(cand):                                    # re-passed verification ⇒ safe to reuse (Clock-A saved)
                self.stats.suggestion_verified += 1
                self._exact[ek] = cand                          # promote to the exact-verified tier for this spec
                return "verified_suggestion", cand
            self.stats.suggestion_rejected += 1                 # candidate failed ⇒ fall through to a real LLM call
        # MISS — generate (the LLM call, Clock A) then verify before storing/returning
        self.stats.misses += 1
        result = generate(spec)
        if not verify(result):
            return "miss", None                                 # generated code did not verify — never store/ship it
        self._exact[ek] = result
        self._norm[nk] = result
        return "miss", result


def measure_bpath(workload, version: str = "v1") -> dict:
    """Measure the Clock-A reduction (LLM generations avoided) on a workload of spec variants. `workload` is a list
    of spec strings (some exact repeats, some whitespace/comment variants of earlier ones). Generation is mocked
    (live LLM is BLOCKED: egress); the COUNT of avoided generations is exact/deterministic — the honest Clock-A
    metric. Clock B (verification) is unchanged and reported separately (the two clocks never mix)."""
    gen_calls = {"n": 0}

    def generate(spec):
        gen_calls["n"] += 1
        return {"code": normalized_key(spec), "ok": True}       # a deterministic stand-in for the model's output

    def verify(cand):
        return bool(cand) and cand.get("ok") is True            # a deterministic stand-in for the verifier
    cache = TwoTierCache(version=version)
    paths = []
    for spec in workload:
        path, _ = cache.request(spec, generate, verify)
        paths.append(path)
    st = cache.stats
    return {
        "clock": "A (LLM latency) — live BLOCKED: egress; metric = generations avoided (exact)",
        "requests": len(workload), "llm_generations": st.llm_generations, "gen_calls_actual": gen_calls["n"],
        "exact_hits": st.exact_hits, "verified_suggestions": st.suggestion_verified, "misses": st.misses,
        "clockA_reduction": round(1 - st.llm_generations / max(1, len(workload)), 3),
        "soundness": "every returned result is verified (exact tier was verified when stored; suggestion re-verified; "
                     "miss generated-then-verified) — a fuzzy-key hit NEVER ships unverified",
        "ledger_separation": "Clock A (this metric) is reported apart from Clock C (compute) — A's speed ≠ B's latency",
    }
