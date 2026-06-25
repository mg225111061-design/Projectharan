"""
NATIVE ARSENAL — first-order syntactic unification (Robinson, occurs-checked), in-repo, zero external dep.
=========================================================================================================
Solve a term equation s ≐ t by computing the most-general unifier. Mechanisms ② (canonical form by solving) ⑧ ⑬.
Term grammar: a variable is a str "?x"; a compound is a tuple (functor, arg, …); a constant is a non-"?" atom / int.
★ CERTIFICATE (per-instance, §7): the MGU is APPLIED to both sides and the results must be syntactically EQUAL — a
  wrong substitution cannot pass. No unifier (functor clash / arity / occurs-check) ⇒ DECLINE with the reason.
Higher-order (non-pattern) unification is undecidable and AC-unification is only finitary ⇒ those defer; the
distinct-bound-variable Miller-pattern case reduces to this syntactic core.
"""
from __future__ import annotations

from typing import Dict, Optional

import kernel_verdict as KV


def _is_var(t) -> bool:
    return isinstance(t, str) and t.startswith("?")


def walk(t, s: Dict):
    while _is_var(t) and t in s:
        t = s[t]
    return t


def _occurs(v: str, t, s: Dict) -> bool:
    t = walk(t, s)
    if t == v:
        return True
    if isinstance(t, tuple):
        return any(_occurs(v, a, s) for a in t[1:])
    return False


def unify(a, b, s: Optional[Dict] = None) -> Optional[Dict]:
    s = {} if s is None else s
    a, b = walk(a, s), walk(b, s)
    if a == b:
        return s
    if _is_var(a):
        if _occurs(a, b, s):
            return None
        s2 = dict(s); s2[a] = b; return s2
    if _is_var(b):
        if _occurs(b, a, s):
            return None
        s2 = dict(s); s2[b] = a; return s2
    if isinstance(a, tuple) and isinstance(b, tuple) and len(a) == len(b) and a and b and a[0] == b[0]:
        for x, y in zip(a[1:], b[1:]):
            s = unify(x, y, s)
            if s is None:
                return None
        return s
    return None


def _apply(t, s: Dict):
    t = walk(t, s)
    if isinstance(t, tuple):
        return (t[0],) + tuple(_apply(a, s) for a in t[1:])
    return t


def unify_grade(a, b) -> KV.Verdict:
    """Compute the MGU of a ≐ b and CERTIFY it (apply to both sides ⇒ equal); no unifier ⇒ DECLINE with the clash."""
    s = unify(a, b)
    if s is None:
        return KV.decline(f"unify: no unifier (functor/arity clash or occurs-check) for {a!r} ≐ {b!r} ⇒ DECLINE",
                          "native_unify")
    if _apply(a, s) != _apply(b, s):                        # ★ re-check the MGU ★
        return KV.decline("unify: MGU fails the apply-to-both-sides re-check ⇒ DECLINE (bug guard)", "native_unify")
    mgu = {k: v for k, v in s.items()}
    cert = KV.Cert(KV.EXACT, "most_general_unifier", passed=True, check_cost="apply MGU to both sides ⇒ equal",
                   detail=f"MGU {mgu} unifies {a!r} ≐ {b!r} (occurs-checked, re-verified)")
    return KV.exact({"mgu": {k: _termstr(v) for k, v in mgu.items()}}, "native_unify", "Robinson unification", cert)


def _termstr(t) -> str:
    if isinstance(t, tuple):
        return f"{t[0]}(" + ",".join(_termstr(a) for a in t[1:]) + ")"
    return str(t)


def m2_unify_grade(x) -> KV.Verdict:
    """Route {"unify": [a, b]} → MGU decision."""
    if isinstance(x, dict) and "unify" in x and len(x["unify"]) == 2:
        return unify_grade(x["unify"][0], x["unify"][1])
    return KV.decline("native_unify: expected {unify:[a,b]}", "native_unify")
