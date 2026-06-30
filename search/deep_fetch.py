"""
§BI SR-2 — deep fetch beyond the snippet + source-priority ranking + bounded 1-hop follow.
============================================================================================
A search snippet is too short to ground an answer. SR-2 fetches the FULL TEXT of the top results and follows
the single most relevant link one hop deeper — preferring ORIGINAL/primary sources (a company's own blog, a
peer-reviewed paper, a .gov/.edu page, an SEC filing) over aggregators and SEO spam. The fetch itself is an
INJECTED callable `fetch(url) -> text`, so the ranking + plan logic is fully testable offline (the live
`web_fetch` binds on Render, under the same egress rules as the provider path).

★ Honest: ranking is a deterministic domain-tier heuristic, not a truth oracle — a high tier means "more likely
primary/authoritative", never "correct". Conflicts across sources are surfaced downstream (SR-4), not hidden.
zero-dep (stdlib only).
"""
from __future__ import annotations

import re
from typing import Callable, List, Optional, Tuple
from urllib.parse import urlparse


# ── source tiers: primary/authoritative first, aggregators/spam last (higher = preferred) ───────────────
_TIER = [
    (5, ("arxiv.org", "doi.org", "ncbi.nlm.nih.gov", "pubmed", "nature.com", "acm.org", "ieee.org")),
    (5, (".gov", ".edu", "sec.gov", "europa.eu", "who.int", "nist.gov")),
    (4, ("github.com", "gitlab.com", "readthedocs", "docs.", "developer.", "official")),
    (2, ("medium.com", "substack.com", "blogspot", "wordpress", "dev.to")),
    (1, ("pinterest.", "quora.com", "answers.", "ehow", "content-farm", "listicle")),
]


def source_tier(url: str) -> int:
    """Deterministic authority tier of a URL's host (5 primary/peer-reviewed/gov … 1 aggregator/spam, 3 default).
    ★ NOT a correctness oracle — a tier is a prior on being a primary source, nothing more."""
    host = (urlparse(url).netloc or url or "").lower()
    full = (url or "").lower()
    for score, marks in _TIER:
        if any(m in host or m in full for m in marks):
            return score
    return 3


def rank_sources(results: List[dict]) -> List[dict]:
    """Stable-sort results by (source tier desc, original index asc) — primary sources float up, ties keep the
    search engine's order. Adds `_tier` for transparency."""
    enriched = [dict(r, _tier=source_tier(r.get("url") or r.get("link") or "")) for r in results]
    return sorted(enriched, key=lambda r: -r["_tier"])          # python sort is stable ⇒ ties keep input order


_LINK_RE = re.compile(r'href=["\']?(https?://[^"\'> ]+)', re.IGNORECASE)


def pick_followups(page_text: str, base_tier: int, max_links: int = 1) -> List[str]:
    """SR-2 1-hop: from a fetched page, pick up to `max_links` outbound links that are at least as authoritative
    as the page itself (don't follow a primary source down into spam). Bounded — never a crawl."""
    links = _LINK_RE.findall(page_text or "")
    ranked = sorted(set(links), key=lambda u: -source_tier(u))
    return [u for u in ranked if source_tier(u) >= base_tier][:max_links]


def deep_fetch(results: List[dict], fetch: Optional[Callable[[str], str]] = None, top_k: int = 3,
               follow_hops: int = 1) -> dict:
    """Plan (and, if `fetch` is provided, execute) a deep fetch: rank → take top_k → full-text each → follow ≤1
    hop to an equally-or-more authoritative link. Returns {plan, docs}. With fetch=None it returns the PLAN only
    (pure, no I/O) so the caller can inspect it; the live fetch runs on Render."""
    ranked = rank_sources(results)
    chosen = ranked[:max(1, top_k)]
    plan = [{"url": r.get("url") or r.get("link"), "tier": r["_tier"]} for r in chosen]
    docs: List[dict] = []
    if fetch is not None:
        for r in chosen:
            url = r.get("url") or r.get("link") or ""
            text = fetch(url) or ""
            docs.append({"url": url, "tier": r["_tier"], "text": text, "depth": 0})
            if follow_hops > 0:
                for nxt in pick_followups(text, r["_tier"], max_links=follow_hops):
                    docs.append({"url": nxt, "tier": source_tier(nxt), "text": fetch(nxt) or "", "depth": 1})
    return {"plan": plan, "docs": docs, "ranked_tiers": [r["_tier"] for r in ranked]}


def adversarial_battery() -> dict:
    """★ primary sources outrank aggregators; ★ 1-hop follow stays ≥ the page's tier (no descent into spam);
    ★ plan-only mode does zero I/O; ★ injected fetch gathers full text + the followed hop."""
    results = [{"url": "https://pinterest.com/x", "title": "p"}, {"url": "https://arxiv.org/abs/1", "title": "a"},
               {"url": "https://medium.com/y", "title": "m"}, {"url": "https://nist.gov/z", "title": "n"}]
    ranked = rank_sources(results)
    pages = {"https://arxiv.org/abs/1": 'see <a href="https://doi.org/10.1/2">doi</a> and '
                                        '<a href="https://pinterest.com/junk">junk</a>',
             "https://doi.org/10.1/2": "primary methods section", "https://nist.gov/z": "standard text",
             "https://pinterest.com/x": "", "https://medium.com/y": ""}
    fetched = deep_fetch(results, fetch=lambda u: pages.get(u, ""), top_k=2, follow_hops=1)
    plan_only = deep_fetch(results, fetch=None, top_k=2)
    followed = [d["url"] for d in fetched["docs"] if d["depth"] == 1]
    cases = {
        "primary_first": ranked[0]["_tier"] == 5 and ranked[-1]["_tier"] == 1,
        "doi_followed_not_spam": "https://doi.org/10.1/2" in followed and "https://pinterest.com/junk" not in followed,
        "plan_only_no_io": plan_only["docs"] == [] and len(plan_only["plan"]) == 2,
        "fetched_fulltext": any(d["text"] == "primary methods section" for d in fetched["docs"]),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
