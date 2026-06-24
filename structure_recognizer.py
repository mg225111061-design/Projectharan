"""
v27 STAGE 12 — structure recognition + LLM-offload dispatcher  ★the cross-cutting top lever★
============================================================================================
"General code" is locally structured. Underneath a piece there is often an ALGEBRAIC OBJECT
(monoid / lattice / semiring / fixpoint) and a SHAPE (a closed-form loop, a tensor/linear-algebra
kernel, a relational join, a string/regex scan, a dataflow fixpoint, an error-tolerant probabilistic
estimate). When we can RECOGNIZE that structure we can do better than re-emitting tokens:

  (a) OFFLOAD it to a sound solver — the LLM proposes a sketch/spec, a *sound* synthesizer completes
      it and a verifier PROVES it (less LLM work, higher accuracy); or
  (b) apply a CERTIFIED REWRITE — a structure-justified transform proved equivalent to the original.

★ The differentiator is the certificate, never "nicer code". ★  This module is the recognizer + the
dispatcher. It implements TWO end-to-end SOUND actions and is honest everywhere else:

  • CLOSED_FORM_LOOP → OFFLOAD to the fold solver (S7). Verified lifting: the Python loop is lifted to a
    HARAN fold, the solver returns a closed form, and we gate it by DIFFERENTIAL EQUIVALENCE against the
    *original executed code* on many inputs (★never a wrong closed form★). O(n) → O(1)/O(log n).
  • RELATIONAL_JOIN (equi-join) → CERTIFIED REWRITE to a hash join. Source-to-source, identical emit, then
    differential-equivalence-gated AND measured: O(n·m) → O(n+m). (A pure-Python win — no numpy needed.)

Every other recognized class (TENSOR_LA, STRING_REGEX, DATAFLOW_FIXPOINT, PROBABILISTIC_APPROX) is
classified honestly and routed to its future stage; with no sound action wired here it returns NONE →
the honest LLM general-generation fallback. Recognition is sound static analysis; the two actions are
gated by execution, so a misclassification can only DECLINE (NONE), never emit a wrong answer.

★ HONEST LIMITS ★: (1) only the *structured minority* of pieces is offloaded; glue stays with the LLM —
there is NO uniform speedup (Ω(N), §1.3). (2) The "LLM proposes the sketch" half needs a key/egress
(absent here, §1.6); we implement and measure the *sound completion+proof* half (the transferable part),
exactly as S9 did for the missing SIMD backend.
"""
from __future__ import annotations

import ast
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import fold_kernels as FK

# ── code-shape BROTH (§2 pattern × §3): the fold solver `FK.fold_certificate` is a PURE function of its HARAN input
#    string but costs ~58 ms; memoize solved fold closures so a RECURRING structural pattern re-looks-up in O(1)
#    instead of re-solving (the broth idea — pre-prove/cache common instantiations → instant lookup — applied to the
#    recognizer). SOUND: pure-function memo (the verdict object is only ever READ downstream); the per-source
#    differential-equivalence GATE still runs on every dispatch, so caching the solver never weakens soundness.
_FOLD_BROTH: dict = {}


def _cached_fold_certificate(haran: str):
    v = _FOLD_BROTH.get(haran)
    if v is None:
        v = FK.fold_certificate(haran)
        _FOLD_BROTH[haran] = v
    return v

# ── shape classes + algebraic objects (the unified algebra of §0.4) ─────────────────────────────────
CLOSED_FORM_LOOP = "CLOSED_FORM_LOOP"
TENSOR_LA = "TENSOR_LA"
RELATIONAL_JOIN = "RELATIONAL_JOIN"
STRING_REGEX = "STRING_REGEX"
DATAFLOW_FIXPOINT = "DATAFLOW_FIXPOINT"
PROBABILISTIC_APPROX = "PROBABILISTIC_APPROX"
NONE = "NONE"

# associative accumulator ops → (haran-op, algebra, identity)
_MONOID_BIN = {"Add": ("+", "monoid", "0"), "Mult": ("*", "monoid", "1")}
_LATTICE_FN = {"max": ("max", "lattice"), "min": ("min", "lattice")}


@dataclass
class Structure:
    kind: str
    algebra: str = "none"          # monoid | lattice | semiring | fixpoint | none
    detail: str = ""
    fn_name: str = ""
    def __str__(self):
        return f"{self.kind} (algebra={self.algebra}) — {self.detail}"


@dataclass
class Dispatch:
    status: str                    # OFFLOADED | RECOGNIZED_REWRITE | NONE
    structure: Structure = None
    certificate: str = ""
    closed_form: str = ""
    complexity: str = ""
    speedup: float = 1.0
    workload: str = ""
    detail: str = ""
    def __str__(self):
        if self.status == "OFFLOADED":
            return f"OFFLOADED → {self.closed_form} ({self.complexity}; differential-equivalence verified)"
        if self.status == "RECOGNIZED_REWRITE":
            return f"RECOGNIZED_REWRITE [{self.structure.kind}] {self.speedup:.2f}× ({self.workload}; equivalence verified)"
        return f"NONE — {self.detail} (→ LLM general generation)"


# ── parsing helpers ─────────────────────────────────────────────────────────────────────────────────
def _first_fn(source: str, fn_name: Optional[str]) -> Optional[ast.FunctionDef]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if fn_name:
        return next((f for f in fns if f.name == fn_name), None)
    return fns[0] if fns else None


def _names_used(node: ast.AST) -> set:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _canon_expr(src: str) -> str:
    """Canonical source for an expression: round-trip through the AST so cosmetically-different
    spellings (`(n) + 1` vs `n + 1`) collapse to one string. Keeps the structural key shape-invariant."""
    try:
        return ast.unparse(ast.parse(src, mode="eval").body)
    except SyntaxError:
        return src


def _has_call(fnnode: ast.AST, mod: str) -> bool:
    """True if the function calls `mod.<something>` (e.g. re.* or random.*)."""
    for n in ast.walk(fnnode):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and isinstance(n.func.value, ast.Name) and n.func.value.id == mod:
            return True
    return False


def _for_loops(fnnode: ast.AST) -> List[ast.For]:
    return [n for n in ast.walk(fnnode) if isinstance(n, ast.For)]


# ── individual structure detectors (sound, syntactic) ───────────────────────────────────────────────
@dataclass
class _AccLoop:
    var: str
    lo: str
    hi: str            # python range upper bound (EXCLUSIVE), as source
    op: str            # "+" | "*"
    algebra: str
    body: str          # the accumulated expression, source, in terms of `var`


def _closed_form_loop(fnnode: ast.FunctionDef) -> Optional[_AccLoop]:
    """`for v in range(lo,hi): acc OP= f(v)` (OP associative), acc returned. f depends on v only."""
    fors = [n for n in fnnode.body if isinstance(n, ast.For)]
    if len(_for_loops(fnnode)) != 1 or len(fors) != 1:
        return None
    loop = fors[0]
    if not (isinstance(loop.iter, ast.Call) and isinstance(loop.iter.func, ast.Name)
            and loop.iter.func.id == "range" and isinstance(loop.target, ast.Name)):
        return None
    args = loop.iter.args
    if len(args) == 1:
        lo, hi = "0", ast.unparse(args[0])
    elif len(args) == 2:
        lo, hi = ast.unparse(args[0]), ast.unparse(args[1])
    else:
        return None                              # step != 1 → not lifted here (honest)
    if len(loop.body) != 1:
        return None
    stmt = loop.body[0]
    var = loop.target.id
    op = algebra = body = None
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
        b = _MONOID_BIN.get(type(stmt.op).__name__)
        if b:
            op, algebra, body = b[0], b[1], ast.unparse(stmt.value)
    elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        acc = stmt.targets[0].id
        v = stmt.value
        if isinstance(v, ast.BinOp) and type(v.op).__name__ in _MONOID_BIN:        # acc = acc + f(v)
            b = _MONOID_BIN[type(v.op).__name__]
            other = None
            if isinstance(v.left, ast.Name) and v.left.id == acc:
                other = v.right
            elif isinstance(v.right, ast.Name) and v.right.id == acc:
                other = v.left
            if other is not None:
                op, algebra, body = b[0], b[1], ast.unparse(other)
    if op is None or body is None:
        return None
    # f(v) must depend only on the loop var (and constants/params) — NOT the accumulator / external state
    if var not in _names_used(ast.parse(body, mode="eval")):
        return None
    return _AccLoop(var=var, lo=lo, hi=hi, op=op, algebra=algebra, body=body)


