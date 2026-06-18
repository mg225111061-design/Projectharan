"""
v33 STAGE 0 — content-addressed offline artifact store (the "soup pantry").
============================================================================
Slow work (proved fold families, compiled decision functions, discovered algorithms, absence certificates)
is brewed ONCE at build-time and persisted here. Runtime only LOOKS UP by content address — never re-derives
(first principle). Addresses are blake2b digests of a canonical serialization (blake3 is unavailable in this
environment → blake2b, honestly labeled; both are collision-resistant for this use).

Layout:  .fold_soup/<aa>/<digest>.json   (sharded by first byte). An in-memory L1 dict fronts the L2 disk.
A manifest records counts. Everything is JSON (auditable, no pickling of code — artifacts are DATA: closed
forms, certificates, decision-function parameters — executed by a fixed interpreter, never eval of stored code).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

HASH_NAME = "blake2b"              # blake3 unavailable here → blake2b (labeled, not faked as blake3)
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fold_soup")


def digest(obj: Any) -> str:
    """Content address = blake2b of the canonical JSON (sorted keys, compact)."""
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.blake2b(blob, digest_size=16).hexdigest()


@dataclass
class ArtifactStore:
    root: str = _ROOT
    _l1: Dict[str, Any] = None      # in-memory hot cache (L1) over the on-disk L2

    def __post_init__(self):
        self._l1 = {}
        os.makedirs(self.root, exist_ok=True)

    def _path(self, dg: str) -> str:
        sub = os.path.join(self.root, dg[:2])
        os.makedirs(sub, exist_ok=True)
        return os.path.join(sub, dg + ".json")

    def put(self, obj: Any) -> str:
        """Store an artifact (DATA only — closed forms / certificates / decider params). Returns its address."""
        dg = digest(obj)
        self._l1[dg] = obj
        p = self._path(dg)
        if not os.path.exists(p):
            with open(p, "w") as f:
                json.dump(obj, f, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return dg

    def get(self, dg: str) -> Optional[Any]:
        """O(1) lookup: L1 memory → L2 disk. None if absent."""
        if dg in self._l1:
            return self._l1[dg]
        p = self._path(dg)
        if os.path.exists(p):
            with open(p) as f:
                obj = json.load(f)
            self._l1[dg] = obj
            return obj
        return None

    def has(self, dg: str) -> bool:
        return dg in self._l1 or os.path.exists(self._path(dg))

    def count(self) -> int:
        n = 0
        for sub in os.listdir(self.root) if os.path.isdir(self.root) else []:
            d = os.path.join(self.root, sub)
            if os.path.isdir(d):
                n += sum(1 for f in os.listdir(d) if f.endswith(".json"))
        return n

    def clear(self) -> None:
        import shutil
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root, exist_ok=True)
        self._l1 = {}


# a process-wide default store
STORE = ArtifactStore()
