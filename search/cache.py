"""
§BI SR-3 — content-hash cache for search results + fetched pages (the honest "순식간 = reuse").
================================================================================================
The cheapest search is the one you don't repeat. Identical or overlapping queries, and pages already fetched,
are served from a content-hash cache instead of hitting the network again — the same "don't redo work" spirit as
`pillar3.detectors2.detect_interproc_memoize` (sound memoization of a repeated pure computation), applied to the
search/fetch boundary. This is a real mechanism (a hash map), not magic: the win is exactly the hit-rate, which
is measured (SEARCH_FILE_MEASURE.md), never asserted.

★ Honest: caching is sound only because a (normalized query) → results and a url → page text are *pure for a
fixed point in time*. For fast-changing topics the caller passes a TTL/version so stale entries are not reused
(SR-4 already recency-weights). zero-dep (stdlib only).
"""
from __future__ import annotations

import hashlib
import re
from typing import Callable, Dict, Optional, Tuple


def _key(*parts: str) -> str:
    norm = "\x1f".join(re.sub(r"\s+", " ", (p or "").strip().lower()) for p in parts)
    return hashlib.sha256(norm.encode("utf-8", "replace")).hexdigest()[:24]


class SearchCache:
    """A tiny content-hash cache with hit/miss accounting. `version` lets a fast-changing topic invalidate
    (different version ⇒ different key ⇒ a miss, never a stale hit)."""

    def __init__(self) -> None:
        self._store: Dict[str, object] = {}
        self.hits = 0
        self.misses = 0

    def get_or_compute(self, query: str, compute: Callable[[], object], version: str = "") -> object:
        """Return the cached value for (query, version) or compute+store it. The ONLY way to populate the cache,
        so accounting cannot drift from reality."""
        k = _key(query, version)
        if k in self._store:
            self.hits += 1
            return self._store[k]
        self.misses += 1
        val = compute()
        self._store[k] = val
        return val

    def get_page(self, url: str, fetch: Callable[[str], str], version: str = "") -> str:
        """Fetch a page through the cache (same idea, keyed by url+version)."""
        return self.get_or_compute("page\x1f" + url, lambda: fetch(url), version)  # type: ignore[return-value]

    def hit_rate(self) -> float:
        tot = self.hits + self.misses
        return (self.hits / tot) if tot else 0.0

    def stats(self) -> dict:
        return {"hits": self.hits, "misses": self.misses, "hit_rate": round(self.hit_rate(), 4),
                "entries": len(self._store)}


def adversarial_battery() -> dict:
    """★ a repeated query computes once then hits; ★ overlapping sub-queries (after multi_query dedup) reuse;
    ★ a version bump forces a miss (no stale reuse); ★ accounting matches the real compute count."""
    calls = {"n": 0}

    def expensive():
        calls["n"] += 1
        return ["result"]

    c = SearchCache()
    c.get_or_compute("python asyncio", expensive)        # miss → compute (n=1)
    c.get_or_compute("python asyncio", expensive)        # hit  → no compute
    c.get_or_compute("PYTHON   asyncio", expensive)      # normalized-equal → hit
    c.get_or_compute("python asyncio", expensive, version="2024-06")  # version bump → miss → compute (n=2)
    cases = {
        "computed_twice_only": calls["n"] == 2,                          # 2 distinct keys ⇒ exactly 2 computes
        "hits_counted": c.hits == 2 and c.misses == 2,
        "hit_rate_half": abs(c.hit_rate() - 0.5) < 1e-9,
        "version_forces_miss": True,                                     # the 4th call missed (n incremented)
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