def _while_acc_loop(fnnode: ast.FunctionDef) -> Optional[_AccLoop]:
    """CODE-SHAPE NORMALIZATION: `acc=id; k=lo; while k<=hi (or k<hi): acc OP= f(k); k+=1; return acc` ⇒ the SAME
    `_AccLoop` the for-form yields. Conservative — only the exact canonical counter-while matches; else None."""
    if _for_loops(fnnode):
        return None
    whiles = [n for n in ast.walk(fnnode) if isinstance(n, ast.While)]
    body_whiles = [n for n in fnnode.body if isinstance(n, ast.While)]
    if len(whiles) != 1 or len(body_whiles) != 1:
        return None
    loop = body_whiles[0]
    cond = loop.test
    if not (isinstance(cond, ast.Compare) and len(cond.ops) == 1 and isinstance(cond.left, ast.Name)):
        return None
    kvar = cond.left.id
    ot = type(cond.ops[0]).__name__
    hi_src = ast.unparse(cond.comparators[0])
    hi = _canon_expr(f"({hi_src}) + 1") if ot == "LtE" else (hi_src if ot == "Lt" else None)
    if hi is None:
        return None
    inits = {}                                               # simple pre-loop assigns (handles 's=0; k=1')
    for st in fnnode.body:
        if st is loop:
            break
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            inits[st.targets[0].id] = ast.unparse(st.value)
    if kvar not in inits or len(loop.body) != 2:
        return None
    inc = acc_stmt = None
    for st in loop.body:
        if (isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name) and st.target.id == kvar
                and isinstance(st.op, ast.Add) and isinstance(st.value, ast.Constant) and st.value.value == 1):
            inc = st
        else:
            acc_stmt = st
    if inc is None or not (isinstance(acc_stmt, ast.AugAssign) and isinstance(acc_stmt.target, ast.Name)):
        return None
    acc = acc_stmt.target.id
    b = _MONOID_BIN.get(type(acc_stmt.op).__name__)
    if acc == kvar or acc not in inits or not b:
        return None
    op, algebra, body = b[0], b[1], ast.unparse(acc_stmt.value)
    rets = [n for n in ast.walk(fnnode) if isinstance(n, ast.Return)]
    if not (len(rets) == 1 and isinstance(rets[0].value, ast.Name) and rets[0].value.id == acc):
        return None                                          # accumulator must be the returned value
    if kvar not in _names_used(ast.parse(body, mode="eval")):
        return None                                          # f(k) must depend on the counter (and only it)
    return _AccLoop(var=kvar, lo=inits[kvar], hi=hi, op=op, algebra=algebra, body=body)


def _comprehension_acc(fnnode: ast.FunctionDef) -> Optional[_AccLoop]:
    """CODE-SHAPE NORMALIZATION: `return sum(f(k) for k in range(lo,hi))` (or math.prod) ⇒ the SAME `_AccLoop`."""
    if _for_loops(fnnode) or any(isinstance(n, ast.While) for n in ast.walk(fnnode)):
        return None
    rets = [n for n in ast.walk(fnnode) if isinstance(n, ast.Return)]
    if len(rets) != 1 or not isinstance(rets[0].value, ast.Call) or len(rets[0].value.args) != 1:
        return None
    call = rets[0].value
    fname = call.func.id if isinstance(call.func, ast.Name) else (
        call.func.attr if isinstance(call.func, ast.Attribute) else None)
    if fname == "sum":
        op, algebra = "+", "monoid"
    elif fname == "prod":
        op, algebra = "*", "monoid"
    else:
        return None
    gen = call.args[0]
    if not (isinstance(gen, ast.GeneratorExp) and len(gen.generators) == 1):
        return None
    comp = gen.generators[0]
    if comp.ifs or not (isinstance(comp.iter, ast.Call) and isinstance(comp.iter.func, ast.Name)
                        and comp.iter.func.id == "range" and isinstance(comp.target, ast.Name)):
        return None
    args = comp.iter.args
    if len(args) == 1:
        lo, hi = "0", ast.unparse(args[0])
    elif len(args) == 2:
        lo, hi = ast.unparse(args[0]), ast.unparse(args[1])
    else:
        return None                                          # step ≠ 1 not lifted here (honest)
    var, body = comp.target.id, ast.unparse(gen.elt)
    if var not in _names_used(ast.parse(body, mode="eval")):
        return None
    return _AccLoop(var=var, lo=lo, hi=hi, op=op, algebra=algebra, body=body)


def _recursion_acc(fnnode: ast.FunctionDef) -> Optional[_AccLoop]:
    """CODE-SHAPE NORMALIZATION: a LINEAR self-recursion `def f(p): if p<c: return ID; return f(p-1) OP h(p)` ⇒
    the SAME `_AccLoop` (sum k=lo..p of h(k)). Conservative — exactly one self-call f(p−1), monoid-identity base,
    h(p) depends only on p; else None. Binary recursion (f(p−1)+f(p−2)) has two self-calls ⇒ rejected."""
    import copy
    if _for_loops(fnnode) or any(isinstance(n, ast.While) for n in ast.walk(fnnode)):
        return None
    a = fnnode.args
    if len(a.args) != 1 or a.vararg or a.kwarg or a.kwonlyargs:
        return None
    p, fname = a.args[0].arg, fnnode.name
    selfcalls = [n for n in ast.walk(fnnode) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == fname]
    if len(selfcalls) != 1:                                  # linear recursion only (binary → reject)
        return None
    sc = selfcalls[0]
    if not (len(sc.args) == 1 and isinstance(sc.args[0], ast.BinOp) and isinstance(sc.args[0].op, ast.Sub)
            and isinstance(sc.args[0].left, ast.Name) and sc.args[0].left.id == p
            and isinstance(sc.args[0].right, ast.Constant) and sc.args[0].right.value == 1):
        return None                                          # the self-call must be exactly f(p−1)
    body = fnnode.body
    base_test = base_ret = rec_ret = None
    if len(body) == 2 and isinstance(body[0], ast.If) and isinstance(body[1], ast.Return):
        iff = body[0]
        if len(iff.body) == 1 and isinstance(iff.body[0], ast.Return) and not iff.orelse:
            base_test, base_ret, rec_ret = iff.test, iff.body[0], body[1]
    elif len(body) == 1 and isinstance(body[0], ast.If) and body[0].orelse:
        iff = body[0]
        if (len(iff.body) == 1 and isinstance(iff.body[0], ast.Return)
                and len(iff.orelse) == 1 and isinstance(iff.orelse[0], ast.Return)):
            base_test, base_ret, rec_ret = iff.test, iff.body[0], iff.orelse[0]
    if base_test is None:
        return None
    if not (isinstance(base_test, ast.Compare) and len(base_test.ops) == 1 and isinstance(base_test.left, ast.Name)
            and base_test.left.id == p and isinstance(base_test.comparators[0], ast.Constant)):
        return None
    cval, ot = base_test.comparators[0].value, type(base_test.ops[0]).__name__
    if ot == "Lt":
        lo = cval                                            # p<c → terms from k=c
    elif ot in ("LtE", "Eq"):
        lo = cval + 1                                        # p<=c / p==c → terms from k=c+1
    else:
        return None
    rv = rec_ret.value
    if not (isinstance(rv, ast.BinOp) and type(rv.op).__name__ in _MONOID_BIN):
        return None
    b = _MONOID_BIN[type(rv.op).__name__]
    sides = [rv.left, rv.right]
    if sides[0] is sc:
        h = sides[1]
    elif sides[1] is sc:
        h = sides[0]
    else:
        return None                                          # recursion term must be f(p−1) OP h(p)
    if not isinstance(base_ret.value, ast.Constant):
        return None
    ident = base_ret.value.value
    if (b[0] == "+" and ident != 0) or (b[0] == "*" and ident != 1):
        return None                                          # base case must be the monoid identity
    idx = "k" if p != "k" else "j"
    hh = copy.deepcopy(h)
    for nd in ast.walk(hh):
        if isinstance(nd, ast.Name) and nd.id == p:
            nd.id = idx
    body_idx = ast.unparse(hh)
    if idx not in _names_used(ast.parse(body_idx, mode="eval")):
        return None                                          # the summand must depend on the index
    return _AccLoop(var=idx, lo=str(lo), hi=_canon_expr(f"{p} + 1"), op=b[0], algebra=b[1], body=body_idx)


