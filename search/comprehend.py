"""
§BI SR-4 — context upgrade for the LLM (★ best-effort, NOT an understanding guarantee).
=========================================================================================
Turn fetched pages into BETTER CONTEXT: pull structure (title / date / author / key claims), rank source
credibility, ★ surface CONFLICTS (when sources disagree, show both sides with attribution instead of silently
picking one), weight recency, and enforce copyright (a quote <15 words, at most one per source, paraphrase
preferred). Good context helps the model — but it is NOT comprehension.

★ THE honesty line (Correction 2): this module produces *context*, never "understanding". `Context.guarantee`
is ALWAYS "best-effort" and `Context.understanding_certified` is ALWAYS False — the LLM's grasp of meaning stays
probabilistic, and claiming otherwise would be a false-EXACT. Extraction is verifiable (SR/FL completeness);
understanding is not, and we never pretend it is. zero-dep (stdlib only).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from search.deep_fetch import source_tier
except Exception:  # noqa: BLE001 — allow flat import in tests
    from deep_fetch import source_tier  # type: ignore


_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b|\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
                   r"\.?\s+\d{1,2},?\s+\d{4})\b")
# keyword is case-insensitive (?i:…), but the NAME capture requires real capitals and stays on ONE line
# ([ \t] not \s, so it never swallows the next line's first word as part of the author).
_AUTHOR = re.compile(r"(?:^|\n)[ \t]*(?i:by|author|written by)[:\s]+([A-Z][A-Za-z.\-]+(?:[ \t]+[A-Z][A-Za-z.\-]+){0,3})")


def structure(doc: dict) -> dict:
    """Heuristic structured extraction from {url, text}: title (first heading / first line), date, author, and a
    few key-claim sentences. ★ Heuristic ⇒ a best-effort STRUCTURING of the text, not a semantic reading."""
    text = doc.get("text", "") or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = ""
    for ln in lines:
        if ln.startswith("#"):
            title = ln.lstrip("# ").strip(); break
    if not title and lines:
        title = lines[0][:200]
    dm = _DATE.search(text)
    am = _AUTHOR.search(text)
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text))
    claims = [s.strip() for s in sentences if re.search(r"\d", s) or
              re.search(r"\b(is|are|was|were|will|can|must|shows?|found|reported)\b", s)]
    return {"url": doc.get("url", ""), "title": title, "date": (dm.group(0) if dm else None),
            "author": (am.group(1) if am else None), "key_claims": claims[:5],
            "credibility": source_tier(doc.get("url", ""))}


# ── copyright: quote <15 words, ≤1 quote per source, paraphrase preferred ──────────────────────────────
def safe_quote(text: str, max_words: int = 14) -> str:
    """Trim a quote to STRICTLY under 15 words (≤14) so a verbatim excerpt stays fair-use-sized. Adds an ellipsis
    when truncated. ★ The copyright floor is structural — the function cannot return a 15+-word quote."""
    words = (text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + " …"


def copyright_pack(quotes_by_source: Dict[str, List[str]]) -> List[dict]:
    """At most ONE quote per source, each <15 words; the rest must be paraphrased. Returns the allowed quotes +
    a paraphrase_preferred flag — the policy the directive requires, enforced in code not prose."""
    out = []
    for src, quotes in quotes_by_source.items():
        if not quotes:
            continue
        q = safe_quote(quotes[0])
        out.append({"source": src, "quote": q, "words": len(q.replace(" …", "").split()),
                    "dropped": max(0, len(quotes) - 1), "paraphrase_preferred": True})
    return out


# ── conflict surfacing: when sources disagree, show BOTH sides with attribution ─────────────────────────
def surface_conflicts(facts_by_source: Dict[str, Dict[str, str]]) -> List[dict]:
    """facts_by_source: {url: {subject: value}}. For any subject where ≥2 sources give DIFFERENT values, emit a
    both-sides record with attribution + each source's credibility — never silently pick a winner."""
    by_subject: Dict[str, Dict[str, str]] = {}
    for src, facts in facts_by_source.items():
        for subj, val in facts.items():
            by_subject.setdefault(subj, {})[src] = val
    conflicts = []
    for subj, srcvals in by_subject.items():
        if len({str(v).strip().lower() for v in srcvals.values()}) > 1:
            conflicts.append({"subject": subj, "both_sides": True,
                              "positions": sorted(({"source": s, "value": v, "credibility": source_tier(s)}
                                                   for s, v in srcvals.items()),
                                                  key=lambda p: -p["credibility"])})
    return conflicts


@dataclass
class Context:
    """The upgraded context handed to the LLM. ★ guarantee is ALWAYS 'best-effort'; understanding is NEVER
    certified — this object is better grounding, not comprehension."""
    structured: List[dict] = field(default_factory=list)
    conflicts: List[dict] = field(default_factory=list)
    quotes: List[dict] = field(default_factory=list)
    guarantee: str = "best-effort"           # ★ never "certified" / "exact" / "understood"
    understanding_certified: bool = False     # ★ ALWAYS False (Correction 2)


def comprehend(docs: List[dict], facts_by_source: Optional[Dict[str, Dict[str, str]]] = None,
               quotes_by_source: Optional[Dict[str, List[str]]] = None) -> Context:
    """Build the upgraded Context from fetched docs (+ optional extracted facts/quotes). ★ Always best-effort,
    understanding never certified — the single honesty invariant of the search path."""
    structured = sorted((structure(d) for d in docs), key=lambda s: -s["credibility"])
    conflicts = surface_conflicts(facts_by_source or {})
    quotes = copyright_pack(quotes_by_source or {})
    return Context(structured=structured, conflicts=conflicts, quotes=quotes,
                   guarantee="best-effort", understanding_certified=False)


def adversarial_battery() -> dict:
    """★ structure pulls title/date/author/claims; ★ a quote is forced <15 words, ≤1 per source; ★ disagreeing
    sources surface BOTH sides w/ attribution, higher-credibility first; ★ Context is ALWAYS best-effort, never
    certifies understanding (false-EXACT 0 on the comprehension claim)."""
    doc = {"url": "https://arxiv.org/abs/1", "text": "# Transformers\nBy Jane Doe\nPublished 2017-06-12.\n"
                                                     "The model uses 8 attention heads. It outperforms RNNs."}
    s = structure(doc)
    long = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen"
    pack = copyright_pack({"https://a.com": [long, "second quote"], "https://b.com": ["short one"]})
    conf = surface_conflicts({"https://nist.gov/x": {"population": "8 million"},
                              "https://blog.example/y": {"population": "9 million"}})
    ctx = comprehend([doc], facts_by_source={"https://nist.gov/x": {"v": "1"}, "https://b.org": {"v": "2"}},
                     quotes_by_source={"https://a.com": [long]})
    a_quote = pack[0]
    cases = {
        "structure_fields": s["title"] == "Transformers" and s["date"] == "2017-06-12" and s["author"] == "Jane Doe",
        "quote_under_15_words": a_quote["words"] <= 14 and a_quote["dropped"] == 1,
        "one_quote_per_source": len(pack) == 2,
        "conflict_both_sides": len(conf) == 1 and conf[0]["both_sides"] and len(conf[0]["positions"]) == 2,
        "conflict_credibility_order": conf[0]["positions"][0]["credibility"] >= conf[0]["positions"][1]["credibility"],
        "never_certifies_understanding": ctx.guarantee == "best-effort" and ctx.understanding_certified is False,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
