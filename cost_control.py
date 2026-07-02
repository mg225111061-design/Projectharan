"""
PHASE 3.S3 — LLM cost control: cacheable static prefix + best-of-N with verifier early-exit.
=============================================================================================
Two structural levers that cut LLM cost WITHOUT touching soundness (the verifier is still the gate):
  • prompt-cache prefix: the STATIC context (system prompt, spec, broth rules) is placed FIRST as a stable,
    cacheable prefix; only the volatile tail (this code + its counterexample) changes per call. A cache HIT
    bills the prefix at ~0.1×. effective = tail + 0.1·prefix.
  • best-of-N + early-exit: generate candidates in parallel but STOP at the first one the SOUND verifier
    accepts (the rest are cancelled). The exact verifier is the cost ceiling — no reward-model, no waste.

★ ENV HONESTY: live LLM token cost/latency needs an API key + egress → [BLOCKED]. We therefore measure the
STRUCTURAL savings from token counts (a word-count PROXY — no live tokenizer), not a live bill. Stated. ★
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


def approx_tokens(text: str) -> int:
    """A coarse token PROXY (≈ words + punctuation/4). NOT a real tokenizer (none here) — labeled as a proxy."""
    return max(1, len(text.split()) + len(text) // 4)


@dataclass
class CachePlan:
    prefix_tokens: int
    tail_tokens: int
    cold_tokens: int
    warm_tokens: float          # with a prefix cache hit (~0.1× prefix)
    savings: float              # 1 - warm/cold

    def __str__(self):
        return f"cache prefix {self.prefix_tokens}t + tail {self.tail_tokens}t: cold {self.cold_tokens} → warm "\
               f"{self.warm_tokens:.0f} ({self.savings:.0%} saved on a cache hit)"


def plan_with_cache_prefix(static_ctx: str, volatile_tail: str, hit_factor: float = 0.1) -> CachePlan:
    """Place the static context as a cacheable prefix; the volatile tail changes per call. Returns the
    cold vs warm (cache-hit) token cost. hit_factor is the provider's cached-prefix discount (~0.1×)."""
    p, t = approx_tokens(static_ctx), approx_tokens(volatile_tail)
    cold = p + t
    warm = hit_factor * p + t
    return CachePlan(p, t, cold, warm, round(1 - warm / cold, 3) if cold else 0.0)


@dataclass
class BestOfNCost:
    n: int
    p_pass: float
    expected_candidates: float  # expected #generations until the first verifier-PASS (early-exit)
    tokens_per_cand: int
    expected_tokens: float
    naive_tokens: int           # if we generated all N
    savings: float

    def __str__(self):
        return f"best-of-{self.n} @p={self.p_pass}: E[cands]={self.expected_candidates:.2f} → "\
               f"{self.expected_tokens:.0f}t vs {self.naive_tokens}t ({self.savings:.0%} saved by early-exit)"


def best_of_n_cost(n: int, p_pass: float, tokens_per_cand: int) -> BestOfNCost:
    """Expected generation cost with verifier EARLY-EXIT: stop at the first PASS. E[#generated until first
    success in N tries] under independent pass-prob p (capped at N). The SOUND verifier bounds the cost."""
    # E[min(geom(p), N)] = Σ_{i=1..N} P(no pass in first i-1) = Σ_{i=0..N-1} (1-p)^i
    q = 1 - p_pass
    exp_cands = sum(q ** i for i in range(n)) if p_pass > 0 else n
    expected_tokens = exp_cands * tokens_per_cand
    naive = n * tokens_per_cand
    return BestOfNCost(n, p_pass, round(exp_cands, 3), tokens_per_cand, round(expected_tokens, 1), naive,
                       round(1 - expected_tokens / naive, 3) if naive else 0.0)


@dataclass
class CostReport:
    cache: CachePlan
    best_of_n: BestOfNCost
    live_llm: str

    def combined_factor(self) -> float:
        """Illustrative combined cost factor (cache warm × best-of-N early-exit), per the proxy model."""
        return round((self.cache.warm_tokens / self.cache.cold_tokens) *
                     (self.best_of_n.expected_tokens / self.best_of_n.naive_tokens), 3)


def measure_cost(static_ctx: Optional[str] = None, tail: Optional[str] = None,
                 n: int = 6, p_pass: float = 0.5) -> CostReport:
    """Structural LLM-cost measurement (proxy tokens). Live billing is [BLOCKED: key/egress]."""
    static_ctx = static_ctx or ("SYSTEM: verify code against spec. SPEC: ensures result = sum 1..n. "
                                 "BROTH RULES: faulhaber, c-finite, gosper, telescoping. " * 20)
    tail = tail or "USER: fn f(n: Nat){ fold k in 1..n { k } }  COUNTEREXAMPLE: n=1 -> 2 != 1"
    cache = plan_with_cache_prefix(static_ctx, tail)
    bon = best_of_n_cost(n, p_pass, tokens_per_cand=approx_tokens(tail) + 40)
    return CostReport(cache, bon,
                      "[BLOCKED: live LLM token cost needs an API key + egress; structural savings measured "
                      "from a token PROXY, not a live bill]")
