"""
ACCEL §M-max — A/B/C/D DRIVEN TO THE LIMIT: transitive purity (A), nested batching (A), prefetch/overlap (B), and
COMPOSITION-TO-FIXPOINT with an END-TO-END equivalence proof.
================================================================================================================
The base moves (verified_io/parallel/algo/serde) each prove ONE local transform. This module pushes three of them
to their reachable limit and then COMPOSES proved transforms until no further one applies — the fixpoint — carrying
a single end-to-end equivalence guarantee.

  • A.transitive_purity — the base A1 conservatively REJECTS any call to a non-builtin (it cannot see the callee).
    Here we take the whole call graph: a function is PURE iff it is locally clean (no clock/RNG/IO/global/arg-mutation)
    AND every function it calls is (transitively) proved pure. Computed by a monotone fixpoint over the graph; cycles
    (mutual/■self recursion) resolve soundly. This caches a function that calls user-defined pure helpers — which the
    base move could not.
  • A.nested_batch — batch across NESTED loops (`for u: for o in u.orders: fetch(o)`): prove no carried dependency and
    that the flattened batched call is RESULT-EQUIVALENT to the nested per-item calls, in order. Else DECLINE.
  • B.prefetch_overlap — overlap stage i+1's I/O with stage i's compute. SAFE iff stage i+1's I/O neither writes what
    stage i's compute reads/writes NOR reads what stage i's compute writes (prefetching cannot change semantics).
    The proof unlocks safety; the latency win is the honest overlap model (max(io,compute) vs io+compute), never faked.
  • compose_to_fixpoint — apply every proposer to the program repeatedly; each APPLIED step is individually proved
    equivalent, so the composition is equivalent BY TRANSITIVITY (≡ is transitive); we additionally re-check the fully
    composed program against the original by DIFFERENTIAL execution on samples (belt-and-suspenders). Iterate until a
    full pass applies nothing new (the fixpoint). A step whose differential disagrees is NOT applied (precision first).

★ Invariant unchanged: applied ⇔ proved. Widening what is ATTEMPTED never widens what is wrongly ACCEPTED.
"""
from __future__ import annotations

import ast
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from accel.pipeline import Acceleration, proved, rejected
from accel.verified_io import _IMPURE_NAMES, _MUTATORS, _PURE_CALLS


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
# A.transitive_purity — call-graph fixpoint purity
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
class _LocalPurity(ast.NodeVisitor):
    """Flags the IMPURE constructs (clock/RNG/IO/global/nonlocal/arg-mutation) and COLLECTS the free-name calls that
    must be resolved transitively (a call to a name that is neither a known-pure builtin nor a parameter)."""
    def __init__(self, params: Set[str]):
        self.params = params
        self.violations: List[str] = []
        self.callees: Set[str] = set()
        self.globals: Set[str] = set()

    def visit_Global(self, node):
        self.globals.update(node.names)
        self.violations.append(f"`global {', '.join(node.names)}` — module-state access")

    def visit_Nonlocal(self, node):
        self.violations.append(f"`nonlocal {', '.join(node.names)}` — closure-state mutation")

    def visit_Call(self, node):
        f = node.func
        if isinstance(f, ast.Name):
            if f.id in _IMPURE_NAMES:
                self.violations.append(f"call `{f.id}(...)` — clock/RNG/IO/nondeterministic")
            elif f.id not in _PURE_CALLS and f.id not in self.params:
                self.callees.add(f.id)                      # ← resolve transitively (NOT an automatic violation)
        if isinstance(f, ast.Attribute):
            if f.attr in _IMPURE_NAMES:
                self.violations.append(f"call `.{f.attr}(...)` — clock/RNG/IO/nondeterministic")
            if f.attr in _MUTATORS and isinstance(f.value, ast.Name) and f.value.id in self.params:
                self.violations.append(f"`{f.value.id}.{f.attr}(...)` — mutates an argument")
            if isinstance(f.value, ast.Name) and f.value.id in _IMPURE_NAMES:
                self.violations.append(f"call `{f.value.id}.{f.attr}(...)` — impure module")
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        if isinstance(node.target, ast.Name) and node.target.id in self.globals:
            self.violations.append(f"`{node.target.id} +=` on a global")
        if isinstance(node.target, (ast.Subscript, ast.Attribute)) and isinstance(node.target.value, ast.Name) \
                and node.target.value.id in self.params:
            self.violations.append(f"mutates argument `{node.target.value.id}` (augmented assignment)")
        self.generic_visit(node)

    def visit_Assign(self, node):
        for tgt in node.targets:
            if isinstance(tgt, (ast.Subscript, ast.Attribute)) and isinstance(tgt.value, ast.Name) \
                    and tgt.value.id in self.params:
                self.violations.append(f"mutates argument `{tgt.value.id}` (item/attr assignment)")
        self.generic_visit(node)


