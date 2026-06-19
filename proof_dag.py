"""
PHASE 3.S2 — proof DAG: fine-grained incremental recheck (iCoq-style), only changed proofs re-verified.
=======================================================================================================
A change to one obligation should NOT re-verify the whole library. Each proof obligation is a node with a
content CHECKSUM and dependency edges; when a node's content changes, only IT and its TRANSITIVE DEPENDENTS
are rechecked (everything else keeps its cached verdict). This amortizes verification across edits.
(Extends spec_propagation.py's transport idea to a checksum-keyed dependency graph.)
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple


def _checksum(content: str) -> str:
    return hashlib.blake2b(content.encode("utf-8"), digest_size=8).hexdigest()


@dataclass
class Node:
    nid: str
    content: str
    deps: Tuple[str, ...]
    checksum: str = ""
    verified: Optional[bool] = None

    def __post_init__(self):
        self.checksum = _checksum(self.content)


class ProofDAG:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.dependents: Dict[str, Set[str]] = {}     # nid → set of nodes that depend on it

    def add(self, nid: str, content: str, deps: Tuple[str, ...] = ()):
        self.nodes[nid] = Node(nid, content, tuple(deps))
        self.dependents.setdefault(nid, set())
        for d in deps:
            self.dependents.setdefault(d, set()).add(nid)

    def verify_all(self, check_fn: Callable[[str], bool]) -> int:
        """Cold pass: verify every node, cache the verdict. Returns the number verified."""
        n = 0
        for node in self.nodes.values():
            node.verified = check_fn(node.content)
            n += 1
        return n

    def _transitive_dependents(self, nid: str) -> Set[str]:
        out, stack = set(), [nid]
        while stack:
            cur = stack.pop()
            for dep in self.dependents.get(cur, ()):
                if dep not in out:
                    out.add(dep)
                    stack.append(dep)
        return out

    def update(self, nid: str, new_content: str) -> Set[str]:
        """Change a node's content. If its checksum changed, mark it + all transitive dependents DIRTY.
        Returns the dirty set (the ONLY nodes that need rechecking)."""
        node = self.nodes[nid]
        new_sum = _checksum(new_content)
        if new_sum == node.checksum:
            return set()                               # no real change → nothing to recheck (checksum-keyed)
        node.content, node.checksum, node.verified = new_content, new_sum, None
        dirty = {nid} | self._transitive_dependents(nid)
        for d in dirty:
            self.nodes[d].verified = None              # invalidate cached verdicts of dependents
        return dirty

    def recheck(self, check_fn: Callable[[str], bool]) -> int:
        """Warm pass: recheck ONLY the nodes whose verdict was invalidated (verified is None)."""
        n = 0
        for node in self.nodes.values():
            if node.verified is None:
                node.verified = check_fn(node.content)
                n += 1
        return n


def _fresh_dag(n_nodes: int, fanout: int) -> Tuple["ProofDAG", Callable]:
    dag = ProofDAG()

    def check(content: str) -> bool:
        return "BAD" not in content                    # a trivial deterministic checker (stand-in)
    for i in range(n_nodes):
        deps = tuple(f"p{j}" for j in range(max(0, i - fanout), i))
        dag.add(f"p{i}", f"obligation-{i}", deps)
    return dag, check


def measure_incremental(n_nodes: int = 200, fanout: int = 3) -> dict:
    """Build a DAG (chain-with-fanout), verify all (cold), then report the recheck RATIO for BOTH a typical
    LEAF change (few dependents — the incremental win) AND the worst case ROOT change (many dependents). No
    cherry-picking: both are reported. Also a no-op edit (same checksum ⇒ ZERO recheck)."""
    # typical: change a near-leaf node (few transitive dependents)
    dag, check = _fresh_dag(n_nodes, fanout)
    dag.verify_all(check)
    leaf_dirty = dag.update(f"p{n_nodes - 2}", "obligation-LEAF-CHANGED")
    leaf_warm = dag.recheck(check)
    # worst case: change the root (all downstream dirty)
    dag2, check2 = _fresh_dag(n_nodes, fanout)
    dag2.verify_all(check2)
    root_dirty = dag2.update("p0", "obligation-ROOT-CHANGED")
    root_warm = dag2.recheck(check2)
    # no-op: identical content ⇒ checksum match ⇒ zero recheck
    dag3, check3 = _fresh_dag(n_nodes, fanout)
    dag3.verify_all(check3)
    noop_dirty = dag3.update("p10", "obligation-10")
    return {"n_nodes": n_nodes,
            "leaf_change": {"dirty": len(leaf_dirty), "rechecked": leaf_warm,
                            "ratio": round(leaf_warm / n_nodes, 3)},
            "root_change_worst": {"dirty": len(root_dirty), "rechecked": root_warm,
                                  "ratio": round(root_warm / n_nodes, 3)},
            "noop_edit_rechecked": len(noop_dirty),     # 0 — checksum match ⇒ nothing rechecked
            "note": "only the changed node + transitive dependents are rechecked (checksum-keyed); leaf change "
                    "≪ full, root change is the worst case, identical content ⇒ 0 (both reported, no cherry-pick)"}
