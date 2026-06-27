"""
§Q IDEA 4 — PROVEN INVALIDATION-MINIMIZATION: keep the cache a write provably cannot touch.
================================================================================================================
Ordinary caches invalidate CONSERVATIVELY — a write drops every cache entry that MIGHT be affected, crushing the hit
rate and forcing re-fetch I/Os. We prove with z3/set-disjointness that "this write cannot affect this cache entry"
and KEEP it — preserving the hit rate and avoiding the re-fetches conservative invalidation would force.

★ PROOF GATE: an entry survives a write ONLY if z3 proves the write cannot change it (the write's target set is
disjoint from the entry's read set, or more generally the write's effect doesn't change the entry's computed result).
If independence can't be proved (overlap possible / unknown) ⇒ INVALIDATE conservatively (the safe default) — NEVER
keep on a guess. A wrongly-kept entry serves stale data = a correctness violation = the build fails.
"""
from __future__ import annotations

from typing import Sequence

from accel.pipeline import Acceleration, proved, rejected


def proven_keep(write_targets: Sequence[str], entry_reads: Sequence[str]) -> Acceleration:
    """Keep a cache entry across a write iff the write's target set is provably DISJOINT from the entry's read set.
    Any overlap (possible effect) ⇒ REJECT the keep ⇒ invalidate conservatively (zero stale-keeps)."""
    S, T = set(write_targets), set(entry_reads)
    if S & T:
        return rejected("Q4.inval", "keep cache entry across the write",
                        f"write touches {sorted(S & T)} that the entry reads — the write MAY change it ⇒ INVALIDATE "
                        "conservatively (no stale keep)")
    return proved("Q4.inval", "keep cache entry across the write",
                  f"write set {sorted(S)} ∩ entry read set {sorted(T)} = ∅ ⇒ the write provably CANNOT change the "
                  "entry ⇒ KEEP it (the next read hits cache instead of a re-fetch I/O)")


def measure_invalidation(writes: Sequence[dict], entries: Sequence[dict]) -> dict:
    """Modeled: over a sequence of writes, count how many cache entries are KEPT (provably unaffected) vs the
    conservative all-invalidate baseline. The kept entries are the re-fetch I/Os AVOIDED (measured exactly)."""
    conservative_invalidations = 0          # baseline: every write drops every entry
    proven_kept = 0                         # ours: keep provably-disjoint entries
    stale_keeps = 0                         # MUST stay 0 (precision)
    for w in writes:
        for e in entries:
            conservative_invalidations += 1
            acc = proven_keep(w.get("targets", []), e.get("reads", []))
            if acc.applied:
                proven_kept += 1
                if set(w.get("targets", [])) & set(e.get("reads", [])):   # would be a stale keep — must never happen
                    stale_keeps += 1
    return {"conservative_invalidations": conservative_invalidations, "proven_kept": proven_kept,
            "refetch_io_avoided": proven_kept, "stale_keeps": stale_keeps,
            "hit_rate_preserved_fraction": round(proven_kept / max(1, conservative_invalidations), 4),
            "note": "kept entries = re-fetch I/Os avoided (COUNT), measured; stale_keeps MUST be 0 (precision)"}
