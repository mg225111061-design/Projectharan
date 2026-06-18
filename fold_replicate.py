"""
v27 STAGE 13 — certified fold / replicate engine ("fold the PROCESS" across a large repo).
============================================================================================
Repeated structure is everywhere (GitHub: a large fraction of code is cloned; framework code is mostly
template). An LLM re-emits each of N near-identical instances token-by-token — cost grows linearly in N
(and decode is several× slower than prefill). HARAN does the opposite:

      PROVE THE PATTERN ONCE (parametrically, over the holes)  →  CERTIFY each of the N instances by a
      CHEAP per-instance side-condition check (sound universal instantiation), reusing the one proof.

This is the real mechanism behind proof reuse / parametric verification: if `∀ holes. Q(holes) → P(holes)`
is proven once, then for concrete holes h it suffices to check `Q(h)` (cheap arithmetic) to conclude
`P(h)` — NO re-proof. The Z3 solve is paid once; the N instances cost almost nothing. **As N grows the
gap to the LLM widens** — exactly the "scale advantage", and it is MEASURED here (one solve vs N solves).

Pieces:
  • structural_signature / group_clones — detect repeated structure (α-renamed, constant-blanked AST hash);
    the differing constants ARE the template holes.
  • Template + prove_template — a parametric spec (precond Q over holes, property P over holes+inputs)
    proven once with Z3 (z3_adapter). REFUTED ⇒ honestly NOT_A_TEMPLATE (with a counterexample).
  • replicate — prove once, certify N instances by checking Q(h); MEASURE fold-cost vs naive (N solves).
  • a Merkle-style summary cache (sig+spec hash) — a re-run re-proves only CHANGED templates (perceived-zero
    for unchanged ones); measured cold-vs-warm.
  • a repetition-rate gate — below 30% repeated, folding is DISABLED (honest: no benefit on novel code).

★ HONEST LIMITS (§1.3, §5) ★: (1) only the REPEATED part folds; novel logic is Ω(K) and stays per-instance
— blend is Amdahl-bounded by the novel fraction, NOT "instant". (2) Deriving the parametric SPEC from
arbitrary code is Rice-hard; the spec is SUPPLIED (clone detection finds the structure + the holes, the
property is given). (3) The crossover-N and multiples here are measured on the SYNTHETIC workload below;
for a real target repo the repetition rate / crossover is [TBD: 측정필요 — measure that repo].
"""
from __future__ import annotations

import ast
import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import z3_adapter as Z


# ── structural clone detection ──────────────────────────────────────────────────────────────────────
class _Canon(ast.NodeTransformer):
    """α-rename locals to V0,V1,… (first-occurrence) and blank numeric constants to a sentinel — so that
    clones that differ ONLY in names/constants collapse to one signature. Records the constants (holes)."""
    def __init__(self):
        self.names: Dict[str, str] = {}
        self.holes: List[object] = []

    def _v(self, name: str) -> str:
        if name not in self.names:
            self.names[name] = f"V{len(self.names)}"
        return self.names[name]

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

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            self.holes.append(node.value)
            return ast.copy_location(ast.Constant(value=0), node)
        return node


def structural_signature(source: str, fn_name: Optional[str] = None) -> Tuple[str, List[object]]:
    """Return (signature, holes). Two functions are clones iff their signatures are equal; `holes` are the
    numeric constants in occurrence order (the template's instantiation values)."""
    tree = ast.parse(source)
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    fn = next((f for f in fns if f.name == fn_name), None) if fn_name else (fns[0] if fns else None)
    if fn is None:
        return ("", [])
    c = _Canon()
    norm = c.visit(ast.fix_missing_locations(fn))
    return (ast.dump(norm, annotate_fields=True), c.holes)