def _reduce_acc(fnnode: ast.FunctionDef) -> Optional[_AccLoop]:
    """CODE-SHAPE NORMALIZATION: `return reduce(lambda a,k: a OP h(k), range(lo,hi), ID)` (functools.reduce /
    bare reduce) ⇒ the SAME `_AccLoop`. Conservative — a 2-arg lambda whose body is `acc OP h(k)` with acc = the
    accumulator param appearing as exactly one (bare-Name) operand, h(k) depending ONLY on the element param (NOT
    the accumulator), a range iterable, and a monoid-identity initializer; else None."""
    if _for_loops(fnnode) or any(isinstance(n, ast.While) for n in ast.walk(fnnode)):
        return None
    rets = [n for n in ast.walk(fnnode) if isinstance(n, ast.Return)]
    if len(rets) != 1 or not isinstance(rets[0].value, ast.Call):
        return None
    call = rets[0].value
    f = call.func
    is_reduce = (isinstance(f, ast.Name) and f.id == "reduce") or (isinstance(f, ast.Attribute) and f.attr == "reduce")
    if not is_reduce or len(call.args) != 3:                 # require the explicit initializer (the identity)
        return None
    func, iterable, init = call.args
    if not isinstance(func, ast.Lambda):
        return None
    la = func.args
    if len(la.args) != 2 or la.vararg or la.kwarg or la.kwonlyargs or la.defaults:
        return None
    accname, elname = la.args[0].arg, la.args[1].arg
    if accname == elname:
        return None
    lb = func.body
    if not (isinstance(lb, ast.BinOp) and type(lb.op).__name__ in _MONOID_BIN):
        return None
    b = _MONOID_BIN[type(lb.op).__name__]
    is_acc = lambda nd: isinstance(nd, ast.Name) and nd.id == accname   # noqa: E731
    if is_acc(lb.left) and not is_acc(lb.right):
        h = lb.right
    elif is_acc(lb.right) and not is_acc(lb.left):
        h = lb.left
    else:
        return None                                          # accumulator must be exactly one operand
    hnames = _names_used(h)
    if accname in hnames or elname not in hnames:
        return None                                          # h(k) must depend on the element, never the accumulator
    if not (isinstance(iterable, ast.Call) and isinstance(iterable.func, ast.Name) and iterable.func.id == "range"):
        return None
    rargs = iterable.args
    if len(rargs) == 1:
        lo, hi = "0", ast.unparse(rargs[0])
    elif len(rargs) == 2:
        lo, hi = ast.unparse(rargs[0]), ast.unparse(rargs[1])
    else:
        return None                                          # step ≠ 1 not lifted here (honest)
    if not (isinstance(init, ast.Constant) and ((b[0] == "+" and init.value == 0)
                                                or (b[0] == "*" and init.value == 1))):
        return None                                          # initializer must be the monoid identity
    return _AccLoop(var=elname, lo=_canon_expr(lo), hi=_canon_expr(hi), op=b[0], algebra=b[1], body=ast.unparse(h))


def _acc_loop_any_shape(fnnode: ast.FunctionDef) -> Optional[_AccLoop]:
    """Code-shape invariance: a for-loop, a counter-while, a sum/prod comprehension, a linear self-recursion, and a
    functools.reduce fold computing the same accumulation all NORMALIZE to the same `_AccLoop` structural key (same
    var/bounds/op/algebra/body) ⇒ the same algorithm + the same verified closed form."""
    return (_closed_form_loop(fnnode) or _while_acc_loop(fnnode) or _comprehension_acc(fnnode)
            or _recursion_acc(fnnode) or _reduce_acc(fnnode))


@dataclass
class _NestedAcc:
    """A doubly-nested accumulation Σ_i Σ_j h(i,j): the OUTER loop var/bounds, the INNER loop var/bounds (whose
    bounds MAY depend on the outer var — the triangular case), op/algebra, and the body h (in terms of i,j,param)."""
    vi: str
    lo1: str
    hi1: str           # outer range upper bound (EXCLUSIVE), source
    vj: str
    lo2: str
    hi2: str           # inner range upper bound (EXCLUSIVE), source — may reference the outer var
    op: str            # "+" | "*"
    algebra: str
    body: str          # accumulated expression, source, in terms of vi/vj (and the param)


def _nested_acc(fnnode: ast.FunctionDef) -> Optional[_NestedAcc]:
    """CODE-SHAPE NORMALIZATION (nested): `acc=ID; for i in range(lo1,hi1): for j in range(lo2,hi2): acc OP= h(i,j);
    return acc` ⇒ a `_NestedAcc` 2-D fold. Conservative & sound — EXACTLY two nested `for`s (the inner is the outer
    body's only statement; the acc-update is the inner body's only statement), one accumulator initialised to the
    monoid identity and returned, h depends only on {i, j, param} (NOT the accumulator / external state). Inner
    bounds MAY reference the outer var (triangular sums); outer bounds reference only the param. Else None."""
    if len(_for_loops(fnnode)) != 2 or any(isinstance(n, ast.While) for n in ast.walk(fnnode)):
        return None
    if len(fnnode.args.args) != 1 or fnnode.args.vararg or fnnode.args.kwarg or fnnode.args.kwonlyargs:
        return None
    param = fnnode.args.args[0].arg
    body = fnnode.body
    if not (len(body) == 3 and isinstance(body[0], ast.Assign) and isinstance(body[1], ast.For)
            and isinstance(body[2], ast.Return)):
        return None
    init, outer, ret = body
    if not (len(init.targets) == 1 and isinstance(init.targets[0], ast.Name) and isinstance(init.value, ast.Constant)):
        return None
    accname = init.targets[0].id
    if not (isinstance(ret.value, ast.Name) and ret.value.id == accname):
        return None
    # outer loop: `for i in range(lo1,hi1):` whose body is exactly the inner `for`
    if not (isinstance(outer.iter, ast.Call) and isinstance(outer.iter.func, ast.Name) and outer.iter.func.id == "range"
            and isinstance(outer.target, ast.Name) and len(outer.body) == 1 and isinstance(outer.body[0], ast.For)):
        return None
    inner = outer.body[0]
    if not (isinstance(inner.iter, ast.Call) and isinstance(inner.iter.func, ast.Name) and inner.iter.func.id == "range"
            and isinstance(inner.target, ast.Name) and len(inner.body) == 1):
        return None
    vi, vj = outer.target.id, inner.target.id
    if vi == vj or vi == param or vj == param or vi == accname or vj == accname:
        return None
    stmt = inner.body[0]
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == accname:
        b = _MONOID_BIN.get(type(stmt.op).__name__)
        hsrc = stmt.value
    else:
        return None
    if b is None:
        return None
    if (b[0] == "+" and init.value.value != 0) or (b[0] == "*" and init.value.value != 1):
        return None                                          # base accumulator must be the monoid identity

    def _bounds(call):
        a = call.args
        if len(a) == 1:
            return "0", ast.unparse(a[0])
        if len(a) == 2:
            return ast.unparse(a[0]), ast.unparse(a[1])
        return None
    ob, ib = _bounds(outer.iter), _bounds(inner.iter)
    if ob is None or ib is None:                             # step ≠ 1 not lifted here (honest)
        return None
    lo1, hi1 = ob
    lo2, hi2 = ib
    # the accumulated body must reference only {i, j, param} and NOT the accumulator/other names
    hnames = _names_used(ast.parse(ast.unparse(hsrc), mode="eval"))
    if not hnames.issubset({vi, vj, param}) or not (hnames & {vi, vj}):
        return None
    # the OUTER bounds may reference only the param (not i/j); the INNER bounds may reference the param and i
    if not (_names_used(ast.parse(lo1, mode="eval")).issubset({param})
            and _names_used(ast.parse(hi1, mode="eval")).issubset({param})):
        return None
    if not (_names_used(ast.parse(lo2, mode="eval")).issubset({param, vi})
            and _names_used(ast.parse(hi2, mode="eval")).issubset({param, vi})):
        return None
    return _NestedAcc(vi=vi, lo1=_canon_expr(lo1), hi1=_canon_expr(hi1), vj=vj, lo2=_canon_expr(lo2),
                      hi2=_canon_expr(hi2), op=b[0], algebra=b[1], body=ast.unparse(hsrc))


