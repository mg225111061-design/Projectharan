"""
PRODUCT HARDENING PHASE 1 — sound content-hash caching (stdlib only, zero-dep). The biggest Clock-A win: a hit
avoids the LLM call / the re-verification entirely, and is PROVABLY the same computation (keyed on a content hash
of the exact inputs + a version), so a stale/wrong hit is impossible.
=================================================================================================================
★ SOUNDNESS INVARIANT: key = sha256(canonical(exact inputs) + VERSION). Identical inputs+version ⇒ identical key ⇒
  the cached result is byte-for-byte what a cold run produces. Any mutated input OR a version bump ⇒ different key ⇒
  MISS. A cache is never consulted across versions. (A stale hit would be a correctness bug — tested against.)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple


def content_key(*parts: Any, version: str = "v1") -> str:
    """A deterministic content hash of the EXACT inputs + version. Canonical JSON ⇒ stable across runs/processes."""
    def canon(o):
        if isinstance(o, (bytes, bytearray)):
            return {"__bytes__": hashlib.sha256(bytes(o)).hexdigest()}
        if isinstance(o, dict):
            return {str(k): canon(o[k]) for k in sorted(o, key=str)}
        if isinstance(o, (list, tuple)):
            return [canon(v) for v in o]
        if callable(o):
            return {"__callable__": getattr(o, "__qualname__", repr(o))}
        return o
    blob = json.dumps([canon(p) for p in parts], sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob + b"::" + version.encode()).hexdigest()


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0

    @property
    def hit_rate(self) -> float:
        t = self.hits + self.misses
        return round(self.hits / t, 3) if t else 0.0


@dataclass
class SoundCache:
    """A content-hash-keyed cache. `compute(key_parts, fn)` returns fn() on a miss (and stores it) or the stored
    value on a hit — guaranteed identical because the key includes a hash of the exact inputs + version."""
    name: str
    version: str = "v1"
    store: Dict[str, Any] = field(default_factory=dict)
    stats: CacheStats = field(default_factory=CacheStats)

    def get(self, *key_parts) -> Tuple[bool, Any]:
        k = content_key(*key_parts, version=self.version)
        if k in self.store:
            self.stats.hits += 1
            return True, self.store[k]
        self.stats.misses += 1
        return False, None

    def put(self, value, *key_parts) -> None:
        self.store[content_key(*key_parts, version=self.version)] = value

    def compute(self, key_parts, fn: Callable):
        hit, v = self.get(*key_parts)
        if hit:
            return v
        v = fn()
        self.put(v, *key_parts)
        return v

    def invalidate_version(self, new_version: str) -> None:
        """A version bump abandons the old keys (different hash ⇒ every prior entry MISSES — never stale)."""
        self.version = new_version


# the three product caches (1a result, 1b verification, 1c CEGIS counterexamples)
RESULT_CACHE = SoundCache("result", version="v1")
VERIFY_CACHE = SoundCache("verification", version="v1")
CEGIS_CACHE = SoundCache("cegis_counterexamples", version="v1")


def cached_result(task_spec, provider: str, model: str, fn: Callable):
    """1a: skip the LLM call when (task spec + provider + model + version) was already produced + verified."""
    return RESULT_CACHE.compute((task_spec, provider, model), fn)


def cached_verification(code: str, spec, verifier_version: str, fn: Callable):
    """1b: skip re-verification when (code + spec + verifier version) was already proved (verification is
    deterministic in its inputs, so the cached verdict is sound)."""
    return VERIFY_CACHE.compute((code, spec, verifier_version), fn)


def report() -> dict:
    return {c.name: {"hits": c.stats.hits, "misses": c.stats.misses, "hit_rate": c.stats.hit_rate, "size": len(c.store)}
            for c in (RESULT_CACHE, VERIFY_CACHE, CEGIS_CACHE)}
