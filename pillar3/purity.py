"""
Pillar 3 · ROUND 3 #68 — purity / determinism analysis → EXACT memoization (SOUND static analysis).
====================================================================================================
Memoization is only behavior-preserving for a PURE function: same inputs ⇒ same output, no side effects to
skip. Memoizing an impure function is a correctness bug (a cache hit returns a stale result and skips the side
effect). So we MEMOIZE ONLY when a conservative AST analysis PROVES purity — no impure calls (I/O, random,
time, mutation methods), no global/nonlocal writes, no argument mutation, no yield, and only whitelisted
builtins / self-recursion. If purity cannot be established, the function is treated as impure ⇒ DECLINE (a
wrong "pure" would be a correctness bug — Constitution: a wrong "safe" is unsound). Pure ⇒ memoize ⇒ EXACT,
measured whole-program. (Conservative: unknown ⇒ impure; we never over-approximate purity.)
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from typing import Callable, Optional, Tuple

import kernel_verdict as KV
from pillar3 import lifting as LF

# builtins that are pure (deterministic, side-effect-free) — anything else called is conservatively impure
_PURE_BUILTINS = {"len", "abs", "min", "max", "sum", "range", "int", "float", "str", "bool", "tuple", "list",
                  "dict", "set", "frozenset", "sorted", "map", "filter", "zip", "enumerate", "round", "pow",
                  "divmod", "all", "any", "reversed", "ord", "chr", "bin", "hex", "complex"}
_IMPURE_BUILTINS = {"print", "open", "input", "exec", "eval", "__import__", "globals", "locals", "setattr", "delattr"}
_IMPURE_MODULES = {"random", "time", "os", "sys", "datetime", "io", "subprocess", "socket", "requests", "secrets"}
_MUTATING_METHODS = {"append", "extend", "insert", "pop", "remove", "add", "update", "sort", "clear",
                     "setdefault", "popitem", "discard", "writelines", "write", "seek", "__setitem__"}


def is_pure(fn: Callable) -> Tuple[bool, str]:
    """Conservative AST purity proof. Returns (pure, reason). Unknown ⇒ impure (sound — never over-approximate)."""
    try:
        src = textwrap.dedent(inspect.getsource(fn))
        tree = ast.parse(src)
    except (OSError, TypeError, SyntaxError) as e:
        return False, f"source unavailable / unparsable ({type(e).__name__}) ⇒ conservatively impure"
    func = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if func is None:
        return False, "not a plain function ⇒ conservatively impure"
    if isinstance(func, ast.AsyncFunctionDef):
        return False, "async function (awaitable effects) ⇒ impure"
    argnames = {a.arg for a in func.args.args} | {a.arg for a in func.args.kwonlyargs}
    local_fns = {func.name}                                  # self-recursion is allowed
    # SOUNDNESS: mutating a Subscript/Attribute is pure ONLY if the base is a FRESHLY-created local container
    # (mutating a fresh local can't change external state); mutating a global/free/arg name is impure.
    _FRESH = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)
    _FRESH_CALLS = {"list", "dict", "set", "tuple", "frozenset", "bytearray", "array"}
    fresh_locals = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, _FRESH) or (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                                           and val.func.id in _FRESH_CALLS):
                fresh_locals.add(node.targets[0].id)
    reasons = []
    for node in ast.walk(func):
        if isinstance(node, ast.FunctionDef) and node is not func:
            local_fns.add(node.name)                         # nested helpers (their bodies are walked too)
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            reasons.append("global/nonlocal binding (external state)")
        if isinstance(node, (ast.Yield, ast.YieldFrom, ast.Await)):
            reasons.append("yield/await (stateful)")
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                if f.id in _IMPURE_BUILTINS:
                    reasons.append(f"calls impure builtin {f.id}()")
                elif f.id not in _PURE_BUILTINS and f.id not in local_fns:
                    reasons.append(f"calls non-whitelisted function {f.id}() (unknown purity)")
            elif isinstance(f, ast.Attribute):
                base = f.value.id if isinstance(f.value, ast.Name) else None
                if base in _IMPURE_MODULES:
                    reasons.append(f"calls {base}.{f.attr}() (impure module)")
                elif f.attr in _MUTATING_METHODS:
                    reasons.append(f"mutating method .{f.attr}()")
                elif base != "math":                         # math.* is pure; any other attr-call is unknown
                    reasons.append(f"calls .{f.attr}() of unknown purity")
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if not isinstance(t, (ast.Subscript, ast.Attribute)):
                    continue                                 # plain-name binding is a local, not a mutation
                base = t.value
                while isinstance(base, (ast.Subscript, ast.Attribute)):
                    base = base.value
                if isinstance(base, ast.Name):
                    if base.id in argnames:
                        reasons.append(f"mutates argument {base.id}")
                    elif base.id not in fresh_locals:        # global / free / aliased ⇒ external mutation
                        reasons.append(f"mutates external/non-local {base.id}")
                else:
                    reasons.append("mutates a non-name target (unknown aliasing)")
    if reasons:
        return False, "; ".join(sorted(set(reasons))[:3])
    return True, "no impure calls, no global/arg mutation, only pure builtins/self-recursion ⇒ pure"


def memoize_grade(fn: Callable, make_input: Callable[[], tuple], *, n: int, samples: int = 5,
                  residual_iters: int = 0, floor: float = 1.20) -> Tuple[KV.Verdict, Optional[object]]:
    """Memoize ONLY if purity is proven; then memoization is behavior-preserving ⇒ EXACT, measured whole-program.
    Impure (or unprovable) ⇒ DECLINE (memoizing it would be unsound)."""
    pure, reason = is_pure(fn)
    if not pure:
        return KV.decline(f"purity NOT proven ({reason}) ⇒ DECLINE memoization (unsound to cache)", "memoize"), None

    def naive(workload):
        return [fn(x) for x in workload]

    def memoized(workload):
        cache = {}
        out = []
        for x in workload:
            if x not in cache:
                cache[x] = fn(x)
            out.append(cache[x])
        return out

    # differential: pure ⇒ memoized must match naive exactly
    wl = make_input()[0]
    if naive(wl) != memoized(wl):
        return KV.decline("memoized result disagrees with naive (purity claim was wrong) ⇒ DECLINE", "memoize"), None
    rep = LF.measure_lift(lambda w: naive(w), lambda w: memoized(w), make_input, residual_iters, n=n, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"pure but memoization gives no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE",
                       "memoize")
        v.report = rep
        return v, rep
    cert = KV.Cert(KV.EXACT, "purity_proven_memoization", passed=True, check_cost="AST purity proof",
                   detail=f"function proven pure ({reason}); memoization is behavior-preserving (EXACT)")
    v = KV.exact(memoized, "memoize", str(rep), cert)
    v.report = rep
    return v, rep


# ── a PURE expensive function (memoizable, EXACT) and an IMPURE one (must DECLINE) ──────────────────────
def pure_work(x):
    s = 0
    for i in range(300):
        s += (x * i * i - 3 * x + 7) % 1000                  # pure arithmetic only
    return s


import random as _rnd                                        # noqa: E402  (used only by the impure demo fn)


def impure_work(x):
    return x + _rnd.randint(0, 9)                            # NONDETERMINISTIC ⇒ memoizing it is unsound


_GLOBAL_COUNTER = {"n": 0}


def impure_sideeffect(x):
    _GLOBAL_COUNTER["n"] += 1                                # mutates external state ⇒ a cache hit skips it
    return x * x


_WL_CACHE: dict = {}


def make_workload(unique: int = 60, reps: int = 5000):
    """A workload with many DUPLICATE args (unique≪len) so memoization of a pure fn wins big."""
    key = (unique, reps)
    if key not in _WL_CACHE:
        rng = _rnd.Random(43)
        _WL_CACHE[key] = ([rng.randrange(unique) for _ in range(reps)],)
    return _WL_CACHE[key]