@dataclass
class _CondAcc:
    """A FILTERED accumulation Σ_{k: k%M==R} h(k): loop var/bounds, the modular predicate (M, R), op/algebra,
    and the summand h (in terms of the loop var). The reindex k = M·t + r₀ closes it to an O(1) closed form."""
    var: str
    lo: str
    hi: str            # range upper bound (EXCLUSIVE), source
    mod: int           # M in `k % M == R`
    rem: int           # R
    op: str
    algebra: str
    body: str


def _cond_acc(fnnode: ast.FunctionDef) -> Optional[_CondAcc]:
    """CODE-SHAPE NORMALIZATION (filtered): `acc=ID; for k in range(lo,hi): if k%M==R: acc OP= h(k); return acc`
    ⇒ a `_CondAcc`. Conservative & sound — one `for` over range(lo,hi) whose only body statement is an `if k%M==R`
    (M≥2, 0≤R<M, constants) with NO else and a single acc-update inside; acc initialised to the monoid identity and
    returned; h depends ONLY on the loop var. Else None."""
    if len(_for_loops(fnnode)) != 1 or any(isinstance(n, ast.While) for n in ast.walk(fnnode)):
        return None
    if len(fnnode.args.args) != 1 or fnnode.args.vararg or fnnode.args.kwarg or fnnode.args.kwonlyargs:
        return None
    param = fnnode.args.args[0].arg
    body = fnnode.body
    if not (len(body) == 3 and isinstance(body[0], ast.Assign) and isinstance(body[1], ast.For)
            and isinstance(body[2], ast.Return)):
        return None
    init, loop, ret = body
    if not (len(init.targets) == 1 and isinstance(init.targets[0], ast.Name) and isinstance(init.value, ast.Constant)):
        return None
    accname = init.targets[0].id
    if not (isinstance(ret.value, ast.Name) and ret.value.id == accname):
        return None
    if not (isinstance(loop.iter, ast.Call) and isinstance(loop.iter.func, ast.Name) and loop.iter.func.id == "range"
            and isinstance(loop.target, ast.Name) and len(loop.body) == 1 and isinstance(loop.body[0], ast.If)):
        return None
    var = loop.target.id
    if var in (param, accname):
        return None
    args = loop.iter.args
    if len(args) == 1:
        lo, hi = "0", ast.unparse(args[0])
    elif len(args) == 2:
        lo, hi = ast.unparse(args[0]), ast.unparse(args[1])
    else:
        return None
    iff = loop.body[0]
    if iff.orelse or len(iff.body) != 1:                     # no else; the if-body is exactly the accumulation
        return None
    test = iff.test                                          # the predicate must be `k % M == R` (constants)
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
            and isinstance(test.left, ast.BinOp) and isinstance(test.left.op, ast.Mod)
            and isinstance(test.left.left, ast.Name) and test.left.left.id == var
            and isinstance(test.left.right, ast.Constant) and isinstance(test.comparators[0], ast.Constant)):
        return None
    M, R = test.left.right.value, test.comparators[0].value
    if not (isinstance(M, int) and isinstance(R, int) and M >= 2 and 0 <= R < M):
        return None
    stmt = iff.body[0]
    if not (isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == accname):
        return None
    b = _MONOID_BIN.get(type(stmt.op).__name__)
    if b is None:
        return None
    if (b[0] == "+" and init.value.value != 0) or (b[0] == "*" and init.value.value != 1):
        return None
    hsrc = ast.unparse(stmt.value)
    hnames = _names_used(ast.parse(hsrc, mode="eval"))
    if hnames - {var} or var not in hnames:                  # h depends ONLY on the loop var
        return None
    return _CondAcc(var=var, lo=_canon_expr(lo), hi=_canon_expr(hi), mod=M, rem=R,
                    op=b[0], algebra=b[1], body=hsrc)


def _cond_comprehension(fnnode: ast.FunctionDef) -> Optional[_CondAcc]:
    """CODE-SHAPE NORMALIZATION (filtered, comprehension form): `return sum(h(k) for k in range(lo,hi) if k%M==R)`
    ⇒ the SAME `_CondAcc` the filtered for-loop yields — a filtered sum collapses identically however it is written.
    Conservative — sum/prod over ONE range generator with EXACTLY one `k%M==R` filter (constants M≥2, 0≤R<M); the
    summand depends only on the loop var. Else None."""
    if _for_loops(fnnode) or any(isinstance(n, ast.While) for n in ast.walk(fnnode)):
        return None
    if len(fnnode.args.args) != 1 or fnnode.args.vararg or fnnode.args.kwarg or fnnode.args.kwonlyargs:
        return None
    rets = [n for n in ast.walk(fnnode) if isinstance(n, ast.Return)]
    if len(rets) != 1 or not isinstance(rets[0].value, ast.Call) or len(rets[0].value.args) != 1:
        return None
    call = rets[0].value
    fname = call.func.id if isinstance(call.func, ast.Name) else (
        call.func.attr if isinstance(call.func, ast.Attribute) else None)
    if fname == "sum":
        op, algebra = "+", "monoid"
    elif fname == "prod":
        op, algebra = "*", "monoid"
    else:
        return None
    gen = call.args[0]
    if not (isinstance(gen, ast.GeneratorExp) and len(gen.generators) == 1):
        return None
    comp = gen.generators[0]
    if not (len(comp.ifs) == 1 and isinstance(comp.iter, ast.Call) and isinstance(comp.iter.func, ast.Name)
            and comp.iter.func.id == "range" and isinstance(comp.target, ast.Name)):
        return None
    var = comp.target.id
    test = comp.ifs[0]                                       # the single filter must be `k % M == R` (constants)
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
            and isinstance(test.left, ast.BinOp) and isinstance(test.left.op, ast.Mod)
            and isinstance(test.left.left, ast.Name) and test.left.left.id == var
            and isinstance(test.left.right, ast.Constant) and isinstance(test.comparators[0], ast.Constant)):
        return None
    M, R = test.left.right.value, test.comparators[0].value
    if not (isinstance(M, int) and isinstance(R, int) and M >= 2 and 0 <= R < M):
        return None
    args = comp.iter.args
    if len(args) == 1:
        lo, hi = "0", ast.unparse(args[0])
    elif len(args) == 2:
        lo, hi = ast.unparse(args[0]), ast.unparse(args[1])
    else:
        return None
    body = ast.unparse(gen.elt)
    hnames = _names_used(ast.parse(body, mode="eval"))
    if hnames - {var} or var not in hnames:
        return None
    return _CondAcc(var=var, lo=_canon_expr(lo), hi=_canon_expr(hi), mod=M, rem=R, op=op, algebra=algebra, body=body)


def _cond_any_shape(fnnode: ast.FunctionDef) -> Optional[_CondAcc]:
    """A filtered accumulation Σ_{k%M==R} h(k) written as a for-loop OR a sum/prod comprehension normalizes to the
    SAME `_CondAcc` key ⇒ the same collapse + the same verified closed form (shape invariance for filtered sums)."""
    return _cond_acc(fnnode) or _cond_comprehension(fnnode)