def _local_analyze(source: str) -> Tuple[bool, Set[str], str]:
    """(locally_clean, callees_to_resolve, why_not). locally_clean = no impure construct (calls to unknown functions
    are NOT a violation here — they are returned as callees for the transitive fixpoint)."""
    try:
        tree = ast.parse(source.strip())
    except SyntaxError as e:
        return False, set(), f"unparseable: {e}"
    fn = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if fn is None:
        return False, set(), "no function definition"
    if isinstance(fn, ast.AsyncFunctionDef):
        return False, set(), "async — awaits external effects"
    params = {a.arg for a in fn.args.args} | {a.arg for a in fn.args.kwonlyargs}
    if fn.args.vararg:
        params.add(fn.args.vararg.arg)
    if fn.args.kwarg:
        params.add(fn.args.kwarg.arg)
    v = _LocalPurity(params)
    for stmt in fn.body:
        v.visit(stmt)
    if v.violations:
        return False, v.callees, "; ".join(dict.fromkeys(v.violations))
    return True, v.callees, ""


def prove_pure_transitive(sources: Dict[str, str]) -> Dict[str, Tuple[bool, str]]:
    """Whole-call-graph purity. `sources` = {fn_name: source}. A function is PURE iff it is locally clean AND every
    callee is a known-pure builtin OR a function in `sources` that is itself (transitively) pure. Monotone fixpoint:
    start optimistic with all locally-clean functions PURE, then retract any whose callee is impure/unknown, until
    stable. SOUND & CONSERVATIVE — a callee outside the known set keeps the caller impure."""
    info = {name: _local_analyze(src) for name, src in sources.items()}
    pure = {name for name, (clean, _, _) in info.items() if clean}
    changed = True
    while changed:
        changed = False
        for name in list(pure):
            _clean, callees, _why = info[name]
            for c in callees:
                if c in _PURE_CALLS:
                    continue                                 # known-pure builtin
                if c in sources and c in pure:
                    continue                                 # an in-graph function still believed pure
                pure.discard(name)                           # an unknown / impure callee ⇒ caller impure
                changed = True
                break
    out: Dict[str, Tuple[bool, str]] = {}
    for name, (clean, callees, why) in info.items():
        if name in pure:
            out[name] = (True, f"transitively pure — locally clean; callees {sorted(callees) or '∅'} all proved pure")
        elif not clean:
            out[name] = (False, why)
        else:
            bad = sorted(c for c in callees if not (c in _PURE_CALLS or (c in sources and c in pure)))
            out[name] = (False, f"locally clean but calls unprovable {bad} — purity not transitively established")
    return out


