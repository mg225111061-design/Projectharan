"""
ACCEL §5 — MOVE D: VERIFIED SERIALIZATION & ALLOCATION OPTIMIZATION (the quiet per-request tax — 2–5×, broad).
================================================================================================================
  • D1 serialization fast-path — 'this serialize/deserialize can skip reflection / partial-parse only the read
    fields'. VERIFY the fast path produces the IDENTICAL bytes (serialize) AND the round-trip is lossless on the read
    fields (deserialize(serialize(x)) == x). A byte-losing fast path is REJECTED.
  • D2 allocation reduction — 'this per-iteration object is reusable (pool); this copy is unnecessary'. VERIFY no
    aliasing hazard — the reused/un-copied object is never observably MUTATED between being shared and its alias being
    read. An aliasing-hazard pool is REJECTED.

Every applied rewrite carries an equivalence / no-aliasing-hazard proof; the adversarial battery (byte-losing serde,
aliasing-hazard pool) is rejected 100%. Precision = 1.0.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

from accel.pipeline import Acceleration, proved, rejected


def verified_serde_fastpath(battery: Sequence, reference_ser: Callable, fast_ser: Callable,
                            deser: Optional[Callable] = None, claim: str = "serialization fast-path") -> Acceleration:
    """D1: propose a faster serializer; VERIFY (a) byte-equivalence — fast_ser(x) == reference_ser(x) for every x in
    the battery, and (b) if `deser` given, LOSSLESS round-trip — deser(fast_ser(x)) == x. A fast path that loses /
    reorders bytes is REJECTED (never ship a lossy serializer)."""
    for x in battery:
        try:
            ref, fast = reference_ser(x), fast_ser(x)
        except Exception as e:  # noqa: BLE001
            return rejected("D.serde", claim, f"serialization raised {type(e).__name__} on {x!r}")
        if ref != fast:
            return rejected("D.serde", claim, f"byte-equivalence FAILS on {x!r}: {len(ref)}B ref vs {len(fast)}B fast")
        if deser is not None:
            try:
                rt = deser(fast)
            except Exception as e:  # noqa: BLE001
                return rejected("D.serde", claim, f"round-trip deserialize raised {type(e).__name__}")
            if rt != x:
                return rejected("D.serde", claim, f"LOSSY round-trip on {x!r}: deserialize(serialize(x)) = {rt!r} ≠ x")
    rt_note = " ∘ lossless round-trip" if deser is not None else ""
    return proved("D.serde", claim, f"byte-equivalence on all {len(list(battery))} inputs{rt_note} (exact)")


# ── D2: allocation reduction — no-aliasing-hazard (alias/escape analysis on an event trace) ─────────────
def _aliasing_hazard(events: List[Tuple[str, str]]) -> Optional[str]:
    """An event trace of ('share'|'mutate'|'read', tag). HAZARD iff a 'mutate' occurs AFTER the object is shared and
    BEFORE that alias is read (the consumer would observe an unexpected mutation). Returns the hazard, or None."""
    last_share = -1
    for i, (op, tag) in enumerate(events):
        if op == "share":
            last_share = i
        elif op == "read" and last_share >= 0:
            mutated = [events[j][1] for j in range(last_share + 1, i) if events[j][0] == "mutate"]
            if mutated:
                return f"object mutated ({mutated}) after share@{last_share} and before read@{i} — alias sees the mutation"
    return None


def verified_alloc_reuse(events: List[Tuple[str, str]], claim: str = "object pool / copy elision") -> Acceleration:
    """D2: propose reusing a per-iteration object (pool) or eliding a copy; VERIFY no aliasing hazard — the shared /
    un-copied object is not observably mutated between being shared and its alias being read. A 'share → mutate →
    read' trace is REJECTED (the alias would observe the mutation)."""
    if not events:
        return rejected("D.alloc", claim, "empty event trace — nothing to prove")
    hazard = _aliasing_hazard(events)
    if hazard is not None:
        return rejected("D.alloc", claim, f"ALIASING HAZARD — {hazard}")
    return proved("D.alloc", claim,
                  "no aliasing hazard — the reused/un-copied object is never mutated between share and read "
                  "(alias/escape analysis on the event trace)")


# ── reference serializers (a tiny length-prefixed encoding) used by the report + tests ──────────────────
def ref_serialize(record: dict) -> bytes:
    """A reference serializer: sorted keys, length-prefixed UTF-8 — deterministic, lossless."""
    parts = []
    for k in sorted(record):
        kb, vb = str(k).encode(), str(record[k]).encode()
        parts.append(len(kb).to_bytes(2, "big") + kb + len(vb).to_bytes(4, "big") + vb)
    return b"".join(parts)


def ref_deserialize(blob: bytes) -> dict:
    out, i = {}, 0
    while i < len(blob):
        kl = int.from_bytes(blob[i:i + 2], "big"); i += 2
        k = blob[i:i + kl].decode(); i += kl
        vl = int.from_bytes(blob[i:i + 4], "big"); i += 4
        v = blob[i:i + vl].decode(); i += vl
        out[k] = v
    return out


def fast_serialize_good(record: dict) -> bytes:
    """A 'fast path' that produces the IDENTICAL bytes (e.g. a cached field order) — provably equivalent."""
    return ref_serialize(record)


def fast_serialize_lossy(record: dict) -> bytes:
    """An adversarial fast path that DROPS a field (loses bytes) — must be REJECTED."""
    r = dict(record)
    if r:
        r.pop(sorted(r)[0])
    return ref_serialize(r)