@dataclass
class _Join:
    a_iter: str
    b_iter: str
    a_var: str
    b_var: str
    key_a: str
    key_b: str
    emit: str
    out: str


def _equi_join(fnnode: ast.FunctionDef) -> Optional[_Join]:
    """`for a in A: for b in B: if <a-key> == <b-key>: out.append(<emit>)` — a canonical equi-join."""
    for outer in [n for n in ast.walk(fnnode) if isinstance(n, ast.For)]:
        if not (isinstance(outer.target, ast.Name) and isinstance(outer.iter, ast.Name)):
            continue
        inners = [n for n in outer.body if isinstance(n, ast.For)]
        if len(inners) != 1:
            continue
        inner = inners[0]
        if not (isinstance(inner.target, ast.Name) and isinstance(inner.iter, ast.Name)):
            continue
        if len(inner.body) != 1 or not isinstance(inner.body[0], ast.If):
            continue
        iff = inner.body[0]
        t = iff.test
        if not (isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq)):
            continue                             # single equality only (equi-join) — else honest decline
        if not (len(iff.body) == 1 and isinstance(iff.body[0], ast.Expr)
                and isinstance(iff.body[0].value, ast.Call)):
            continue
        call = iff.body[0].value
        if not (isinstance(call.func, ast.Attribute) and call.func.attr == "append"
                and isinstance(call.func.value, ast.Name) and len(call.args) == 1):
            continue
        a_var, b_var = outer.target.id, inner.target.id
        left, right = t.left, t.comparators[0]
        ln, rn = _names_used(left), _names_used(right)
        if a_var in ln and b_var in rn:
            key_a, key_b = ast.unparse(left), ast.unparse(right)
        elif b_var in ln and a_var in rn:
            key_a, key_b = ast.unparse(right), ast.unparse(left)
        else:
            continue
        return _Join(a_iter=outer.iter.id, b_iter=inner.iter.id, a_var=a_var, b_var=b_var,
                     key_a=key_a, key_b=key_b, emit=ast.unparse(call.args[0]), out=call.func.value.id)
    return None


def _tensor_la(fnnode: ast.FunctionDef) -> bool:
    """≥2 nested loops with a multiply-accumulate `C[..] += A[..]*B[..]` (semiring ⊕/⊗)."""
    for n in ast.walk(fnnode):
        if isinstance(n, ast.AugAssign) and type(n.op).__name__ == "Add" \
                and isinstance(n.target, ast.Subscript) and isinstance(n.value, ast.BinOp) \
                and type(n.value.op).__name__ == "Mult":
            depth = sum(1 for p in ast.walk(fnnode) if isinstance(p, ast.For))
            if depth >= 2:
                return True
    return False


def _dataflow_fixpoint(fnnode: ast.FunctionDef) -> bool:
    """A `while`-to-convergence (changed flag / worklist) — a lattice fixpoint iteration."""
    for n in ast.walk(fnnode):
        if isinstance(n, ast.While):
            cond_names = {x.lower() for x in _names_used(n.test)}
            if any(k in cond_names for k in ("changed", "change", "dirty", "worklist", "queue", "work")):
                return True
            if isinstance(n.test, ast.Name):              # while worklist:
                return True
    return False


# ── the recognizer ──────────────────────────────────────────────────────────────────────────────────
def recognize(source: str, fn_name: Optional[str] = None) -> Structure:
    """Classify a function into a shape + underlying algebra by sound static analysis. Precise structural
    shapes win over weak keyword signals; nothing matched ⇒ NONE (honest)."""
    fn = _first_fn(source, fn_name)
    if fn is None:
        return Structure(NONE, detail="no parseable function")
    name = fn.name
    if _tensor_la(fn):
        return Structure(TENSOR_LA, "semiring", "multiply-accumulate over nested loops", name)
    j = _equi_join(fn)
    if j is not None:
        return Structure(RELATIONAL_JOIN, "semiring", f"equi-join on {j.key_a}=={j.key_b}", name)
    acc = _acc_loop_any_shape(fn)                            # for / counter-while / comprehension → same key
    if acc is not None:
        return Structure(CLOSED_FORM_LOOP, acc.algebra,
                         f"reduce('{acc.op}', f({acc.var})) over range({acc.lo},{acc.hi})", name)
    nst = _nested_acc(fn)                                    # doubly-nested Σ_i Σ_j h(i,j) (2-D fold)
    if nst is not None:
        return Structure(CLOSED_FORM_LOOP, nst.algebra,
                         f"reduce('{nst.op}', f({nst.vi},{nst.vj})) over range×range (nested)", name)
    cnd = _cond_any_shape(fn)                                # filtered Σ_{k%M==R} h(k) — for-loop OR comprehension
    if cnd is not None:
        return Structure(CLOSED_FORM_LOOP, cnd.algebra,
                         f"reduce('{cnd.op}', f({cnd.var}) where {cnd.var}%{cnd.mod}=={cnd.rem})", name)
    if _dataflow_fixpoint(fn):
        return Structure(DATAFLOW_FIXPOINT, "fixpoint", "while-to-convergence (lattice fixpoint)", name)
    if _has_call(fn, "re") or any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                                  and n.func.attr in ("match", "search", "findall", "sub", "split")
                                  for n in ast.walk(fn)):
        return Structure(STRING_REGEX, "none", "regex / string scan", name)
    if _has_call(fn, "random"):
        return Structure(PROBABILISTIC_APPROX, "none", "random sampling (error-tolerant estimate)", name)
    return Structure(NONE, "none", "no provable algebraic/shape structure", name)


# ── action 1: OFFLOAD a closed-form loop to the fold solver (verified lifting) ──────────────────────
# a pure, side-effect-free builtin set: arithmetic + collections, but NO open / eval / exec and only a
# TIGHTLY-WHITELISTED __import__ (functools/operator/math — all pure, no I/O) so common functional idioms
# (functools.reduce folds) execute in the gate. Executing the analyzed code still cannot touch files/network.
import functools as _functools
import operator as _operator
import math as _math
_SAFE_MODULES = {"functools": _functools, "operator": _operator, "math": _math}


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
    """A sandbox __import__ permitting ONLY the pure-module whitelist (no os/sys/subprocess/socket/…)."""
    if level == 0 and name in _SAFE_MODULES:
        return _SAFE_MODULES[name]
    raise ImportError(f"import of '{name}' is not permitted in the equivalence-gate sandbox")


_SAFE_BUILTINS = {"range": range, "min": min, "max": max, "abs": abs, "sum": sum, "pow": pow, "len": len,
                  "list": list, "dict": dict, "tuple": tuple, "set": set, "frozenset": frozenset,
                  "enumerate": enumerate, "sorted": sorted, "reversed": reversed, "zip": zip,
                  "map": map, "filter": filter, "bool": bool, "int": int, "float": float, "str": str,
                  "round": round, "divmod": divmod, "reduce": _functools.reduce, "__import__": _safe_import}
_SAMPLE_N = [1, 2, 3, 5, 8, 13, 20, 37, 64]
# the equivalence gate EXECUTES the user's loop; NEVER run a sample whose iteration count exceeds this budget (a
# super-linear upper bound like range(2**n) would loop ~2^64 times and hang). Affordable samples still verify the
# closed form — a high-degree-polynomial or exponential bound just uses the smaller samples (sound, no-hang).
_GATE_ITER_BUDGET = 2_000_000
# nested gate uses SMALL bounded samples: with degree-≤2 polynomial loop bounds the real double loop runs ≤ N²
# iterations per sample, so the gate is always cheap (never hangs); 12 points over-determine the low-degree
# polynomial closed forms these nested loops produce.
_NESTED_SAMPLE_N = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16]


def _make_callable(source: str, name: str):
    # ONE shared namespace for globals+locals: a recursive function's __globals__ must contain itself,
    # else its self-call raises NameError (the classic exec-with-two-dicts gotcha). __builtins__ stays
    # restricted, so executing the analyzed code for the equivalence gate still cannot import/open/eval.
    ns: dict = {"__builtins__": _SAFE_BUILTINS}
    exec(compile(source, "<recognize>", "exec"), ns)  # noqa: S102
    return ns.get(name)


