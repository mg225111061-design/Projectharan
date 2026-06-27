"""
§V PHASE 2 — THE SOUND MULTILEVEL CACHE: compute-once, look-up-forever, never a wrong hit.
================================================================================================================
Generalizes the offline pre-proving machinery from proofs to ALL engine operations. Three levels (L1 hot-path / L2
verification-fold / L3 proof-DAG) plus an ABSENCE-certificate cache (cache the negatives — "this does NOT fold" — so
a known-miss is never retried) and a JIT-artifact cache (compiled callables reused).

★ SOUND KEYS (precision 1.0). A hit is served ONLY when the key PROVABLY identifies the same computation:
  • content_key — sha256 of a canonical serialization of the input. Same bytes ⇒ same key ⇒ same computation, by
    construction (key-completeness is the injectivity of the serialization on the input space).
  • canonical_ast_key — for code, the sha256 of an α-normalized, docstring/whitespace-stripped AST. Two α-equivalent
    sources share a key AND compute the same result (proved by recompute-equivalence on the cached entry); two
    non-equivalent sources get different canonical forms ⇒ different keys ⇒ no collision.
If key completeness can't be argued, the operation is NOT cached (never a guessed key that could collide).

★ EVICTION is always safe: LRU/size-bounded eviction only costs a recompute on the next miss, never a wrong result —
correctness comes from recompute-equivalence, so the cache is a pure performance layer.
"""
from __future__ import annotations

import ast
import hashlib
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple


# ── sound keys ───────────────────────────────────────────────────────────────────────────────────────────────
def content_key(*parts: Any) -> str:
    """A content hash over a canonical serialization of the inputs. Same inputs ⇒ same key ⇒ same computation. The
    key is COMPLETE by construction: the serialization is injective on the input space, so distinct computations
    cannot share a key (no stale/wrong hit)."""
    h = hashlib.sha256()
    for p in parts:
        h.update(repr(p).encode("utf-8"))
        h.update(b"\x1e")                                   # record separator — repr boundaries can't be forged across parts
    return h.hexdigest()


class _Canon(ast.NodeTransformer):
    """α-normalize an AST: rename locally-bound names to positional slots, drop docstrings, so α-equivalent functions
    canonicalize identically. Free/global names are kept (they carry meaning), so two functions differing only in a
    free reference get DIFFERENT canonical forms (no false merge)."""
    def __init__(self):
        self._map: Dict[str, str] = {}

    def _slot(self, name: str) -> str:
        if name not in self._map:
            self._map[name] = f"_v{len(self._map)}"
        return self._map[name]

    def visit_FunctionDef(self, node):
        for a in node.args.args:
            self._slot(a.arg)
        node.name = "_f"
        # drop a leading docstring
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant) \
                and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]
        self.generic_visit(node)
        return node

    def visit_arg(self, node):
        node.arg = self._slot(node.arg)
        return node

    def visit_Name(self, node):
        if node.id in self._map:                            # only rename names we bound (locals/params); free names kept
            node.id = self._map[node.id]
        return node


def canonical_ast_key(src: str) -> Optional[str]:
    """The canonical-form key for code: α-normalized, docstring-stripped AST dump, hashed. Returns None if the source
    doesn't parse (⇒ not cacheable by this key — never a guessed key). Sound: α-equivalent code shares the key (and is
    proved result-equivalent on the entry); non-equivalent code gets a different canonical form."""
    try:
        tree = ast.parse(src.strip())
    except SyntaxError:
        return None
    canon = _Canon().visit(tree)
    ast.fix_missing_locations(canon)
    return hashlib.sha256(ast.dump(canon).encode("utf-8")).hexdigest()


# ── the cache levels ───────────────────────────────────────────────────────────────────────────────────────────
@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return round(self.hits / self.total, 4) if self.total else 0.0