def group_clones(sources: List[str]) -> Dict[str, List[Tuple[int, List[object]]]]:
    """Group source snippets by structural signature → {sig: [(index, holes), …]}."""
    groups: Dict[str, List[Tuple[int, List[object]]]] = {}
    for i, src in enumerate(sources):
        sig, holes = structural_signature(src)
        groups.setdefault(sig, []).append((i, holes))
    return groups


def repetition_rate(sources: List[str]) -> float:
    """Fraction of functions that belong to a clone family (group size ≥ 2)."""
    if not sources:
        return 0.0
    groups = group_clones(sources)
    repeated = sum(len(v) for v in groups.values() if len(v) >= 2)
    return repeated / len(sources)


def should_fold(sources: List[str], threshold: float = 0.30) -> bool:
    """Honest gate (§S13): below `threshold` repeated code, folding buys nothing → disable it."""
    return repetition_rate(sources) >= threshold


# ── parametric template + the one proof ─────────────────────────────────────────────────────────────
@dataclass
class Template:
    name: str
    holes: List[str]               # hole symbols, e.g. ["A", "B"]
    hole_types: Dict[str, str]     # {"A": "Int", ...}
    inputs: Dict[str, str]         # {"x1": "Int", "x2": "Int"}
    precond: List[str]             # side-conditions over HOLES only — the cheap per-instance check
    ensures: str                   # property over holes+inputs (proven once by Z3)
    input_hyp: List[str] = field(default_factory=list)   # hypotheses over INPUTS (part of the one proof)


@dataclass
class InstanceCert:
    holes: Dict[str, object]
    status: str                    # CERTIFIED | REJECTED
    failing: Optional[str] = None  # the side-condition that failed (if REJECTED)


@dataclass
class ReplicateVerdict:
    status: str                    # REPLICATED | NOT_A_TEMPLATE | NOT_REPEATED
    template_proof: str = ""
    instances: List[InstanceCert] = field(default_factory=list)
    n: int = 0
    certified: int = 0
    naive_ms: float = 0.0
    fold_ms: float = 0.0
    speedup: float = 1.0
    crossover_n: int = 0
    counterexample: Optional[dict] = None
    detail: str = ""

    def __str__(self):
        if self.status == "REPLICATED":
            return (f"REPLICATED: 1 template proof + {self.certified}/{self.n} certified instances; "
                    f"fold {self.fold_ms:.1f}ms vs naive {self.naive_ms:.1f}ms = {self.speedup:.1f}× "
                    f"(crossover N≈{self.crossover_n}); gap widens with N.")
        return f"{self.status} — {self.detail}"


_CACHE: Dict[str, Tuple[str, Optional[dict]]] = {}   # Merkle-style summary cache: sig+spec hash → proof


def reset_cache():
    _CACHE.clear()


def _spec_hash(t: Template) -> str:
    blob = repr((sorted(t.hole_types.items()), sorted(t.inputs.items()), sorted(t.precond),
                 sorted(t.input_hyp), t.ensures))
    return hashlib.sha256(blob.encode()).hexdigest()


def prove_template(t: Template, use_cache: bool = True) -> Tuple[str, Optional[dict], bool]:
    """Prove `∀ holes,inputs: (precond ∧ input_hyp) → ensures` ONCE (Z3). Returns (verdict, cx, cache_hit)."""
    h = _spec_hash(t)
    if use_cache and h in _CACHE:
        v, cx = _CACHE[h]
        return (v, cx, True)
    var_types = {**t.hole_types, **t.inputs}
    r = Z.prove_predicate(t.ensures, var_types, assumptions=list(t.precond) + list(t.input_hyp))
    _CACHE[h] = (r.verdict, r.counterexample)
    return (r.verdict, r.counterexample, False)


_SAFE = {"__builtins__": {}}


def _check_precond(precond: List[str], holes: Dict[str, object]) -> Optional[str]:
    """Cheap per-instance side-condition check (the only work done per instance once the template holds)."""
    for cond in precond:
        try:
            if not eval(cond, dict(_SAFE), dict(holes)):   # noqa: S307 — arithmetic over concrete ints
                return cond
        except Exception:  # noqa: BLE001
            return cond
    return None