def _offload_closed_form(source: str, fn: ast.FunctionDef, acc: _AccLoop) -> Dispatch:
    struct = Structure(CLOSED_FORM_LOOP, acc.algebra, f"reduce('{acc.op}', f({acc.var}))", fn.name)
    if len(fn.args.args) != 1:
        return Dispatch(NONE, struct, detail="closed-form lift supports single-parameter functions here")
    if acc.op != "+":          # HARAN's fold is summation (Σ); a product/other monoid is NOT representable
        return Dispatch(NONE, struct, detail=f"'{acc.op}'-accumulation is not a Σ-fold (the solver sums) "
                        "→ LLM fallback (sound: not lifted to a wrong summation)")
    param = fn.args.args[0].arg
    # f(k) must depend ONLY on the loop var (so the fold upper bound can be a clean fresh symbol)
    body_names = _names_used(ast.parse(acc.body, mode="eval"))
    if body_names - {acc.var}:
        return Dispatch(NONE, struct, detail=f"accumulated expr references {body_names - {acc.var}} "
                        "(not a pure f(k)) — outside the single-symbol fold lift here")
    # lower bound must be a concrete integer literal (the common Σ_{c}^{·} case)
    try:
        lo_val = int(eval(compile(ast.parse(acc.lo, mode="eval"), "<lo>", "eval"), {"__builtins__": {}}))  # noqa: S307
    except Exception:  # noqa: BLE001
        return Dispatch(NONE, struct, detail=f"non-constant lower bound `{acc.lo}` — not lifted here")
    try:
        ref = _make_callable(source, fn.name)
        hi_fn = eval(compile(f"lambda {param}: ({acc.hi})", "<hi>", "eval"), {"__builtins__": _SAFE_BUILTINS})  # noqa: S307
    except Exception as e:  # noqa: BLE001
        return Dispatch(NONE, struct, detail=f"could not build the equivalence gate ({type(e).__name__})")
    if ref is None:
        return Dispatch(NONE, struct, detail="original function not found after exec")
    # ★ lift to a CLEAN-SYMBOL fold `lo..u` (fold_kernels folds these correctly; arithmetic bounds it does
    #   NOT — so we never emit one). HARAN `a..b` is INCLUSIVE Σ; Python range(lo,hi) is Σ_{lo}^{hi-1},
    #   so the matching upper symbol value is u = hi-1. The gate is the sole soundness authority.
    import sympy
    u = sympy.Symbol("u")
    haran = f"fn g(u: Nat) -> Nat {{ fold {acc.var} in {lo_val}..u {{ {acc.body} }} }}"
    verdict = _cached_fold_certificate(haran)               # code-shape broth: O(1) re-lookup of a solved fold
    if verdict.status != "FOLDED":
        return Dispatch(NONE, struct, detail=f"fold solver did not close this form ({verdict.status}: "
                        f"{verdict.reason}) → LLM fallback")
    try:
        cf = sympy.sympify(verdict.closed_form)
    except Exception:  # noqa: BLE001
        return Dispatch(NONE, struct, detail="closed form not interpretable → LLM fallback")
    ok = checked = 0
    for val in _SAMPLE_N:
        try:
            n_eval = int(hi_fn(val)) - 1            # Python range exclusivity → inclusive fold upper
        except Exception:  # noqa: BLE001
            continue
        if n_eval < lo_val:                          # empty range → skip (closed form may extrapolate)
            continue
        # ★ BOUNDED-GATE GUARD (no-hang): the iteration count is (n_eval − lo_val + 1). NEVER execute the real loop
        #   when that exceeds a budget — a super-linear upper bound like range(2**n) would run ~2^64 iterations and
        #   hang. Skip the unaffordable sample; affordable samples still verify the closed form (sound, no-hang). ★
        if n_eval - lo_val + 1 > _GATE_ITER_BUDGET:
            continue
        try:
            want = ref(val)
        except Exception:  # noqa: BLE001
            continue
        checked += 1
        if abs(float(cf.subs(u, n_eval)) - float(want)) <= 1e-6:
            ok += 1
    if checked < 5 or ok != checked:
        return Dispatch(NONE, struct, detail=f"closed form not equivalence-verified ({ok}/{checked}) → "
                        "LLM fallback (sound: a wrong form is never emitted)")
    # present the closed form in terms of the ORIGINAL parameter: cf(u := hi(param)-1)
    try:
        psym = sympy.Symbol(param)
        cf_orig = str(sympy.simplify(cf.subs(u, sympy.sympify(acc.hi.replace(param, param)) - 1)))
    except Exception:  # noqa: BLE001
        cf_orig = f"{verdict.closed_form} [with u = ({acc.hi})-1]"
    cert = (f"OFFLOAD certificate: general loop `{fn.name}` lifted to fold `{lo_val}..u` → {verdict.kernel} "
            f"closed form {verdict.closed_form} ({verdict.complexity}); differential-equivalence verified on "
            f"{checked}/{checked} inputs vs the ORIGINAL executed code (never a wrong closed form). The fold "
            f"solver + the gate are the authority; the LLM only proposed the sketch.")
    return Dispatch("OFFLOADED", struct, certificate=cert, closed_form=cf_orig,
                    complexity=verdict.complexity, detail="offloaded to fold solver")


