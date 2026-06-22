"""
Pillar 3 · ROUND 3 #73 — effects analysis → safe reordering & batching/coalescing (SOUND).
============================================================================================
Each operation has an EFFECT: a read-set, a write-set, and an I/O flag. Two operations COMMUTE (are safe to
reorder or run in parallel) iff they share no write (W-W), and neither writes what the other reads (R-W / W-R),
and they are not both ordering-sensitive I/O. Pure ops commute with everything. From this we license two
transforms, each EXACT (result/effects unchanged): REORDER independent ops, and COALESCE repeated idempotent
READS of the same resource within a window that has no intervening WRITE to it (N round-trips → 1). A conflict
(an intervening write, or ordered I/O) ⇒ DECLINE the transform (keep the order — a wrong reorder is a bug). The
coalescing win is measured as the round-trip reduction (the metric that matters for I/O-bound code).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set, Tuple

import kernel_verdict as KV


@dataclass(frozen=True)
class Effect:
    reads: frozenset = field(default_factory=frozenset)
    writes: frozenset = field(default_factory=frozenset)
    io: bool = False


def commutes(a: Effect, b: Effect) -> bool:
    """Two effects commute iff no W-W, no R-W / W-R conflict, and not both ordering-sensitive I/O."""
    if a.writes & b.writes:
        return False
    if a.writes & b.reads or b.writes & a.reads:
        return False
    if a.io and b.io:
        return False
    return True


def reorderable(seq: List[Effect]) -> bool:
    """Safe to freely reorder / parallelize iff EVERY pair commutes."""
    return all(commutes(seq[i], seq[j]) for i in range(len(seq)) for j in range(i + 1, len(seq)))


def coalesceable_reads(ops: List[Tuple[str, object]]) -> bool:
    """ops = [("read"|"write", key), …]. Repeated reads of a key may coalesce to one iff NO write to that key
    occurs anywhere in the window (the read result is invariant across the window)."""
    written = {key for kind, key in ops if kind == "write"}
    return all(key not in written for kind, key in ops if kind == "read")


@dataclass
class EffectsResult:
    verdict: "KV.Verdict"
    report: Optional[object]


def coalesce_grade(make_input: Callable[[], tuple], fetch_cost: int, *, n: int, samples: int = 5,
                   floor: float = 1.20) -> Tuple[KV.Verdict, Optional[object]]:
    """Prove the read window coalesceable (no intervening write), then measure naive-N-fetches vs coalesced-
    unique-fetches (round-trip reduction). Coalesceable + win ⇒ EXACT; an intervening write ⇒ DECLINE."""
    from pillar3 import lifting as LF
    ops = make_input()[0]
    if not coalesceable_reads(ops):
        return KV.decline("a WRITE to a fetched key occurs in the window — reads are NOT coalesceable ⇒ DECLINE "
                          "(stale result risk)", "coalesce"), None

    def _fetch(key):
        x = 0
        for _ in range(fetch_cost):                          # deterministic stand-in for a round-trip's cost
            x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        return (key, x)

    def naive(o):
        return [_fetch(key) for kind, key in o if kind == "read"]      # one round-trip PER read

    def coalesced(o):
        cache = {}
        out = []
        for kind, key in o:
            if kind != "read":
                continue
            if key not in cache:                             # one round-trip per UNIQUE key (proven safe)
                cache[key] = _fetch(key)
            out.append(cache[key])
        return out

    if naive(ops) != coalesced(ops):
        return KV.decline("coalesced result ≠ naive (effects claim wrong) ⇒ DECLINE", "coalesce"), None
    rep = LF.measure_lift(lambda o: naive(o), lambda o: coalesced(o), make_input, 0, n=n, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"coalesceable but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "coalesce")
        v.report = rep
        return v, rep
    uniq = len({key for kind, key in ops if kind == "read"})
    total = sum(1 for kind, _ in ops if kind == "read")
    cert = KV.Cert(KV.EXACT, "effects_coalesce", passed=True, check_cost="effect-set window analysis",
                   detail=f"reads coalesced {total}→{uniq} round-trips (no intervening write proven); behavior-preserving")
    v = KV.exact(coalesced, "coalesce", str(rep), cert)
    v.report = rep
    return v, rep


# ── effect-sequence batteries: reorderable (independent) vs conflicting; coalesceable vs write-invalidated ──
def reorderable_seqs():
    return [
        [Effect(reads=frozenset({"a"})), Effect(reads=frozenset({"b"})), Effect(reads=frozenset({"c"}))],   # all reads
        [Effect(writes=frozenset({"x"})), Effect(writes=frozenset({"y"})), Effect(reads=frozenset({"z"}))], # disjoint
    ]


def conflicting_seqs():
    return [
        [Effect(writes=frozenset({"x"})), Effect(reads=frozenset({"x"}))],          # W→R same key (RAW)
        [Effect(io=True), Effect(io=True)],                                          # ordered I/O
        [Effect(writes=frozenset({"k"})), Effect(writes=frozenset({"k"}))],          # W-W same key
    ]


_OPS_CACHE: dict = {}


def make_coalesce_ops(unique: int = 40, reads: int = 4000, with_write: bool = False):
    key = (unique, reads, with_write)
    if key not in _OPS_CACHE:
        import random as _rnd
        rng = _rnd.Random(39)
        ops = [("read", rng.randrange(unique)) for _ in range(reads)]
        if with_write:
            ops.insert(reads // 2, ("write", rng.randrange(unique)))   # a write to a fetched key ⇒ not coalesceable
        _OPS_CACHE[key] = (ops,)
    return _OPS_CACHE[key]
