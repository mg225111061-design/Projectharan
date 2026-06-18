"""
v26 STAGE 1 — constant-time / secret-taint certifier (HARAN-IR level, 2-safety taint). ★FLAGSHIP★
=================================================================================================
The differentiated capability: an LLM can only *guess* that code is secret-independent; it cannot
*prove* it. This emits a machine certificate — CT_PROVEN — or a concrete leak counterexample. General,
domain-agnostic: a value labeled `secret` (a key, token, password — anything) must not influence

  (a) a BRANCH condition         (match on secret → control-flow timing leak)
  (b) a MEMORY access index      (table/array indexed by secret → cache-timing leak)
  (c) a VARIABLE-TIME operation  (`/` or `%` with a secret operand — the KyberSlash *class* of bug:
                                  secret-dependent division leaks via timing; this is NOT a claim
                                  that this project implements Kyber — it's the canonical example)
  (d) a LOOP TRIP COUNT          (fold over a secret-dependent range → secret iteration count)

Labels: mark secrets via `requires secret(x)` in the HARAN spec, or pass `secrets={"x", ...}`.

★ HONEST LEVEL LABELING (non-negotiable) ★: this proves constant-timeness at the **HARAN-IR level**.
It does NOT cover binary-level leaks a COMPILER may introduce (Binsec/Rel showed gcc/clang passes inject
CT violations into source-safe code). The certificate says exactly this; never claim binary CT here.

Soundness stance: CT_PROVEN is emitted ONLY when the whole function was modeled and no secret reaches a
leak site. Any unmodeled construct → UNMODELED (we do NOT claim proven). A leak → CT_VIOLATION with the
exact construct + line (a concrete counterexample the write→verify→fix loop feeds back to the model).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set

import haran_ast as A
from haran_parser import parse

# operations whose latency is classically data-dependent (constant-time code must avoid these on secrets)
_VARTIME_OPS = {"/", "%"}
# memory-access style calls: a secret in an INDEX position (any arg after the collection) is a leak.
# (HARAN has no subscript node; table/array access is modeled via these configurable function names.)
_INDEX_FNS = {"get", "at", "nth", "index", "lookup", "table", "select", "load", "fetch"}


@dataclass
class CTVerdict:
    status: str                       # CT_PROVEN | CT_VIOLATION | UNMODELED | NO_SECRETS | PARSE_ERROR | NONE
    secrets: List[str] = field(default_factory=list)
    leaks: List[dict] = field(default_factory=list)     # [{kind, line, detail}]
    unmodeled: List[str] = field(default_factory=list)
    level: str = "HARAN-IR"
    detail: str = ""

    def proven(self) -> bool:
        return self.status == "CT_PROVEN"

    def certificate(self) -> str:
        if self.status == "CT_PROVEN":
            return (f"CT-CERT: constant-time PROVEN at {self.level} level for secrets {self.secrets} — "
                    f"no secret-dependent branch / memory index / variable-time op / loop bound. "
                    f"★ binary-level NOT covered (a compiler may introduce leaks — Binsec/Rel).")
        if self.status == "CT_VIOLATION":
            first = self.leaks[0]
            return (f"CT-VIOLATION ({len(self.leaks)} leak(s)) at {self.level} level; first: line "
                    f"{first['line']}: {first['detail']}")
        return f"{self.status} — {self.detail}"

    def __str__(self):
        return self.certificate()


def _pattern_vars(pat) -> Set[str]:
    """Variable names a pattern binds (these inherit the scrutinee's taint)."""
    out: Set[str] = set()
    if isinstance(pat, A.PVar):
        out.add(pat.name)
    elif isinstance(pat, A.PCons):
        out |= _pattern_vars(pat.head) | _pattern_vars(pat.tail)
    elif isinstance(pat, A.PList):
        for e in pat.elems:
            out |= _pattern_vars(e)
    elif isinstance(pat, A.PCtor):
        for a in pat.args:
            out |= _pattern_vars(a)
    return out


class _Analyzer:
    def __init__(self):
        self.leaks: List[dict] = []
        self.unmodeled: List[str] = []

    def _leak(self, kind: str, node, detail: str):
        self.leaks.append({"kind": kind, "line": getattr(getattr(node, "span", None), "line", 0),
                           "detail": detail})

    def visit(self, n, env: Set[str]) -> bool:
        """Walk node `n`; record any leaks; return True iff the node's VALUE is secret-tainted.
        `env` is the set of secret-tainted variable names in scope (mutated by Let within a Block)."""
        if n is None:
            return False
        if isinstance(n, (A.Num, A.BoolLit)):
            return False
        if isinstance(n, A.Var):
            return n.name in env
        if isinstance(n, A.Un):
            return self.visit(n.operand, env)
        if isinstance(n, A.Bin):
            ls = self.visit(n.lhs, env)
            rs = self.visit(n.rhs, env)
            if n.op in _VARTIME_OPS and (ls or rs):
                self._leak("var_time_op", n, f"variable-time op '{n.op}' on a secret-dependent operand "
                           f"(data-dependent timing — the KyberSlash *class* of leak)")
            return ls or rs
        if isinstance(n, A.Call):
            fname = n.func.name if isinstance(n.func, A.Var) else None
            arg_secret = [self.visit(a, env) for a in n.args]
            if fname in _INDEX_FNS and len(arg_secret) >= 2 and any(arg_secret[1:]):
                self._leak("mem_index", n, f"memory access '{fname}(...)' indexed by a secret-dependent "
                           f"value (table/cache-timing leak — use a constant-time scan)")
            return any(arg_secret)
        if isinstance(n, A.Match):
            sc = self.visit(n.scrut, env)
            if sc:
                self._leak("branch", n, "secret-dependent branch — `match` on a secret-tainted value "
                           "(control-flow timing leak; use arithmetic select / masking)")
            any_arm = False
            for arm in n.arms:
                child = set(env)
                if sc:
                    child |= _pattern_vars(arm.pattern)   # vars from a secret scrutinee are secret
                any_arm = self.visit(arm.body, child) or any_arm
            return sc or any_arm
        if isinstance(n, A.Fold):
            if isinstance(n.domain, A.Range):
                if self.visit(n.domain.lo, env) or self.visit(n.domain.hi, env):
                    self._leak("secret_loop_bound", n, "fold over a secret-dependent range — secret "
                               "iteration count (timing leak; iterate a fixed public range)")
            else:
                self.visit(n.domain, env)
            return self.visit(n.body, set(env))           # binder ranges over a public domain
        if isinstance(n, A.Block):
            child = set(env)
            last = False
            for st in n.stmts:
                last = self.visit(st, child)
            return last
        if isinstance(n, A.Let):
            if self.visit(n.value, env):
                env.add(n.name)                            # block-scoped taint binding
            return False
        if isinstance(n, A.ExprStmt):
            return self.visit(n.value, env)
        if isinstance(n, A.Range):
            return self.visit(n.lo, env) or self.visit(n.hi, env)
        if isinstance(n, A.ListLit):
            return any(self.visit(e, env) for e in n.elems)
        if isinstance(n, A.Quant):
            return self.visit(n.body, env)
        if isinstance(n, A.Lambda):
            return self.visit(n.body, env)
        # a construct we don't model — record it so we never claim CT_PROVEN over unknown control/data flow
        self.unmodeled.append(type(n).__name__)
        return False


def _collect_secrets(fn, secrets: Optional[Set[str]]) -> Set[str]:
    """Secrets = explicit `secrets` arg ∪ every `secret(param)` marker in the `requires` clause."""
    out: Set[str] = set(secrets or ())
    def walk(e):
        if isinstance(e, A.Call) and isinstance(e.func, A.Var) and e.func.name == "secret":
            for a in e.args:
                if isinstance(a, A.Var):
                    out.add(a.name)
        if isinstance(e, A.Bin):
            walk(e.lhs); walk(e.rhs)
        elif isinstance(e, A.Un):
            walk(e.operand)
    if fn.requires is not None:
        walk(fn.requires)
    return out


def certify_ct(code: str, secrets: Optional[Set[str]] = None) -> CTVerdict:
    """Certify constant-timeness of one HARAN function (HARAN-IR level). See module docstring."""
    prog = parse(code)
    if prog.errors:
        return CTVerdict("PARSE_ERROR", detail=str(prog.errors[0]))
    fns = prog.fns()
    if not fns:
        return CTVerdict("NONE", detail="no function found")
    fn = fns[0]
    sec = _collect_secrets(fn, secrets)
    if not sec:
        return CTVerdict("NO_SECRETS", detail="no secret-labeled inputs — mark with `requires secret(x)` "
                         "or pass secrets={...}; nothing to certify")
    an = _Analyzer()
    an.visit(fn.body, set(sec))
    secs = sorted(sec)
    if an.leaks:
        return CTVerdict("CT_VIOLATION", secrets=secs, leaks=an.leaks, unmodeled=an.unmodeled)
    if an.unmodeled:
        return CTVerdict("UNMODELED", secrets=secs, unmodeled=sorted(set(an.unmodeled)),
                         detail=f"unmodeled constructs {sorted(set(an.unmodeled))} — not claiming CT_PROVEN")
    return CTVerdict("CT_PROVEN", secrets=secs)


def ct_feedback(v: CTVerdict) -> str:
    """Concrete counterexample → fix instruction for the write→verify→fix loop (precise, not vague)."""
    if v.status != "CT_VIOLATION" or not v.leaks:
        return ""
    f = v.leaks[0]
    hints = {
        "branch": "replace the secret-dependent `match` with a constant-time arithmetic select/mask "
                  "(compute both arms, select with a 0/1 secret mask).",
        "var_time_op": "remove the secret-dependent `/`/`%` — use Montgomery/Barrett reduction or a "
                       "constant-time routine instead of hardware division.",
        "mem_index": "replace the secret-indexed lookup with a constant-time linear scan over the table.",
        "secret_loop_bound": "iterate a FIXED public range; do not let a secret determine the trip count.",
    }
    return (f"CONSTANT-TIME VIOLATION at line {f['line']}: {f['detail']}. "
            f"Fix: {hints.get(f['kind'], 'make the secret-dependent operation constant-time')} "
            f"Return the corrected constant-time HARAN function only.")