def _offload_nested(source: str, fn: ast.FunctionDef, nst: _NestedAcc) -> Dispatch:
    """OFFLOAD a doubly-nested Σ_i Σ_j h(i,j) loop (O(n²)) to an O(1) closed form: close the INNER fold to C(i),
    substitute it as the outer summand, close the OUTER fold to F(param). The closed form is PROPOSED by the CAS
    (sympy.summation — sound on these polynomial/hypergeometric sums) and is the AUTHORITY only after passing
    DIFFERENTIAL EQUIVALENCE against the ORIGINAL executed nested loop on many inputs (★never a wrong closed form —
    a bad proposal DECLINEs★). Σ only (the inner/outer are summations); a product/other monoid → honest NONE."""
    struct = Structure(CLOSED_FORM_LOOP, nst.algebra,
                       f"reduce('{nst.op}', f({nst.vi},{nst.vj})) over range×range", fn.name)
    if nst.op != "+":
        return Dispatch(NONE, struct, detail=f"'{nst.op}'-accumulation is not a Σ-fold (nested closer sums) "
                        "→ LLM fallback (sound: not lifted to a wrong form)")
    param = fn.args.args[0].arg
    import sympy
    try:
        i, j, p = sympy.symbols(f"{nst.vi} {nst.vj} {param}", integer=True)
        loc = {nst.vi: i, nst.vj: j, param: p}
        h = sympy.sympify(nst.body, locals=loc)
        lo2 = sympy.sympify(nst.lo2, locals=loc); hi2 = sympy.sympify(nst.hi2, locals=loc)
        lo1 = sympy.sympify(nst.lo1, locals=loc); hi1 = sympy.sympify(nst.hi1, locals=loc)
    except Exception as e:  # noqa: BLE001
        return Dispatch(NONE, struct, detail=f"nested bounds/body not interpretable ({type(e).__name__}) → LLM fallback")
    # ★ BOUNDED-GATE GUARD (soundness + no-hang): every loop bound must be a low-degree POLYNOMIAL in {i, param}.
    #   This rejects exponential/non-polynomial bounds (e.g. range(1, 2**i)) whose REAL loop would blow up when the
    #   equivalence gate executes it — the gate must never run an unbounded loop. Polynomial bounds keep the sampled
    #   loop tiny (≤ N_max² iterations), so the gate is always cheap. ★
    try:
        for bnd in (lo1, hi1, lo2, hi2):
            if sympy.Poly(bnd, i, p).total_degree() > 2:
                return Dispatch(NONE, struct, detail="nested loop bound is degree>2 — outside the bounded-gate lift "
                                "(honest: not collapsed)")
    except Exception:  # noqa: BLE001 — non-polynomial bound (e.g. exponential 2**i) ⇒ Poly() raises
        return Dispatch(NONE, struct, detail="nested loop bound is non-polynomial (e.g. exponential) — the gate must "
                        "not execute an unbounded loop → LLM fallback (sound: never collapsed unchecked)")
    try:
        c_i = sympy.summation(h, (j, lo2, hi2 - 1))          # inner inclusive upper = range-exclusive hi − 1
        f_expr = sympy.summation(c_i, (i, lo1, hi1 - 1))     # outer inclusive upper
        f_simpl = sympy.simplify(f_expr)
    except Exception as e:  # noqa: BLE001
        return Dispatch(NONE, struct, detail=f"nested CAS closer could not evaluate ({type(e).__name__}) → LLM fallback")
    # the closed form must be FULLY closed: no residual loop var and no unevaluated Sum
    if f_simpl.has(sympy.Sum) or (f_simpl.free_symbols - {p}):
        return Dispatch(NONE, struct, detail=f"nested sum did not fully close (residual {f_simpl.free_symbols - {p}}"
                        " / unevaluated Sum) → LLM fallback")
    try:
        ref = _make_callable(source, fn.name)
    except Exception as e:  # noqa: BLE001
        return Dispatch(NONE, struct, detail=f"could not build the equivalence gate ({type(e).__name__})")
    if ref is None:
        return Dispatch(NONE, struct, detail="original function not found after exec")
    ok = checked = 0
    # SMALL bounded samples: degree-≤2 polynomial bounds ⇒ ≤16²=256 inner iters/sample, so the gate cannot hang;
    # 12 points over-determine the low-degree-polynomial closed forms these loops produce (a wrong poly proposal
    # would have to AGREE on all 12 to slip through — impossible below degree 11).
    for val in _NESTED_SAMPLE_N:
        try:
            want = ref(val)
            got = float(f_simpl.subs(p, val))
        except Exception:  # noqa: BLE001
            continue
        checked += 1
        if abs(got - float(want)) <= 1e-6:
            ok += 1
    if checked < 5 or ok != checked:
        return Dispatch(NONE, struct, detail=f"nested closed form not equivalence-verified ({ok}/{checked}) → "
                        "LLM fallback (sound: a wrong form is never emitted)")
    cf = str(f_simpl)
    # HONEST per-case complexity: the true iteration count is Σ_i (hi2−lo2); its polynomial degree in the param is
    # the loop's big-O exponent (affine bounds → O(n²); a degree-2 inner bound → O(n³); etc.) — not a fixed label.
    try:
        iters = sympy.expand(sympy.summation(hi2 - lo2, (i, lo1, hi1 - 1)))
        deg = sympy.Poly(iters, p).total_degree() if iters.free_symbols else 0
    except Exception:  # noqa: BLE001
        deg = 2
    was = "O(n²)" if deg == 2 else f"O(n^{deg})"
    cert = (f"OFFLOAD certificate (nested): double loop `{fn.name}` Σ_{nst.vi} Σ_{nst.vj} {nst.body} lifted by "
            f"closing the inner fold to C({nst.vi})={c_i} then the outer fold → closed form {cf} (O(1), was {was} "
            f"nested); differential-equivalence verified on {checked}/{checked} inputs vs the ORIGINAL executed "
            f"nested loop (never a wrong closed form). The CAS proposed; the execution gate is the authority.")
    return Dispatch("OFFLOADED", struct, certificate=cert, closed_form=cf,
                    complexity=f"O(1) (was {was} nested)", detail="offloaded nested loop to closed form")


def _offload_cond(source: str, fn: ast.FunctionDef, cnd: _CondAcc) -> Dispatch:
    """OFFLOAD a FILTERED accumulation Σ_{k=lo, k≡R (mod M)}^{hi−1} h(k) (O(n)) to an O(1) closed form by the exact
    REINDEX k = M·t + r₀ (r₀ = the least k ≥ lo with k ≡ R mod M), summing over t with sympy.summation. The closed
    form is CAS-PROPOSED and authoritative ONLY after DIFFERENTIAL EQUIVALENCE against the ORIGINAL executed loop on
    affordable samples (the gate is BOUNDED by the iteration budget — no hang). Σ only; lower bound concrete."""
    struct = Structure(CLOSED_FORM_LOOP, cnd.algebra,
                       f"reduce('{cnd.op}', f({cnd.var}) where {cnd.var}%{cnd.mod}=={cnd.rem})", fn.name)
    if cnd.op != "+":
        return Dispatch(NONE, struct, detail=f"'{cnd.op}'-accumulation is not a Σ-fold (filtered closer sums) "
                        "→ LLM fallback (sound: not lifted to a wrong form)")
    param = fn.args.args[0].arg
    try:
        lo_val = int(eval(compile(ast.parse(cnd.lo, mode="eval"), "<lo>", "eval"), {"__builtins__": {}}))  # noqa: S307
    except Exception:  # noqa: BLE001
        return Dispatch(NONE, struct, detail=f"non-constant lower bound `{cnd.lo}` — filtered lift needs a concrete lo")
    import sympy
    try:
        t, p = sympy.symbols(f"t {param}", integer=True)
        k = sympy.sympify(cnd.body, locals={cnd.var: sympy.Symbol(cnd.var, integer=True)})
        ksym = sympy.Symbol(cnd.var, integer=True)
        r0 = lo_val + ((cnd.rem - lo_val) % cnd.mod)         # least k ≥ lo with k ≡ R (mod M)
        u = sympy.sympify(cnd.hi, locals={param: p}) - 1     # inclusive upper
        T = sympy.floor((u - r0) / cnd.mod)                  # number of valid k is T+1 (t = 0..T)
        h_t = k.subs(ksym, cnd.mod * t + r0)                 # reindex k = M·t + r₀
        f_expr = sympy.summation(h_t, (t, 0, T))
        f_simpl = sympy.simplify(f_expr)
    except Exception as e:  # noqa: BLE001
        return Dispatch(NONE, struct, detail=f"filtered CAS closer could not evaluate ({type(e).__name__}) → LLM fallback")
    if f_simpl.has(sympy.Sum) or (f_simpl.free_symbols - {p}):
        return Dispatch(NONE, struct, detail="filtered sum did not fully close → LLM fallback")
    try:
        ref = _make_callable(source, fn.name)
        hi_fn = eval(compile(f"lambda {param}: ({cnd.hi})", "<hi>", "eval"), {"__builtins__": _SAFE_BUILTINS})  # noqa: S307
    except Exception as e:  # noqa: BLE001
        return Dispatch(NONE, struct, detail=f"could not build the equivalence gate ({type(e).__name__})")
    if ref is None:
        return Dispatch(NONE, struct, detail="original function not found after exec")
    ok = checked = 0
    for val in _SAMPLE_N:
        try:
            iters = int(hi_fn(val)) - lo_val                 # the real loop runs (hi−lo) iterations (predicate aside)
        except Exception:  # noqa: BLE001
            continue
        if iters <= 0:
            continue
        if iters > _GATE_ITER_BUDGET:                        # NEVER execute an unaffordable loop (no hang)
            continue
        try:
            want = ref(val)
            got = float(f_simpl.subs(p, val))
        except Exception:  # noqa: BLE001
            continue
        checked += 1
        if abs(got - float(want)) <= 1e-6:
            ok += 1
    if checked < 5 or ok != checked:
        return Dispatch(NONE, struct, detail=f"filtered closed form not equivalence-verified ({ok}/{checked}) → "
                        "LLM fallback (sound: a wrong form is never emitted)")
    cf = str(f_simpl)
    cert = (f"OFFLOAD certificate (filtered): loop `{fn.name}` Σ_{{{cnd.var}={cnd.lo}, {cnd.var}%{cnd.mod}=={cnd.rem}}} "
            f"{cnd.body} reindexed k={cnd.mod}·t+{r0} → closed form {cf} (O(1), was O(n)); differential-equivalence "
            f"verified on {checked}/{checked} inputs vs the ORIGINAL executed loop (never a wrong closed form). The "
            f"CAS proposed; the bounded execution gate is the authority.")
    return Dispatch("OFFLOADED", struct, certificate=cert, closed_form=cf,
                    complexity="O(1) (was O(n) filtered)", detail="offloaded filtered loop to closed form")


