"""
§BI WORKSTREAM A — search engine orchestration (broader · deeper · instant · better context).
================================================================================================
Pure, testable logic that sits ABOVE the (future) `web_search`/`web_fetch` backend: query decomposition +
breadth dial (multi_query), deep fetch + source-priority ranking (deep_fetch), content-hash caching (cache),
and the context upgrade (comprehend). ★ The live network execution is author-validated on Render (this sandbox
egress-blocks the open web and no backend is wired); the logic here — distinctness, dedup, ranking, caching,
conflict surfacing, copyright limits — is what makes the fan-out worth doing, and it is fully exercised offline.

★ "순식간 (instant)" = parallel (multi_query) + reuse (cache) + deep-but-bounded fetch (deep_fetch) — mechanisms,
not magic. ★ comprehend is BETTER CONTEXT, never an understanding guarantee (false-EXACT 0 on comprehension).
"""
from __future__ import annotations

from search import cache, comprehend, deep_fetch, multi_query


def adversarial_battery() -> dict:
    """Aggregate the four sub-batteries — the whole search path green in one call."""
    subs = {
        "multi_query": multi_query.adversarial_battery(),
        "deep_fetch": deep_fetch.adversarial_battery(),
        "cache": cache.adversarial_battery(),
        "comprehend": comprehend.adversarial_battery(),
    }
    return {"sub": subs, "all_ok": all(s["all_ok"] for s in subs.values()),
            "failed": {k: s["failed"] for k, s in subs.items() if not s["all_ok"]}}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
