"""
v27 STAGE 16 (levers 2–3) — repo-RAG retrieval + verified-solution cache  (PROPOSERS, verifier-gated).
=======================================================================================================
Two more accuracy/speed levers — but with one iron rule (§1.9, §5.9): RETRIEVAL AND CACHE ARE PROPOSERS,
NEVER GUARANTEES. Anything they surface MUST pass the write→verify→fix verifier before it is used; a
spec-violating retrieval is REJECTED, not trusted.

  • retrieve(query, corpus)         — rank candidate snippets by structural-signature match (S13) + token
                                       overlap (dependency/lexical proximity). Pure ranking, no guarantee.
  • retrieve_and_verify(query, …)    — retrieve top-k, return the FIRST that passes the verifier; if none
                                       verify, return None (honest: RAG found nothing provable).
  • VerifiedSolutionCache            — caches only VERIFIED solutions keyed by structural signature (links
                                       with S13's summary cache); a cache hit is STILL re-verified (sound,
                                       perceived-zero) before reuse.

★ HONEST (§5.9) ★: RAG/cache improve hit-rate and latency (anchors: RepoCoder +10%, CodeRAG +17.7 Pass@1)
but the correctness guarantee is the verifier alone. A live-LLM Pass@1 delta needs a key/egress
([BLOCKED] here) — the key-free, sound claim is "the gate rejects every unverified proposal".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import ai_loop
from fold_replicate import structural_signature

VerifyFn = Callable[[str], bool]


def _default_verify(source: str) -> bool:
    return ai_loop.verify_haran(source).ok


def _safe_sig(source: str) -> str:
    """Structural signature where the source is Python (S13); else fall back to the exact source string
    (so HARAN/other-language solutions are keyed exactly — honest, just not structural)."""
    try:
        sig = structural_signature(source)[0]
    except Exception:  # noqa: BLE001
        sig = ""
    return sig or source


def _tokens(src: str) -> set:
    out, cur = set(), ""
    for ch in src:
        if ch.isalnum() or ch == "_":
            cur += ch
        else:
            if cur:
                out.add(cur)
            cur = ""
    if cur:
        out.add(cur)
    return out


@dataclass
class Entry:
    name: str
    source: str
    verified: bool = False


def _similarity(query: str, cand: str) -> float:
    """Structural-signature match dominates (a true clone), then lexical Jaccard for ties."""
    qs, cs = _safe_sig(query), _safe_sig(cand)
    struct = 1.0 if qs == cs else 0.0
    qt, ct = _tokens(query), _tokens(cand)
    jac = len(qt & ct) / len(qt | ct) if (qt | ct) else 0.0
    return struct + jac           # struct match adds a full point so a clone always outranks a mere overlap


def retrieve(query: str, corpus: List[Entry], k: int = 3) -> List[Entry]:
    """Rank corpus entries by relevance to `query` (signature + lexical). A PROPOSAL, not a guarantee."""
    return sorted(corpus, key=lambda e: (-_similarity(query, e.source), e.name))[:k]


@dataclass
class RagResult:
    status: str                   # VERIFIED_RETRIEVAL | NO_VERIFIED_CANDIDATE
    source: Optional[str] = None
    from_name: str = ""
    considered: int = 0
    rejected: List[str] = field(default_factory=list)   # candidates the verifier threw out
    detail: str = ""


def retrieve_and_verify(query: str, corpus: List[Entry], k: int = 3, verify: VerifyFn = _default_verify) -> RagResult:
    """Retrieve top-k and return the first candidate that PASSES the verifier; reject the rest. RAG never
    decides correctness — the verifier does."""
    cands = retrieve(query, corpus, k)
    rejected: List[str] = []
    for e in cands:
        if verify(e.source):
            return RagResult("VERIFIED_RETRIEVAL", e.source, e.name, len(cands), rejected,
                             "retrieved candidate passed the verifier")
        rejected.append(e.name)
    return RagResult("NO_VERIFIED_CANDIDATE", None, "", len(cands), rejected,
                     "every retrieved candidate FAILED the verifier — nothing trusted (honest)")


class VerifiedSolutionCache:
    """Caches only VERIFIED solutions, keyed by structural signature. A hit is re-verified before reuse."""

    def __init__(self, verify: VerifyFn = _default_verify):
        self._store: Dict[str, str] = {}
        self._verify = verify
        self.hits = 0
        self.misses = 0

    def put(self, source: str) -> bool:
        if not self._verify(source):
            return False                       # never cache an unverified solution
        self._store[_safe_sig(source)] = source
        return True

    def get(self, query: str) -> Optional[str]:
        cached = self._store.get(_safe_sig(query))
        if cached is None:
            self.misses += 1
            return None
        if not self._verify(cached):           # sound: re-verify the hit (perceived-zero, but never blind)
            self.misses += 1
            return None
        self.hits += 1
        return cached
