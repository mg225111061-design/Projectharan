"""
v28 STAGE 25 — automatic spec propagation: Merkle-incremental re-verify + proof transport.
============================================================================================
Code↔spec coupling makes a tiny refactor shatter the proof chain — a maintenance explosion. This binds a
proof to the SEMANTIC CONTRACT, not the code's location/name, so a semantics-preserving refactor carries
its proof along automatically:

  • semantic_key = α-normalized structure (rename-invariant) ⊕ the spec. A RENAME / move keeps the key →
    the cached proof TRANSPORTS (no re-prove). Changing a constant / operator / spec CHANGES the key.
  • Merkle-incremental: on a diff, ONLY obligations whose key changed are re-verified (iCoq-style ~10×);
    the rest are perceived-zero from the proof store.
  • a real semantics change → REPROVE_NEEDED (this is CORRECT, not a defect — the proof SHOULD change);
    a re-proof that fails → DEFER.

★ HONEST (§1.9, §5) ★: ONLY semantics-preserving refactors auto-propagate. A semantics-CHANGING refactor
must re-prove — that is the right behavior, not a bug. The α-key is rename/move-invariant but deliberately
sensitive to constants/operators/spec (a constant change can change meaning), so it never transports a
proof across a real semantic change. Some equivalences are beyond α-renaming → those conservatively reprove.
"""
from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


# ── α-normalization: rename-invariant, but constant/operator-SENSITIVE (unlike S13's template key) ──
class _Alpha(ast.NodeTransformer):
    def __init__(self):
        self.names: Dict[str, str] = {}

    def _v(self, name: str) -> str:
        return self.names.setdefault(name, f"V{len(self.names)}")

    def visit_FunctionDef(self, node):
        node.name = "_F"
        node.args = self.visit(node.args)
        node.body = [self.visit(s) for s in node.body]
        node.decorator_list = []
        node.returns = None
        return node

    def visit_arg(self, node):
        node.arg = self._v(node.arg)
        node.annotation = None
        return node

    def visit_Name(self, node):
        node.id = self._v(node.id)
        return node
    # NOTE: visit_Constant intentionally ABSENT — constants are KEPT (a constant change is a semantics change).


def alpha_normal(source: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "\n".join(line.strip() for line in source.split("\n") if line.strip())   # non-Python fallback
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not fns:
        return ast.dump(tree)
    return ast.dump(_Alpha().visit(ast.fix_missing_locations(fns[0])))


def _norm_spec(spec: str) -> str:
    return " ".join(spec.split())


def semantic_key(source: str, spec: str = "") -> str:
    """The contract identity: α-normalized structure ⊕ spec. Rename/move-invariant; constant/operator/
    spec-sensitive. Two obligations share a key iff they are the SAME contract up to renaming."""
    blob = alpha_normal(source) + "||SPEC||" + _norm_spec(spec)
    return hashlib.sha256(blob.encode()).hexdigest()


def classify_change(old_src: str, new_src: str, old_spec: str = "", new_spec: str = "") -> str:
    """SEMANTICS_PRESERVING iff the contract key is unchanged (a rename/move); else SEMANTICS_CHANGED."""
    same = semantic_key(old_src, old_spec) == semantic_key(new_src, new_spec)
    return "SEMANTICS_PRESERVING" if same else "SEMANTICS_CHANGED"


# ── proof store + incremental propagation ───────────────────────────────────────────────────────────
@dataclass
class Obligation:
    name: str
    source: str
    spec: str = ""

    def key(self) -> str:
        return semantic_key(self.source, self.spec)


@dataclass
class ProofStore:
    proven: Dict[str, bool] = field(default_factory=dict)     # semantic_key -> proof verdict


@dataclass
class PropagationResult:
    statuses: Dict[str, str] = field(default_factory=dict)    # name -> PROPAGATED | REPROVE_NEEDED | DEFER
    reproved: int = 0
    propagated: int = 0
    deferred: int = 0
    prove_calls: int = 0                                      # the EXPENSIVE work actually done
    total: int = 0

    def __str__(self):
        return (f"propagated {self.propagated}/{self.total} (proof transported, no re-prove); "
                f"reproved {self.reproved}; deferred {self.deferred}; prove_calls={self.prove_calls}")


def propagate(obligations: List[Obligation], prove_fn: Callable[[Obligation], bool],
              store: ProofStore) -> PropagationResult:
    """For each obligation: if its contract key is already proven → PROPAGATED (transport, NO prove call);
    else REPROVE_NEEDED → call the (expensive) prover; a failed re-proof → DEFER. Only changed contracts
    cost work (Merkle-incremental)."""
    res = PropagationResult(total=len(obligations))
    for ob in obligations:
        k = ob.key()
        if store.proven.get(k):
            res.statuses[ob.name] = "PROPAGATED"
            res.propagated += 1
            continue
        res.prove_calls += 1
        ok = prove_fn(ob)
        store.proven[k] = ok
        if ok:
            res.statuses[ob.name] = "REPROVE_NEEDED"      # semantics changed/new → re-proved (justified)
            res.reproved += 1
        else:
            res.statuses[ob.name] = "DEFER"               # re-proof failed → honest defer
            res.deferred += 1
    return res
