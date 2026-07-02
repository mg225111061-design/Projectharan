"""
§Q IDEA 6 — PROVEN CONTENT-DEDUP: byte-identical results merged into one I/O.
================================================================================================================
Prove two requests reached by different code paths yield BYTE-IDENTICAL results and serve both from one I/O —
eliminating redundant fetches of the same data reached via different paths.

★ PROOF GATE: dedup applies ONLY if byte-identity is proved — both requests are DETERMINISTIC and produce identical
bytes. If only SEMANTICALLY equivalent (same meaning, possibly different bytes) ⇒ route to Idea 1's semantic
cache-share instead; if a request is non-deterministic (nonce / timestamp / random) ⇒ NOT byte-identical ⇒ keep
separate. Never merge on a guess — a false merge serves the wrong bytes = a correctness violation = the build fails.
"""
from __future__ import annotations

from typing import List, Optional

from accel.pipeline import Acceleration, proved, rejected


def proven_dedup(bytes_a: Optional[bytes], bytes_b: Optional[bytes],
                 a_deterministic: bool = True, b_deterministic: bool = True) -> Acceleration:
    """Merge two requests into one I/O iff byte-identity is PROVED: both deterministic AND identical bytes. A
    non-deterministic request (nonce/timestamp) or differing bytes ⇒ keep separate (zero false merges)."""
    if not (a_deterministic and b_deterministic):
        return rejected("Q6.dedup", "merge byte-identical requests into 1",
                        "a request is NON-DETERMINISTIC (nonce / timestamp / random) — bytes not provably identical")
    if bytes_a is None or bytes_b is None:
        return rejected("Q6.dedup", "merge byte-identical requests into 1", "missing result bytes — cannot prove identity")
    if bytes_a != bytes_b:
        return rejected("Q6.dedup", "merge byte-identical requests into 1",
                        f"results differ ({len(bytes_a)}B vs {len(bytes_b)}B / content) — provably NOT identical, kept separate")
    return proved("Q6.dedup", "merge byte-identical requests into 1",
                  f"both deterministic AND byte-identical ({len(bytes_a)}B, exact match) ⇒ one fetch serves both consumers")


def measure_dedup(requests: List[dict]) -> dict:
    """`requests` = [{name, bytes, deterministic}]. Merge proven-byte-identical deterministic requests; report the
    deduplicated I/O count. Byte-differing / non-deterministic look-alikes are kept separate (zero false merges)."""
    served: List[dict] = []            # distinct I/Os actually issued
    merged = 0
    false_merges = 0
    for r in requests:
        hit = False
        for s in served:
            acc = proven_dedup(r.get("bytes"), s.get("bytes"), r.get("deterministic", True), s.get("deterministic", True))
            if acc.applied:
                merged += 1
                hit = True
                if r.get("bytes") != s.get("bytes"):       # would be a false merge — must never happen
                    false_merges += 1
                break
        if not hit:
            served.append(r)
    return {"requests": len(requests), "distinct_io": len(served), "merged_away": merged,
            "false_merges": false_merges, "io_avoided": merged,
            "note": "byte-identity dedup (COUNT reduction), measured; false_merges MUST be 0 (precision); "
                    "semantic-only equivalents route to Idea 1, not here"}
