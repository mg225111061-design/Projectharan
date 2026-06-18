"""
v27 STAGE 17a — equality saturation (e-graph) with a Z3-certified optimal extraction.
======================================================================================
An e-graph compactly represents MANY equivalent forms of a term at once; we saturate it with a small set
of SOUND ring rewrites (x*2 = x+x, x*1 = x, x+0 = x, x*0 = 0, commutativity, constant folding, and
factoring a*b + a*c = a*(b+c)), then EXTRACT the lowest-cost (fewest-node) equivalent term — egg-style.

★ SOUNDNESS (§1.8) ★: every rewrite is equality-preserving, and on top of that the extracted term is
CHECKED for equivalence to the input by Z3 (∀ vars: input == output). We only report OPTIMIZED if that
proof succeeds — a wrong rewrite can never escape (kernel-checked). Cost reduction is MEASURED (node count).

★ HONEST (§5) ★: the rule set is small (a structured-arithmetic fragment), not egg's full library — egg's
21×/88× are saturation-engine speedups on large rule systems, NOT claimed here; we report OUR measured node
reduction on OUR inputs. Only structured pieces benefit (§0.4 TENSOR_LA path); unstructured terms return
NO_GAIN honestly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import z3

# term := ("+", t, t) | ("*", t, t) | ("var", name) | ("const", int)
Term = tuple


class EGraph:
    def __init__(self):
        self.parent: Dict[int, int] = {}
        self.nodes: Dict[int, set] = {}         # eclass id -> set of e-nodes
        self.hashcons: Dict[tuple, int] = {}    # canonical e-node -> eclass id
        self._cnt = 0

    # union-find
    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def _new_class(self) -> int:
        i = self._cnt
        self._cnt += 1
        self.parent[i] = i
        self.nodes[i] = set()
        return i

    def _canon(self, enode: tuple) -> tuple:
        op = enode[0]
        if op in ("+", "*"):
            return (op, self.find(enode[1]), self.find(enode[2]))
        return enode                            # leaf: ("var", name) | ("const", v)

    def add_enode(self, enode: tuple) -> int:
        enode = self._canon(enode)
        if enode in self.hashcons:
            return self.find(self.hashcons[enode])
        c = self._new_class()
        self.nodes[c].add(enode)
        self.hashcons[enode] = c
        return c

    def add(self, term: Term) -> int:
        op = term[0]
        if op in ("+", "*"):
            return self.add_enode((op, self.add(term[1]), self.add(term[2])))
        return self.add_enode(term)

    def merge(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a == b:
            return
        self.nodes[a] |= self.nodes[b]
        self.parent[b] = a

    def rebuild(self) -> None:
        """Restore the congruence invariant: re-canonicalize the hashcons and merge congruent nodes."""
        changed = True
        while changed:
            changed = False
            self.hashcons = {}
            classes = {}
            for c in list(self.parent):
                if self.find(c) != c:
                    continue
                classes.setdefault(c, set())
            new_nodes: Dict[int, set] = {c: set() for c in classes}
            for c in list(self.parent):
                rc = self.find(c)
                if rc not in new_nodes:
                    new_nodes[rc] = set()
                for n in self.nodes.get(c, set()):
                    cn = self._canon(n)
                    new_nodes[rc].add(cn)
                    if cn in self.hashcons and self.find(self.hashcons[cn]) != rc:
                        self.merge(self.hashcons[cn], rc)
                        changed = True
                    self.hashcons[cn] = self.find(rc)
            self.nodes = {}
            for c in list(self.parent):
                if self.find(c) == c:
                    self.nodes[c] = set()
            for c in list(self.parent):
                rc = self.find(c)
                self.nodes.setdefault(rc, set())
                for n in new_nodes.get(c, set()):
                    self.nodes[rc].add(self._canon(n))

    # helpers
    def const_val(self, c: int) -> Optional[int]:
        for n in self.nodes[self.find(c)]:
            if n[0] == "const":
                return n[1]
        return None

    def _const_class(self, v: int) -> int:
        return self.add_enode(("const", v))


_RULE_NAMES = ["comm", "mul1", "mul0", "add0", "mul2", "const_fold", "factor"]


def _apply_rules(eg: EGraph) -> bool:
    changed = False
    classes = [c for c in list(eg.parent) if eg.find(c) == c]
    for c in classes:
        for n in list(eg.nodes[eg.find(c)]):
            op = n[0]
            if op == "*":
                _, A, B = n
                eg.nodes[eg.find(c)].add(eg._canon(("*", B, A)))     # commutativity
                va, vb = eg.const_val(A), eg.const_val(B)
                if vb == 1:
                    eg.merge(c, A); changed = True
                elif va == 1:
                    eg.merge(c, B); changed = True
                if vb == 0 or va == 0:
                    eg.merge(c, eg._const_class(0)); changed = True
                if va is not None and vb is not None:
                    eg.merge(c, eg._const_class(va * vb)); changed = True
                if vb == 2:
                    eg.merge(c, eg.add_enode(("+", A, A))); changed = True
                if va == 2:
                    eg.merge(c, eg.add_enode(("+", B, B))); changed = True
            elif op == "+":
                _, M, N = n
                eg.nodes[eg.find(c)].add(eg._canon(("+", N, M)))     # commutativity
                vm, vn = eg.const_val(M), eg.const_val(N)
                if vn == 0:
                    eg.merge(c, M); changed = True
                elif vm == 0:
                    eg.merge(c, N); changed = True
                if vm is not None and vn is not None:
                    eg.merge(c, eg._const_class(vm + vn)); changed = True
                # factoring: M ∋ (*,A,B), N ∋ (*,A,C) with same A  ⇒  A*(B+C)
                for mn in [x for x in eg.nodes[eg.find(M)] if x[0] == "*"]:
                    for nn in [y for y in eg.nodes[eg.find(N)] if y[0] == "*"]:
                        for (a1, b1) in ((mn[1], mn[2]), (mn[2], mn[1])):
                            for (a2, c2) in ((nn[1], nn[2]), (nn[2], nn[1])):
                                if eg.find(a1) == eg.find(a2):
                                    fac = eg.add_enode(("*", a1, eg.add_enode(("+", b1, c2))))
                                    eg.merge(c, fac); changed = True
    return changed


def saturate(eg: EGraph, max_iters: int = 30) -> None:
    for _ in range(max_iters):
        ch = _apply_rules(eg)
        eg.rebuild()
        if not ch:
            break


def extract(eg: EGraph, root: int) -> Term:
    """Lowest-cost (fewest-node) term in the root's e-class (cycle-safe)."""
    best: Dict[int, Tuple[int, Term]] = {}

    def cost(c: int, stack: frozenset) -> Tuple[int, Term]:
        c = eg.find(c)
        if c in best:
            return best[c]
        if c in stack:
            return (10 ** 9, ("var", "?"))
        s2 = stack | {c}
        bestcost, bestterm = 10 ** 9, ("var", "?")
        for n in eg.nodes[c]:
            if n[0] in ("+", "*"):
                lc, lt = cost(n[1], s2)
                rc, rt = cost(n[2], s2)
                tc, tt = 1 + lc + rc, (n[0], lt, rt)
            else:
                tc, tt = 1, n
            if tc < bestcost:
                bestcost, bestterm = tc, tt
        if stack == frozenset():
            best[c] = (bestcost, bestterm)
        return (bestcost, bestterm)

    return cost(root, frozenset())[1]