def _subst(expr: str, holes: Dict[str, object]) -> str:
    """Substitute concrete hole values into an expression string for the naive per-instance re-proof."""
    node = ast.parse(expr, mode="eval")
    class _S(ast.NodeTransformer):
        def visit_Name(self, n):
            return ast.copy_location(ast.Constant(holes[n.id]), n) if n.id in holes else n
    return ast.unparse(ast.fix_missing_locations(_S().visit(node)))


def replicate(t: Template, instances: List[Dict[str, object]], measure: bool = True) -> ReplicateVerdict:
    """Prove the template ONCE, certify each instance by the cheap side-condition check, and MEASURE the
    fold strategy (1 solve + N checks) against the naive one (N independent solves)."""
    if len(instances) < 2:
        return ReplicateVerdict("NOT_REPEATED", n=len(instances),
                                detail="fewer than 2 instances — nothing to fold (honest)")
    t0 = time.perf_counter()
    verdict, cx, _hit = prove_template(t, use_cache=False)   # measure the genuine one-time proof cost
    if verdict != "PROVEN":
        return ReplicateVerdict("NOT_A_TEMPLATE", template_proof=verdict, counterexample=cx, n=len(instances),
                                detail=f"the parametric property does not hold ({verdict}) — no replication")
    certs: List[InstanceCert] = []
    for h in instances:
        fail = _check_precond(t.precond, h)
        certs.append(InstanceCert(h, "CERTIFIED" if fail is None else "REJECTED", fail))
    fold_ms = (time.perf_counter() - t0) * 1000
    certified = sum(1 for c in certs if c.status == "CERTIFIED")
    proof = (f"template `{t.name}`: PROVEN ∀{list(t.hole_types)},{list(t.inputs)}: "
             f"({' ∧ '.join(t.precond)}) → {t.ensures}. Each instance certified by checking the precond on "
             f"its concrete holes (sound universal instantiation) — the Z3 solve is paid ONCE.")
    v = ReplicateVerdict("REPLICATED", template_proof=proof, instances=certs, n=len(instances),
                         certified=certified, fold_ms=fold_ms)
    if measure:
        # naive baseline: verify each instance INDEPENDENTLY from scratch (one Z3 solve per instance)
        t1 = time.perf_counter()
        for h in instances:
            ens = _subst(t.ensures, h)
            asm = [_subst(c, h) for c in t.precond] + list(t.input_hyp)
            Z.prove_predicate(ens, dict(t.inputs), assumptions=asm)
        v.naive_ms = (time.perf_counter() - t1) * 1000
        v.speedup = v.naive_ms / fold_ms if fold_ms > 0 else 1.0
        # crossover N: smallest N where (1 solve + N·check) < (N·solve). check≪solve ⇒ N≈1 once proven.
        per_solve = v.naive_ms / len(instances)
        per_check = max((fold_ms - per_solve) / len(instances), 0.0) + 1e-9
        v.crossover_n = max(1, int(per_solve / max(per_solve - per_check, 1e-9)))
    return v


def fold_repo(items: List[Tuple[Template, List[Dict[str, object]]]], reset: bool = True) -> Dict[str, object]:
    """Process many (template, instances) families with the summary cache; re-running re-proves only the
    CHANGED templates. Returns counts + cold/warm wall-clock (perceived-zero re-verify for unchanged)."""
    if reset:
        reset_cache()
    t = time.perf_counter()
    proved = cached = 0
    for tmpl, _inst in items:
        _v, _cx, hit = prove_template(tmpl, use_cache=True)
        cached += int(hit)
        proved += int(not hit)
    return {"templates": len(items), "proved": proved, "cached": cached,
            "ms": (time.perf_counter() - t) * 1000}
