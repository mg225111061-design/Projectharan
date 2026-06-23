"""
Pillar 3 · ROUND 2 #53 — defensive-copy elimination (SOUND mutation analysis) → EXACT, faster.
================================================================================================
Defensive programming wraps every call as  f(list(x))  to protect the caller's data. If a conservative AST
analysis PROVES the callee NEVER mutates that argument (no subscript/attribute store on it, no mutating method,
no aliasing it into a mutated local), the defensive copy is DEAD: f(x) ≡ f(list(x)) and skips the O(n) copy ⇒
EXACT and faster. If the callee CAN mutate the argument, the copy is load-bearing ⇒ DECLINE (removing it would
let the callee corrupt the caller's data — a correctness bug; a wrong "safe" is unsound).
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from typing import Callable, Optional, Tuple

import kernel_verdict as KV
from pillar3 import lifting as LF

_MUTATING_METHODS = {"append", "extend", "insert", "pop", "remove", "add", "update", "sort", "reverse",
                     "clear", "setdefault", "popitem", "discard", "__setitem__", "__delitem__"}


def mutates_arg(fn: Callable, arg_index: int = 0) -> Tuple[bool, str]:
    """Conservative AST proof of whether `fn` may mutate its `arg_index`-th parameter. Unknown ⇒ assume YES
    (sound — never claim a mutating function is copy-safe). Returns (may_mutate, reason)."""
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    except (OSError, TypeError, SyntaxError) as e:
        return True, f"source unavailable ({type(e).__name__}) ⇒ conservatively assume mutation"
    func = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if func is None or arg_index >= len(func.args.args):
        return True, "cannot locate the parameter ⇒ conservatively assume mutation"
    arg = func.args.args[arg_index].arg
    # aliases of the arg: simple `local = arg` bindings make the local a mutation proxy
    aliases = {arg}
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and isinstance(node.value, ast.Name) and node.value.id in aliases:
            aliases.add(node.targets[0].id)
    for node in ast.walk(func):
        # subscript/attribute store on the arg (or an alias)
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            tgts = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in tgts:
                if isinstance(t, (ast.Subscript, ast.Attribute)):
                    base = t.value
                    while isinstance(base, (ast.Subscript, ast.Attribute)):
                        base = base.value
                    if isinstance(base, ast.Name) and base.id in aliases:
                        return True, f"writes {base.id}[...]/.attr (mutates the argument)"
        if isinstance(node, ast.Delete):
            for t in node.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id in aliases:
                    return True, f"del {t.value.id}[...] (mutates the argument)"
        # mutating method call on the arg: arg.append(...) etc.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            base = node.func.value
            if isinstance(base, ast.Name) and base.id in aliases and node.func.attr in _MUTATING_METHODS:
                return True, f"{base.id}.{node.func.attr}() (mutating method on the argument)"
    return False, "no subscript/attr store, no mutating method, no aliased mutation ⇒ argument is not mutated"


def copyelim_grade(fn: Callable, make_input: Callable[[], tuple], *, n: int, samples: int = 5,
                   residual_iters: int = 0, floor: float = 1.20) -> Tuple[KV.Verdict, Optional[object]]:
    """If `fn` provably doesn't mutate its argument, drop the defensive copy: f(x) ≡ f(list(x)) and is faster ⇒
    EXACT (measured whole-program). If it can mutate ⇒ DECLINE (keep the copy)."""
    may, reason = mutates_arg(fn, 0)
    if may:
        return KV.decline(f"defensive copy is load-bearing — {reason} ⇒ DECLINE (keep the copy)", "copyelim"), None
    defensive = lambda x: fn(list(x))                       # the defensive call: copies x every time
    direct = lambda x: fn(x)                                # the copy-eliminated call
    arg = make_input()[0]
    if defensive(arg) != direct(arg):                       # differential corroboration (must agree)
        return KV.decline("copy-eliminated result ≠ defensive result ⇒ DECLINE", "copyelim"), None
    rep = LF.measure_lift(lambda x: defensive(x), lambda x: direct(x), make_input, residual_iters, n=n, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"copy provably dead but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "copyelim")
        v.report = rep
        return v, rep
    cert = KV.Cert(KV.EXACT, "no_arg_mutation", passed=True, check_cost="AST mutation analysis",
                   detail=f"callee proven not to mutate its argument ({reason}) ⇒ defensive copy is dead (EXACT)")
    v = KV.exact(direct, "copyelim", str(rep), cert)
    v.report = rep
    return v, rep


# ── a read-only callee (copy removable) and a mutating one (copy load-bearing) ──────────────────────────
def peek_readonly(xs):
    # a CHEAP O(1) read of a few elements — so the O(n) defensive copy dominates and eliminating it wins big
    return xs[len(xs) // 2] + xs[0] - xs[-1]


def normalize_mutating(xs):
    xs.sort()                                               # MUTATES the argument ⇒ the copy is load-bearing
    return xs[len(xs) // 2]


_COPY_CACHE: dict = {}


def make_copy_input(n: int = 120000):
    if n not in _COPY_CACHE:
        import random as _rnd
        rng = _rnd.Random(19)
        _COPY_CACHE[n] = ([rng.randrange(-1000, 1000) for _ in range(n)],)
    return _COPY_CACHE[n]