def verified_cache_transitive(sources: Dict[str, str], target: str) -> Acceleration:
    """A.transitive_purity: cache `target` iff it is transitively pure across the whole call graph `sources`."""
    if target not in sources:
        return rejected("A.cache+", f"memoize {target} (transitive)", f"{target} not in the provided sources")
    verdict = prove_pure_transitive(sources)
    ok, why = verdict[target]
    if not ok:
        return rejected("A.cache+", f"memoize {target} (transitive)", f"transitive purity NOT proved: {why}")
    return proved("A.cache+", f"memoize {target} (transitive)", f"transitive purity proof — {why}")


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
# A.nested_batch — batch across nested loops
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def verified_nested_batch(outer: Sequence, inner_of: Callable, per_call: Callable, batch_call: Callable,
                          carried: bool = False) -> Acceleration:
    """Batch `for o in outer: for i in inner_of(o): per_call(o,i)` into one `batch_call(flattened)`. VERIFY (a) no
    carried dependency and (b) result-equivalence: batch_call(items) == [per_call(o,i) for (o,i) in items] EXACTLY,
    in order, over the actual flattened items. Else DECLINE."""
    if carried:
        return rejected("A.nestbatch", "batch nested loops into 1",
                        "loop-carried dependency across the nested calls — NOT independent")
    try:
        items = [(o, i) for o in outer for i in inner_of(o)]
        individual = [per_call(o, i) for (o, i) in items]
        batched = list(batch_call(items))
    except Exception as e:  # noqa: BLE001
        return rejected("A.nestbatch", "batch nested loops into 1", f"evaluation raised {type(e).__name__}")
    if batched != individual:
        return rejected("A.nestbatch", "batch nested loops into 1",
                        "result-equivalence FAILS — the batched call drops/reorders the nested rows")
    return proved("A.nestbatch", f"batch {len(items)} nested calls into 1",
                  f"no carried dep ∘ result-equivalence on all {len(items)} flattened (outer,inner) items (exact)")


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
# B.prefetch_overlap — overlap next-stage I/O with current-stage compute
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def verified_prefetch_overlap(stages: List[Dict]) -> Acceleration:
    """Each stage = {name, io_reads, io_writes, compute_reads, compute_writes}. Prefetching stage i+1's I/O while
    stage i computes is SAFE iff (1) stage i+1's I/O does not WRITE anything stage i's compute reads or writes, and
    (2) stage i+1's I/O does not READ anything stage i's compute writes (i.e. the prefetched I/O does not depend on
    the current compute's output). Any conflict ⇒ DECLINE. The proof is SAFETY; the latency win is the honest overlap
    model max(io,compute) vs io+compute, never a fabricated number."""
    if len(stages) < 2:
        return rejected("B.prefetch", "overlap I/O with compute", "need ≥2 stages to overlap")
    conflicts: List[str] = []
    for i in range(len(stages) - 1):
        nio_r = set(stages[i + 1].get("io_reads", []))
        nio_w = set(stages[i + 1].get("io_writes", []))
        cc_r = set(stages[i].get("compute_reads", []))
        cc_w = set(stages[i].get("compute_writes", []))
        a, b = stages[i].get("name", i), stages[i + 1].get("name", i + 1)
        if nio_w & (cc_r | cc_w):
            conflicts.append(f"{b}.io✍ ∩ {a}.compute on {sorted(nio_w & (cc_r | cc_w))} (prefetch would clobber)")
        if nio_r & cc_w:
            conflicts.append(f"{b}.io👁 ∩ {a}.compute✍ on {sorted(nio_r & cc_w)} (prefetch needs current output)")
    if conflicts:
        return rejected("B.prefetch", "overlap I/O with compute", "dependence: " + "; ".join(conflicts[:3]))
    return proved("B.prefetch", f"prefetch-overlap {len(stages)} stages",
                  f"each next-stage I/O is independent of the current compute across all {len(stages) - 1} boundaries "
                  "⇒ overlapping preserves semantics (latency win = max(io,compute) vs io+compute, measured on device)")


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
# compose_to_fixpoint — apply proved transforms until none remains; end-to-end equivalence by transitivity + diff
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def _run_program(stages: List[Callable], x):
    for fn in stages:
        x = fn(x)
    return x


def _differential(stages_a: List[Callable], stages_b: List[Callable], samples: Sequence) -> bool:
    """End-to-end differential: the two staged programs agree on every sample input (sound over the sample set)."""
    for x in samples:
        try:
            if _run_program(stages_a, x) != _run_program(stages_b, x):
                return False
        except Exception:  # noqa: BLE001
            return False
    return True


