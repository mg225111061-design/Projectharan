"""
§BI SR-1 + SR-5 — parallel multi-query decomposition + breadth dial (the honest "순식간 = parallel").
=====================================================================================================
"순식간 (instant)" is NOT magic — it is **parallelism**: search one question from several angles at the same
time. This module is the PURE, deterministic part of that: turn one query into a set of *distinct* sub-queries
(so the parallel calls each cover different ground, not the same string N times) and dial the breadth to the
question's complexity. The actual concurrent `web_search` calls + the knowledge-driven expansion ("which towns
are within 1 hour of X") are the LLM's job on Render — this module guarantees distinctness, the breadth budget,
and result dedup, which is what makes the parallel fan-out worth doing.

★ Honest scope: a pure function cannot know which places are near X (that needs world knowledge) — so we do the
*structural* expansion (explicit enumeration splitting + research-angle variants), and the LLM does the semantic
expansion on Render. Every emitted sub-query is distinct by construction; we never pad the fan-out with repeats.
zero-dep (stdlib only).
"""
from __future__ import annotations

import hashlib
import re
from typing import Iterable, List, Sequence


# ── SR-5: breadth dial — scale the number of parallel sub-queries to the question's complexity ──────────
def breadth_for(complexity: str) -> int:
    """A simple fact needs 1 query; a broad/deep research question fans out to many. NOT unbounded — capped at
    20 (the directive's 8–20 deep band) so a runaway prompt cannot launch a thousand calls."""
    return {"trivial": 1, "simple": 1, "moderate": 4, "broad": 8, "deep": 16, "exhaustive": 20}.get(
        (complexity or "simple").strip().lower(), 4)


_ANGLES = ("latest", "official documentation", "comparison vs alternatives", "reviews and criticism",
           "how it works", "pricing and availability", "recent news", "best practices",
           "tutorial and examples", "limitations and risks", "benchmarks and performance", "common use cases",
           "history and background", "security considerations", "integration and API")


def _norm(q: str) -> str:
    return re.sub(r"\s+", " ", (q or "").strip().lower())


def _split_enumeration(query: str) -> List[str]:
    """Explicit enumeration in the query itself ("A, B and C hotels") → ["A hotels", "B hotels", "C hotels"].
    Splits a leading comma/and list and re-attaches the shared tail. Deterministic, no world knowledge."""
    m = re.match(r"^\s*(.+?)\s+(hotels?|restaurants?|tools?|libraries|options|providers|vendors)\b(.*)$",
                 query, re.IGNORECASE)
    head, tail = (m.group(1), f" {m.group(2)}{m.group(3)}") if m else (query, "")
    parts = re.split(r"\s*,\s*|\s+\band\b\s+", head)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        return [f"{p}{tail}".strip() for p in parts]
    return []


def decompose(query: str, breadth: int = 4) -> List[str]:
    """SR-1: one query → up to `breadth` DISTINCT sub-queries (the base, any explicit enumeration, then research
    angles), deduped case-insensitively. ★ Each is meaningfully different — we never repeat the same string to
    inflate the parallel fan-out (that would buy latency, not coverage)."""
    breadth = max(1, int(breadth))
    out: List[str] = []
    seen = set()

    def add(q: str):
        q = q.strip()
        key = _norm(q)
        if q and key not in seen:
            seen.add(key)
            out.append(q)

    add(query)
    for e in _split_enumeration(query):
        add(e)
    base = query.strip().rstrip("?.")
    for ang in _ANGLES:
        if len(out) >= breadth:
            break
        add(f"{base} {ang}")
    return out[:breadth]


# ── result dedup — overlapping searches return the same pages; keep each once (the cache's friend) ──────
def _result_key(r: dict) -> str:
    url = (r.get("url") or r.get("link") or "").strip().lower().rstrip("/")
    if url:
        return f"u:{url}"
    body = (r.get("title", "") + r.get("snippet", "") + r.get("text", "")).encode("utf-8", "replace")
    return "h:" + hashlib.sha256(body).hexdigest()[:16]


def dedup_results(results: Iterable[dict]) -> List[dict]:
    """Dedup search hits by normalized URL, falling back to a content hash. Order-preserving (first wins)."""
    seen = set()
    out = []
    for r in results:
        k = _result_key(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def plan(query: str, complexity: str = "moderate") -> dict:
    """End-to-end SR-1+SR-5 plan: complexity → breadth → distinct sub-queries (to be searched in PARALLEL on
    Render). Pure; returns the plan so the caller (or a test) can verify distinctness + budget before any I/O."""
    b = breadth_for(complexity)
    subs = decompose(query, b)
    return {"breadth": b, "sub_queries": subs, "distinct": len(subs) == len({_norm(s) for s in subs}),
            "parallel": len(subs) > 1}


def adversarial_battery() -> dict:
    """★ sub-queries are pairwise distinct (no padded repeats); ★ breadth scales with complexity; ★ enumeration
    is split; ★ dedup removes URL + content duplicates."""
    p_deep = plan("vector databases", "deep")
    p_simple = plan("capital of France", "simple")
    enum = decompose("Oxford, Bath and Bristol hotels", 8)
    dd = dedup_results([{"url": "https://a.com/x"}, {"url": "https://a.com/x/"}, {"title": "t", "snippet": "s"},
                        {"title": "t", "snippet": "s"}, {"url": "https://b.com"}])
    cases = {
        "deep_distinct": p_deep["distinct"] and len(p_deep["sub_queries"]) == 16,
        "simple_single": p_simple["breadth"] == 1 and len(p_simple["sub_queries"]) == 1,
        "no_repeats": len(p_deep["sub_queries"]) == len(set(s.lower() for s in p_deep["sub_queries"])),
        "enumeration_split": "Oxford hotels" in enum and "Bath hotels" in enum and "Bristol hotels" in enum,
        "dedup_url_and_content": len(dd) == 3,                       # a.com (url-normalized) + t/s + b.com
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