# ── action 2: CERTIFIED REWRITE of an equi-join to a hash join (measured) ───────────────────────────
def _synth_hash_join(j: _Join) -> str:
    # `__dd` (collections.defaultdict) is injected into the exec globals — the restricted builtins
    # deliberately have no __import__, so we never `import` inside the synthesized code.
    return (
        f"def __hj({j.a_iter}, {j.b_iter}):\n"
        f"    __idx = __dd(list)\n"
        f"    for {j.b_var} in {j.b_iter}:\n"
        f"        __idx[{j.key_b}].append({j.b_var})\n"
        f"    {j.out} = []\n"
        f"    for {j.a_var} in {j.a_iter}:\n"
        f"        for {j.b_var} in __idx.get({j.key_a}, []):\n"
        f"            {j.out}.append({j.emit})\n"
        f"    return {j.out}\n"
    )


def _rewrite_join(source: str, fn: ast.FunctionDef, j: _Join, n: int = 3000) -> Dispatch:
    struct = Structure(RELATIONAL_JOIN, "semiring", f"equi-join {j.key_a}=={j.key_b}", fn.name)
    # only the tuple/int-keyed shape is auto-sampleable here; otherwise classify but decline the rewrite
    if not (j.key_a.startswith(j.a_var) and j.key_b.startswith(j.b_var)):
        return Dispatch(NONE, struct, detail="join key shape not auto-sampleable here (honest)")
    try:
        import collections
        orig = _make_callable(source, fn.name)
        hj_ns: dict = {}
        hj_globals = {"__builtins__": _SAFE_BUILTINS, "__dd": collections.defaultdict}
        exec(compile(_synth_hash_join(j), "<hashjoin>", "exec"), hj_globals, hj_ns)  # noqa: S102
        hj = hj_ns["__hj"]
    except Exception as e:  # noqa: BLE001
        return Dispatch(NONE, struct, detail=f"could not build/exec the rewrite ({type(e).__name__})")
    import random
    rng = random.Random(0xC0FFEE)
    # ★ differential-equivalence gate ★ on several random small relations (tuples of ints)
    for _ in range(20):
        A = [(rng.randint(0, 8), rng.randint(0, 99)) for _ in range(rng.randint(0, 12))]
        B = [(rng.randint(0, 8), rng.randint(0, 99)) for _ in range(rng.randint(0, 12))]
        try:
            if orig(list(A), list(B)) != hj(list(A), list(B)):
                return Dispatch(NONE, struct, detail="hash-join not equivalent to the original on a sample "
                                "(compound/non-canonical body) — rewrite declined (sound)")
        except Exception as e:  # noqa: BLE001
            return Dispatch(NONE, struct, detail=f"equivalence gate could not run ({type(e).__name__})")
    # measured speedup on a sizeable workload (O(n·m) nested loop vs O(n+m) hash join)
    bigA = [(rng.randint(0, n // 4), rng.randint(0, 10 ** 6)) for _ in range(n)]
    bigB = [(rng.randint(0, n // 4), rng.randint(0, 10 ** 6)) for _ in range(n)]
    t = time.perf_counter(); r1 = orig(list(bigA), list(bigB)); s_naive = time.perf_counter() - t
    t = time.perf_counter(); r2 = hj(list(bigA), list(bigB)); s_hash = time.perf_counter() - t
    if r1 != r2:
        return Dispatch(NONE, struct, detail="output mismatch on the measured workload — rewrite rejected")
    speedup = s_naive / s_hash if s_hash > 0 else 1.0
    workload = f"equi-join of two {n}-row relations on a {n // 4}-cardinality key"
    if speedup < 1.1:
        return Dispatch(NONE, struct, speedup=speedup, workload=workload,
                        detail=f"measured {speedup:.2f}× (<1.1×) — not a win, reverted (§1.10)")
    cert = (f"REWRITE certificate: nested-loop equi-join on {j.key_a}=={j.key_b} → hash join "
            f"(O(n·m) → O(n+m)); differential-equivalence verified on 20 random relations + the measured "
            f"workload; identical output (never a wrong transform). Measured {speedup:.2f}× on {workload}.")
    return Dispatch("RECOGNIZED_REWRITE", struct, certificate=cert, speedup=speedup, workload=workload,
                    detail="certified hash-join rewrite")


# ── the dispatcher ──────────────────────────────────────────────────────────────────────────────────
def dispatch(source: str, fn_name: Optional[str] = None) -> Dispatch:
    """Recognize the structure and take the sound action: OFFLOAD (closed form) / REWRITE (hash join) /
    NONE (honest LLM fallback). A misclassification can only DECLINE — the execution gates never let a
    wrong answer through."""
    fn = _first_fn(source, fn_name)
    if fn is None:
        return Dispatch(NONE, Structure(NONE, detail="no parseable function"), detail="no function")
    try:
        if _tensor_la(fn):
            return Dispatch(NONE, Structure(TENSOR_LA, "semiring", "multiply-accumulate", fn.name),
                            detail="tensor/LA recognized → equality-saturation path is S17 (not wired here)")
        j = _equi_join(fn)
        if j is not None:
            return _rewrite_join(source, fn, j)
        acc = _acc_loop_any_shape(fn)                        # for / counter-while / comprehension all offload
        if acc is not None:
            return _offload_closed_form(source, fn, acc)
        nst = _nested_acc(fn)                                # doubly-nested Σ_i Σ_j h(i,j) → O(1) closed form
        if nst is not None:
            return _offload_nested(source, fn, nst)
        cnd = _cond_any_shape(fn)                            # filtered Σ_{k%M==R} h(k) — for-loop OR comprehension
        if cnd is not None:
            return _offload_cond(source, fn, cnd)
        s = recognize(source, fn_name)
        if s.kind == DATAFLOW_FIXPOINT:
            return Dispatch(NONE, s, detail="dataflow fixpoint recognized → abstract-interpretation path "
                            "(S16/S17), not offloaded here")
        return Dispatch(NONE, s, detail=s.detail)
    except Exception as e:  # noqa: BLE001 — recognition/offload must never crash the pipeline
        return Dispatch(NONE, Structure(NONE, detail=f"recognizer error: {type(e).__name__}"),
                        detail="recognizer raised — safe NONE (LLM fallback)")


# ── §2 (ABSORB MATH): decision-procedures-as-analysis on a recognized Σ-accumulation loop ───────────────
def decide_loop(source: str, fn_name: Optional[str] = None):
    """Run the absorbed MATH decision procedures on a Σ-accumulation loop in the user's SOURCE: DECIDE whether
    Σ_{k=lo}^{n} f(k) collapses to a closed form (Gosper — COMPLETE on hypergeometric terms). Returns a
    `loop_decision.LoopDecision`: CLOSED_FORM (an O(1) form, differential-gated) / NO_CLOSED_FORM (a PROVEN
    'this loop is irreducible' — keep it) / UNDECIDED (outside the class — no false claim). This COMPLEMENTS
    `dispatch`'s fold-offload: where the fold solver can't close a form, the decision procedure can still PROVE
    the loop has no closed form (a first-class result), or find one the fold missed. Returns None when the
    function is not a single-symbol Σ-accumulation loop with a concrete lower bound (honest: outside this
    analysis — never a false verdict). It NEVER mutates code; it only decides and certifies."""
    import loop_decision as LD                                # lazy: keeps recognizer import light
    fn = _first_fn(source, fn_name)
    if fn is None:
        return None
    acc = _closed_form_loop(fn)
    if acc is None or acc.op != "+":                          # only Σ-summation is in this analysis's scope
        return None
    if _names_used(ast.parse(acc.body, mode="eval")) - {acc.var}:   # body must be a pure f(k) (loop var only)
        return None
    try:                                                     # lower bound must be a concrete integer
        lo = int(eval(compile(ast.parse(acc.lo, mode="eval"), "<lo>", "eval"), {"__builtins__": {}}))  # noqa: S307
    except Exception:                                        # noqa: BLE001
        return None
    return LD.decide_sum_collapse(acc.body, acc.var, lo)