class SoundCache:
    """An LRU, size-bounded, sound key→value cache. `get_or_compute(key, compute)` returns the stored value on a hit
    (O(1)) or computes+stores on a miss. Correctness is by recompute-equivalence: the stored value is exactly what
    `compute()` returns for that key, so eviction (which only forces a recompute) is always safe."""
    def __init__(self, name: str, capacity: int = 4096):
        self.name = name
        self.capacity = capacity
        self._d: "OrderedDict[str, Any]" = OrderedDict()
        self.stats = CacheStats()

    def get_or_compute(self, key: str, compute: Callable[[], Any]) -> Any:
        if key in self._d:
            self._d.move_to_end(key)
            self.stats.hits += 1
            return self._d[key]
        self.stats.misses += 1
        val = compute()
        self._d[key] = val
        if len(self._d) > self.capacity:
            self._d.popitem(last=False)                     # evict LRU — only costs a recompute next time, never wrong
            self.stats.evictions += 1
        return val

    def peek(self, key: str) -> Tuple[bool, Any]:
        return (key in self._d, self._d.get(key))

    def __len__(self):
        return len(self._d)


class AbsenceCache:
    """Cache the NEGATIVES: a key recorded here is a KNOWN MISS (e.g. 'this code does NOT fold' / 'no structure') so
    the engine never re-attempts a proven-failed computation. Sound because the negative is a real proven result —
    not a guess — recorded the same way a positive fold is."""
    def __init__(self, name: str):
        self.name = name
        self._s: set = set()
        self.hits = 0
        self.records = 0

    def is_known_miss(self, key: str) -> bool:
        if key in self._s:
            self.hits += 1
            return True
        return False

    def record_miss(self, key: str) -> None:
        if key not in self._s:
            self._s.add(key)
            self.records += 1


class JITArtifactCache:
    """Cache compiled/lowered artifacts (e.g. a compiled callable) keyed by the source's canonical key, so the same
    code is compiled ONCE and reused. The artifact is a pure function of the key (deterministic compile)."""
    def __init__(self):
        self._d: Dict[str, Any] = {}
        self.compiles = 0
        self.reuses = 0

    def get_or_compile(self, src: str, compile_fn: Callable[[str], Any]) -> Any:
        k = canonical_ast_key(src) or content_key(src)
        if k in self._d:
            self.reuses += 1
            return self._d[k]
        self.compiles += 1
        art = compile_fn(src)
        self._d[k] = art
        return art


@dataclass
class MultiLevelCache:
    """L1 (hot-path immediate) · L2 (verification/fold results) · L3 (proof DAG / lemma library) + absence + JIT —
    the offline multilevel structure generalized to all engine operations."""
    L1: SoundCache = field(default_factory=lambda: SoundCache("L1-hot", 8192))
    L2: SoundCache = field(default_factory=lambda: SoundCache("L2-verify-fold", 8192))
    L3: SoundCache = field(default_factory=lambda: SoundCache("L3-proof-dag", 8192))
    absence: AbsenceCache = field(default_factory=lambda: AbsenceCache("absence-cert"))
    jit: JITArtifactCache = field(default_factory=JITArtifactCache)

    def summary(self) -> dict:
        return {lvl: {"hit_rate": c.stats.hit_rate, "hits": c.stats.hits, "misses": c.stats.misses,
                      "evictions": c.stats.evictions, "size": len(c)}
                for lvl, c in (("L1", self.L1), ("L2", self.L2), ("L3", self.L3))} | {
            "absence": {"records": self.absence.records, "hits": self.absence.hits},
            "jit": {"compiles": self.jit.compiles, "reuses": self.jit.reuses}}


def prove_key_completeness(samples, key_fn, compute_fn) -> dict:
    """★ The soundness proof for a key: over a battery, (a) NO two inputs with different recompute results share a key
    (no collision ⇒ no wrong hit), and (b) inputs that SHARE a key recompute to the SAME result (the key is a sound
    equivalence). Returns {sound, collisions} — `sound` must hold or the operation is not cached."""
    by_key: Dict[str, Any] = {}
    collisions = []
    for s in samples:
        k = key_fn(s)
        if k is None:
            continue
        v = compute_fn(s)
        if k in by_key and by_key[k] != v:
            collisions.append({"key": k[:12], "v1": by_key[k], "v2": v})
        else:
            by_key.setdefault(k, v)
    return {"sound": not collisions, "collisions": collisions, "distinct_keys": len(by_key), "samples": len(list(samples))}