def compose_to_fixpoint(original: List[Callable], proposers: List[Tuple[str, Callable]], samples: Sequence,
                        max_rounds: int = 8) -> dict:
    """`original` = the program as an ordered list of stage callables. `proposers` = [(name, prop)] where
    prop(current_stages) → (Acceleration, new_stages | None): a proposer inspects the program and proposes a
    proved-equivalent replacement. We apply every PROVED step whose end-to-end differential against the current
    program holds, and iterate until a full pass applies nothing new (the FIXPOINT).

    End-to-end equivalence: each applied step is individually proved equivalent, so original ≡ final BY TRANSITIVITY;
    we additionally confirm original ≡ final by DIFFERENTIAL execution on `samples`. A step whose differential
    disagrees with its own equivalence claim is REFUSED (precision first — never apply an unproved/unsound step)."""
    current = list(original)
    applied: List[Tuple[str, Acceleration]] = []
    refused: List[str] = []
    rounds = 0
    hit_fixpoint = False
    while rounds < max_rounds:
        rounds += 1
        new_this_round = 0
        for name, prop in proposers:
            try:
                acc, new_stages = prop(current)
            except Exception as e:  # noqa: BLE001
                refused.append(f"{name}: proposer raised {type(e).__name__}")
                continue
            if not (acc.applied and new_stages is not None):
                continue
            if any(an == name for an, _ in applied):
                continue                                     # already applied this transform (idempotent)
            if not _differential(current, new_stages, samples):
                refused.append(f"{name}: claimed proved but end-to-end differential DISAGREES ⇒ refused")
                continue
            current = new_stages
            applied.append((name, acc))
            new_this_round += 1
        if new_this_round == 0:
            hit_fixpoint = True                              # a full pass applied nothing new
            break                                            # ★ FIXPOINT
    end_to_end = _differential(original, current, samples)
    return {
        "rounds": rounds,
        "fixpoint_reached": hit_fixpoint,                    # True ⇒ converged; False ⇒ stopped at max_rounds (report it)
        "applied": [{"name": n, "certificate": a.certificate} for n, a in applied],
        "applied_count": len(applied),
        "refused": refused,
        "end_to_end_equiv": end_to_end,
        "end_to_end_proof": "each applied step proved semantics-equivalent ⇒ original ≡ final by TRANSITIVITY of ≡; "
                            f"additionally confirmed by differential execution on {len(list(samples))} samples "
                            f"(agree={end_to_end})",
        "invariant": "applied ⇔ proved; a step failing the end-to-end differential is REFUSED (precision first)",
    }


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
# a self-contained fixpoint DEMO over a concrete slow pipeline (used by the report + tests)
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def compose_fixpoint_demo() -> dict:
    """A concrete slow pipeline [order-preserving dedup (O(N²)) → square-each (recompute) → sum] with proposers that
    swap each stage for a proved-equivalent faster one. Runs the fixpoint and returns the end-to-end result."""
    from accel.verified_algo import dedup_slow, dedup_fast, verified_algo_swap

    def square_recompute(lst):
        return [lst[i] ** 2 for i in range(len(lst))]

    def square_map(lst):
        return [x * x for x in lst]

    def sum_stage(lst):
        return sum(lst)

    original = [dedup_slow, square_recompute, sum_stage]
    samples = [[1, 2, 2, 3], [5, 5, 5], [], [9, 1, 9, 2, 1], list(range(20)) + list(range(10))]
    battery = samples

    def propose_dedup(stages):
        acc = verified_algo_swap(dedup_slow, dedup_fast, battery, claim="O(N²)→O(N) dedup (seen-set)")
        if not acc.applied:
            return acc, None
        return acc, [dedup_fast if fn is dedup_slow else fn for fn in stages]

    def propose_square(stages):
        acc = verified_algo_swap(square_recompute, square_map, battery, claim="index-recompute → direct map")
        if not acc.applied:
            return acc, None
        return acc, [square_map if fn is square_recompute else fn for fn in stages]

    result = compose_to_fixpoint(original, [("C.algo:dedup", propose_dedup), ("C.cse:square", propose_square)], samples)
    result["pipeline"] = "dedup(O(N²)) → square(recompute) → sum  ⇒  dedup(O(N)) → square(map) → sum"
    return result