def term_size(t: Term) -> int:
    return 1 if t[0] in ("var", "const") else 1 + term_size(t[1]) + term_size(t[2])


def _to_z3(t: Term, env: Dict[str, z3.ArithRef]):
    if t[0] == "const":
        return z3.IntVal(t[1])
    if t[0] == "var":
        return env.setdefault(t[1], z3.Int(t[1]))
    l, r = _to_z3(t[1], env), _to_z3(t[2], env)
    return l + r if t[0] == "+" else l * r


def _vars(t: Term, acc: set) -> set:
    if t[0] == "var":
        acc.add(t[1])
    elif t[0] in ("+", "*"):
        _vars(t[1], acc); _vars(t[2], acc)
    return acc


@dataclass
class OptVerdict:
    status: str            # OPTIMIZED | NO_GAIN | UNSOUND_BLOCKED
    original: Term = None
    optimized: Term = None
    before: int = 0
    after: int = 0
    rules: List[str] = field(default_factory=lambda: list(_RULE_NAMES))
    detail: str = ""

    def __str__(self):
        if self.status == "OPTIMIZED":
            return f"OPTIMIZED {self.before}→{self.after} nodes (Z3-equivalent): {fmt(self.optimized)}"
        return f"{self.status} — {self.detail}"


def fmt(t: Term) -> str:
    if t[0] == "const":
        return str(t[1])
    if t[0] == "var":
        return t[1]
    return f"({fmt(t[1])} {t[0]} {fmt(t[2])})"


def optimize(term: Term, max_iters: int = 30) -> OptVerdict:
    """Saturate, extract the cheapest form, and CERTIFY equivalence with Z3 before reporting OPTIMIZED."""
    eg = EGraph()
    root = eg.add(term)
    saturate(eg, max_iters)
    best = extract(eg, root)
    before, after = term_size(term), term_size(best)
    # ★ kernel check ★: prove ∀ vars: term == best (a wrong rewrite can never pass)
    env: Dict[str, z3.ArithRef] = {}
    for v in _vars(term, set()) | _vars(best, set()):
        env[v] = z3.Int(v)
    s = z3.Solver()
    s.add(_to_z3(term, env) != _to_z3(best, env))
    if s.check() != z3.unsat:
        return OptVerdict("UNSOUND_BLOCKED", term, term, before, before,
                          detail="extracted form not Z3-equivalent — rejected (should never happen)")
    if after >= before:
        return OptVerdict("NO_GAIN", term, best, before, after, detail=f"no smaller equivalent form ({before} nodes)")
    return OptVerdict("OPTIMIZED", term, best, before, after)
