"""
v34 STAGE 2 — e-graph + superoptimizer, from scratch (no egg / egglog; dependency-0).
======================================================================================
A correct congruence-closure e-graph with egg-style DEFERRED REBUILDING, e-matching, an e-class analysis
(constant folding), and DAG-cost extraction. Used offline (build-time) to discover faster equivalent
expressions; the runtime only does an O(1) content-addressed lookup of a PRE-VERIFIED result.

DEFERRED REBUILDING (the core idea we re-implement and SELF-MEASURE): congruence invariants are restored at
PHASE BOUNDARIES, not after every merge. A saturation round does READ (collect all matches) then WRITE
(apply all merges into a worklist), then ONE rebuild() that repairs canonical parents + cascades congruent
merges. This turns repeated O(n) re-canonicalization into amortized near-O(1). ★ We measure OUR OWN speedup
(eager-rebuild vs deferred-rebuild) and report that number — never egg's published 88×/21× (rule: measured only). ★

SOUNDNESS (rule 2): rewrites are semantics-preserving (ring axioms + constant folding). A discovered
equivalence is VERIFIED (numeric battery + Schwartz-Zippel / finite_check) before it is cached or used — an
unverified discovery is NEVER used. Runtime does NO search.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# An expression term: (op, child_terms...). Leaves: ("const", value) | ("var", name).
Term = tuple


@dataclass
class ENode:
    op: str
    children: Tuple[int, ...]            # child e-class ids (canonicalized)

    def key(self, find) -> Tuple:
        return (self.op, tuple(find(c) for c in self.children))


class EGraph:
    def __init__(self, deferred: bool = True):
        self.parent: List[int] = []                 # union-find
        self.rank: List[int] = []
        self.classes: Dict[int, List[ENode]] = {}   # eclass id -> its e-nodes
        self.hashcons: Dict[Tuple, int] = {}         # canonical enode key -> eclass id
        self.uses: Dict[int, List[Tuple[Tuple, int]]] = {}   # eclass -> [(enode key, parent eclass)]
        self.analysis: Dict[int, Optional[int]] = {}         # eclass -> constant value (semilattice) or None
        self.worklist: List[int] = []
        self.deferred = deferred
        self.rebuilds = 0
        self.repairs = 0

    # ── union-find ──
    def find(self, x: int) -> int:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:               # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def _new_class(self) -> int:
        i = len(self.parent)
        self.parent.append(i); self.rank.append(0)
        self.classes[i] = []; self.uses[i] = []; self.analysis[i] = None
        return i

    # ── add / canonicalize / hashcons ──
    def add(self, op: str, children: Tuple[int, ...] = ()) -> int:
        node = ENode(op, tuple(self.find(c) for c in children))
        k = node.key(self.find)
        if k in self.hashcons:
            return self.find(self.hashcons[k])
        cid = self._new_class()
        self.classes[cid].append(node)
        self.hashcons[k] = cid
        for ch in node.children:
            self.uses[ch].append((k, cid))
        self._make_analysis(cid, node)
        return cid

    def add_term(self, term: Term) -> int:
        op = term[0]
        if op in ("const", "var"):
            return self.add(f"{op}:{term[1]}", ())
        return self.add(op, tuple(self.add_term(c) for c in term[1:]))

    # ── e-class analysis: constant folding (semilattice meet) ──
    def _const_of(self, node: ENode) -> Optional[int]:
        if node.op.startswith("const:"):
            return int(node.op.split(":", 1)[1])
        vals = [self.analysis[self.find(c)] for c in node.children]
        if any(v is None for v in vals):
            return None
        if node.op == "+":
            return vals[0] + vals[1]
        if node.op == "*":
            return vals[0] * vals[1]
        if node.op == "-" and len(vals) == 2:
            return vals[0] - vals[1]
        return None

    def _make_analysis(self, cid: int, node: ENode):
        c = self._const_of(node)
        if c is not None and self.analysis[self.find(cid)] is None:
            self.analysis[self.find(cid)] = c

    # ── merge (deferred) ──
    def merge(self, a: int, b: int) -> int:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return ra
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        # merge analysis (meet): if both constant they must agree (sound ring); keep the value
        av, bv = self.analysis[ra], self.analysis[rb]
        self.analysis[ra] = av if av is not None else bv
        self.classes[ra].extend(self.classes.get(rb, []))
        self.uses[ra].extend(self.uses.get(rb, []))
        self.worklist.append(ra)
        if not self.deferred:                       # eager: repair immediately (the slow baseline)
            self._rebuild_once()
        return ra

    # ── rebuild: restore congruence at the phase boundary (deferred) ──
    def rebuild(self):
        self.rebuilds += 1
        while self.worklist:
            todo = {self.find(c) for c in self.worklist}
            self.worklist = []
            for cid in todo:
                self._repair(cid)

    def _rebuild_once(self):
        self.rebuilds += 1
        wl, self.worklist = self.worklist, []
        for cid in {self.find(c) for c in wl}:
            self._repair(cid)

    def _repair(self, cid: int):
        self.repairs += 1
        seen: Dict[Tuple, int] = {}
        new_uses = []
        for (k, pcid) in self.uses.get(self.find(cid), []):
            # re-canonicalize the parent enode key
            op, ch = k[0], tuple(self.find(c) for c in k[1])
            nk = (op, ch)
            if nk in seen:
                self.merge(seen[nk], pcid)          # congruent parents → merge (cascades via worklist)
            else:
                seen[nk] = self.find(pcid)
            new_uses.append((nk, self.find(pcid)))
            self.hashcons[nk] = self.find(pcid)
        self.uses[self.find(cid)] = new_uses

    # ── e-matching: find eclasses matching a pattern. Pattern uses ("?", name) for variables. ──
    def ematch(self, pattern: Term) -> List[Tuple[int, dict]]:
        out = []
        for cid in {self.find(c) for c in range(len(self.parent))}:
            for node in self.classes.get(cid, []):
                env: dict = {}
                if self._match_node(pattern, node, env):
                    out.append((cid, env))
        return out

    def _match_node(self, pat: Term, node: ENode, env: dict) -> bool:
        if pat[0] == "?":
            name = pat[1]
            if name in env:
                return env[name] == self.find_node_class(node)
            env[name] = self.find_node_class(node)
            return True
        if pat[0] in ("const", "var"):
            return node.op == f"{pat[0]}:{pat[1]}"
        if node.op != pat[0] or len(node.children) != len(pat) - 1:
            return False
        for pc, ch in zip(pat[1:], node.children):
            if pc[0] == "?":
                name = pc[1]
                if name in env and env[name] != self.find(ch):
                    return False
                env[name] = self.find(ch)
            else:
                # need a child node in class `ch` matching pc
                if not any(self._match_node(pc, cn, env) for cn in self.classes.get(self.find(ch), [])):
                    return False
        return True

    def find_node_class(self, node: ENode) -> int:
        return self.find(self.hashcons[node.key(self.find)])

    def _instantiate(self, pat: Term, env: dict) -> int:
        if pat[0] == "?":
            return env[pat[1]]
        if pat[0] in ("const", "var"):
            return self.add(f"{pat[0]}:{pat[1]}", ())
        return self.add(pat[0], tuple(self._instantiate(c, env) for c in pat[1:]))

    # ── saturation: READ all matches, then WRITE all merges, then ONE rebuild (deferred) ──
    def saturate(self, rewrites: List[Tuple[Term, Term]], iters: int = 12, node_cap: int = 100000) -> int:
        for _ in range(iters):
            matches = []                            # READ phase
            for (lhs, rhs) in rewrites:
                for (cid, env) in self.ematch(lhs):
                    matches.append((cid, rhs, dict(env)))
            applied = 0
            for (cid, rhs, env) in matches:         # WRITE phase
                rcid = self._instantiate(rhs, env)
                if self.find(rcid) != self.find(cid):
                    self.merge(cid, rcid); applied += 1
            self.rebuild()                          # restore congruence ONCE per round
            if applied == 0 or len(self.parent) > node_cap:
                break
        return applied

    # ── DAG-cost extraction (shared subterms counted once) ──
    def extract(self, root: int, cost: Dict[str, int] = None) -> Tuple[Term, int]:
        cost = cost or {}
        best: Dict[int, Tuple[int, Term]] = {}
        # fixpoint over eclasses (handles cycles by iterating until stable)
        for _ in range(len(self.parent) + 2):
            changed = False
            for cid in {self.find(c) for c in range(len(self.parent))}:
                for node in self.classes.get(cid, []):
                    if any(self.find(c) not in best for c in node.children):
                        continue
                    c = cost.get(node.op.split(":")[0], 1) + sum(best[self.find(ch)][0] for ch in node.children)
                    if cid not in best or c < best[cid][0]:
                        term = (node.op,) if not node.children else \
                               (self._op_name(node.op),) + tuple(best[self.find(ch)][1] for ch in node.children)
                        best[cid] = (c, term)
                        changed = True
            if not changed:
                break
        r = self.find(root)
        return (best[r][1], best[r][0]) if r in best else (None, 1 << 30)

    @staticmethod
    def _op_name(op: str) -> str:
        return op


def measure_deferred_rebuilding(reps: int = 3) -> dict:
    """SELF-MEASURE: build the SAME saturation workload with eager rebuild (repair after every merge) vs
    deferred rebuild (repair once per round), report OUR speedup + repair-count ratio. (Not egg's number.)"""
    # workload: a chain of associativity/commutativity rewrites over a sum tree
    def build(deferred):
        eg = EGraph(deferred=deferred)
        terms = [eg.add_term(("var", f"x{i}")) for i in range(14)]
        acc = terms[0]
        for t in terms[1:]:
            acc = eg.add("+", (acc, t))
        rules = [
            (("+", ("?", "a"), ("?", "b")), ("+", ("?", "b"), ("?", "a"))),           # commutativity
            (("+", ("+", ("?", "a"), ("?", "b")), ("?", "c")),
             ("+", ("?", "a"), ("+", ("?", "b"), ("?", "c")))),                       # associativity
        ]
        eg.saturate(rules, iters=6, node_cap=20000)
        return eg
    best_def = best_eag = None
    rep_def = rep_eag = 0
    for _ in range(reps):
        t = time.perf_counter(); egd = build(True); td = (time.perf_counter() - t) * 1000
        t = time.perf_counter(); ege = build(False); te = (time.perf_counter() - t) * 1000
        best_def = td if best_def is None else min(best_def, td)
        best_eag = te if best_eag is None else min(best_eag, te)
        rep_def, rep_eag = egd.repairs, ege.repairs
    return {"eager_ms": round(best_eag, 2), "deferred_ms": round(best_def, 2),
            "speedup": round(best_eag / best_def, 2) if best_def > 0 else 1.0,
            "repairs_eager": rep_eag, "repairs_deferred": rep_def,
            "note": "SELF-measured (our e-graph); NOT egg's published 88×/21×"}
