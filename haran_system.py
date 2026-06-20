"""
v40 PHASE 8 — verifier suite + system skeleton (the Maxwell-demon architecture, sound).
=========================================================================================
Genuinely-implementable, sound, testable pieces of §PHASE-8:
  • 49 Merkle commitment kernel : O(log n) inclusion proof + verify (vs O(n) rescan), EXACT.
  • CircuitBreaker : repeated verification failures ⇒ OPEN ⇒ return DECLINE immediately. ★ NEVER a speculative
    EXACT while open ★ (half-open probes one call to test recovery). The §5 "no speculative EXACT" rule, as code.
  • MVCCCache : immutable multi-version certificate cache keyed by (key, source-hash). A source change ⇒ a
    different hash ⇒ a clean miss (no stale cert). VACUUM reclaims superseded versions.
  • level-triggered reconciler : reconcile from the CURRENT state (idempotent — reconcile∘reconcile = reconcile),
    with an exponential-backoff retry schedule. (write→verify→fix as a K8s-style reconciler.)
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import kernel_verdict as KV
import kernel_router as R


# ── 49 · Merkle commitment: O(log n) inclusion proof + verify, EXACT ──────────────────────────────────
def _h(b: bytes) -> bytes:
    return hashlib.blake2b(b, digest_size=16).digest()


def _leaf_hash(x: Any) -> bytes:
    return _h(b"L" + repr(x).encode())


def _merkle_tree(leaves: List[Any]) -> List[List[bytes]]:
    level = [_leaf_hash(x) for x in leaves]
    tree = [level]
    while len(level) > 1:
        if len(level) % 2:
            level = level + [level[-1]]               # duplicate last (standard padding)
        level = [_h(b"N" + level[i] + level[i + 1]) for i in range(0, len(level), 2)]
        tree.append(level)
    return tree


def _merkle_proof(tree: List[List[bytes]], index: int) -> List[Tuple[str, bytes]]:
    proof = []
    idx = index
    for level in tree[:-1]:
        sib = idx ^ 1
        if sib >= len(level):
            sib = idx                                 # padded duplicate
        proof.append(("R" if idx % 2 == 0 else "L", level[sib]))
        idx //= 2
    return proof


def _merkle_verify(leaf: Any, index: int, proof: List[Tuple[str, bytes]], root: bytes) -> bool:
    h = _leaf_hash(leaf)
    for side, sib in proof:
        h = _h(b"N" + h + sib) if side == "R" else _h(b"N" + sib + h)
    return h == root


def _merkle_detect(d: Any) -> bool:
    return isinstance(d, dict) and d.get("kind") == "merkle_prove" and isinstance(d.get("leaves"), list) and "index" in d


def _merkle_run(d: Any, **kw) -> KV.Verdict:
    leaves, idx = d["leaves"], int(d["index"])
    if not leaves or not (0 <= idx < len(leaves)):
        return KV.decline("merkle needs non-empty leaves and in-range index", "merkle")
    tree = _merkle_tree(leaves)
    root = tree[-1][0]
    proof = _merkle_proof(tree, idx)
    ok = _merkle_verify(leaves[idx], idx, proof, root)        # fast EXACT cert: recompute root from leaf+proof
    cert = KV.Cert(KV.EXACT, "merkle_recompute", passed=ok, check_cost="O(log n)",
                   detail=f"inclusion proof of {len(proof)} sibling hashes recomputes the root (collision-"
                          f"resistant blake2b); membership verified in O(log n) vs O(n) rescan")
    if not ok:
        return KV.decline("merkle proof did not recompute the root", "merkle")
    return KV.exact({"root": root.hex(), "proof_len": len(proof)}, "merkle", "O(log n) proof+verify", cert)


# ── CircuitBreaker — never a speculative EXACT while OPEN ──────────────────────────────────────────────
@dataclass
class CircuitBreaker:
    fail_threshold: int = 3
    state: str = "CLOSED"                              # CLOSED | OPEN | HALF_OPEN
    failures: int = 0

    def call(self, verify_fn: Callable[[], KV.Verdict]) -> KV.Verdict:
        if self.state == "OPEN":
            return KV.decline("circuit OPEN (repeated verification failures) — refusing; NO speculative EXACT", "breaker")
        v = verify_fn()
        if v.status != KV.DECLINE:
            self.failures = 0
            self.state = "CLOSED"                      # a passing verification (incl. from HALF_OPEN) closes it
            return v
        # a DECLINE counts as a failure
        self.failures += 1
        if self.state == "HALF_OPEN" or self.failures >= self.fail_threshold:
            self.state = "OPEN"
        return v

    def half_open(self):
        if self.state == "OPEN":
            self.state = "HALF_OPEN"


# ── MVCCCache — immutable, multi-version, source-hash keyed, with VACUUM ───────────────────────────────
@dataclass
class MVCCCache:
    _store: Dict[str, List[Tuple[str, Any, int]]] = field(default_factory=dict)   # key → [(src_hash, value, ver)]
    _ver: int = 0

    @staticmethod
    def source_hash(source: str) -> str:
        return hashlib.blake2b(source.encode(), digest_size=8).hexdigest()

    def put(self, key: str, source: str, value: Any) -> int:
        self._ver += 1
        self._store.setdefault(key, []).append((self.source_hash(source), value, self._ver))   # immutable append
        return self._ver

    def get(self, key: str, source: str) -> Optional[Any]:
        sh = self.source_hash(source)
        for (h, v, _ver) in reversed(self._store.get(key, [])):   # latest matching source-hash
            if h == sh:
                return v
        return None                                                # source changed ⇒ clean miss (no stale cert)

    def vacuum(self) -> int:
        """Reclaim superseded versions: keep only the latest version per (key, source-hash)."""
        reclaimed = 0
        for key, versions in self._store.items():
            latest: Dict[str, Tuple[str, Any, int]] = {}
            for rec in versions:
                h = rec[0]
                if h not in latest or rec[2] > latest[h][2]:
                    latest[h] = rec
            reclaimed += len(versions) - len(latest)
            self._store[key] = sorted(latest.values(), key=lambda r: r[2])
        return reclaimed


# ── level-triggered reconciler (idempotent) + exponential backoff ─────────────────────────────────────
def reconcile(current: Dict, desired: Dict, apply_fn: Callable[[str, Any], None]) -> List[str]:
    """Compute the diff from the CURRENT observed state to DESIRED and apply it. Idempotent: when current==
    desired nothing is applied, so reconcile∘reconcile = reconcile (level-triggered, not edge-triggered)."""
    changed = []
    for k, want in desired.items():
        if current.get(k) != want:
            apply_fn(k, want)
            changed.append(k)
    return changed


def backoff_schedule(n: int, base_ms: float = 2.0, cap_ms: float = 30000.0) -> List[float]:
    return [min(cap_ms, base_ms * (2 ** i)) for i in range(n)]


def register_all():
    R.register(R.Kernel(49, "merkle", "G",
                        "requires leaves ∧ in-range index  ensures inclusion proof verifies ∧ grade=EXACT ∧ "
                        "cost=O(log n) proof+verify",
                        _merkle_detect, _merkle_run))


register_all()


# ── dogfood: the system pieces compose correctly (zero human audit) ───────────────────────────────────
def self_check() -> dict:
    # circuit breaker: 3 DECLINEs open it; while OPEN it returns DECLINE (never EXACT); half-open + a pass closes
    cb = CircuitBreaker(fail_threshold=3)
    for _ in range(3):
        cb.call(lambda: KV.decline("verify failed", "x"))
    open_decl = cb.call(lambda: KV.exact(1, "x", "O(1)", KV.Cert(KV.EXACT, "k", True)))   # would-be EXACT
    no_speculative = (cb.state == "OPEN" and open_decl.status == KV.DECLINE)
    cb.half_open()
    closed = cb.call(lambda: KV.exact(1, "x", "O(1)", KV.Cert(KV.EXACT, "k", True)))
    breaker_ok = no_speculative and closed.status == KV.EXACT and cb.state == "CLOSED"

    # MVCC: source change ⇒ clean miss; same source ⇒ hit; vacuum reclaims superseded
    c = MVCCCache()
    c.put("goal1", "src v1", "PROVEN")
    hit = c.get("goal1", "src v1") == "PROVEN"
    miss = c.get("goal1", "src v2 (edited)") is None          # source changed ⇒ no stale cert
    c.put("goal1", "src v1", "PROVEN")                         # a re-put (new version, same source)
    reclaimed = c.vacuum() >= 1
    mvcc_ok = hit and miss and reclaimed

    # reconciler idempotency: reconcile twice applies nothing the second time
    applied: List[str] = []
    cur, des = {"a": 1}, {"a": 2, "b": 3}
    reconcile(cur, des, lambda k, v: (cur.__setitem__(k, v), applied.append(k)))
    second = reconcile(cur, des, lambda k, v: applied.append("SHOULD_NOT_HAPPEN"))
    recon_ok = (cur == des and second == [] and "SHOULD_NOT_HAPPEN" not in applied)

    return {"breaker_no_speculative_exact": breaker_ok, "mvcc_source_keyed": mvcc_ok,
            "reconciler_idempotent": recon_ok,
            "all_pass": breaker_ok and mvcc_ok and recon_ok}
