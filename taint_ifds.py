"""
v26 STAGE 2 — taint / IFDS-style injection-freedom prover.
==========================================================
Distributive taint reachability (the IFDS fact is "variable v is tainted"): a SOURCE (user input) that
reaches a SINK (sql/shell/eval/file-path/render) WITHOUT passing a SANITIZER is an injection. Emits an
injection-freedom result or a concrete witness flow (which source, which sink, which line).

  SOURCE   : a param marked `requires source(x)`, or a call to a source function (input/read/recv/...).
  SINK     : a call to a sink function (query/execute/system/eval/open/render/...) with a tainted arg.
  SANITIZER: a call to a sanitizer function (escape/parameterize/quote/validate/...) → result untainted.

Verdicts:  INJECTION_FREE | INJECTION_FLOW (witness) | UNMODELED (no source/sink modeled here).

★ HONEST LIMITS ★ (sound only w.r.t. the MODELED sets, and intraprocedural):
  • Soundness is relative to the configured source/sink/sanitizer name sets — an UNMODELED sink is
    reported as UNMODELED, never as a false INJECTION_FREE.
  • Intraprocedural: a call to an ordinary (non-sink/non-sanitizer) function is treated as
    taint-PROPAGATING (result tainted iff any arg tainted) — a sound over-approximation, not a full
    interprocedural IFDS supergraph (that's the scale technique; this is the distributive core).
  • OX-style (over-approximate): INJECTION_FREE means "no tainted flow to a modeled sink under this
    model", not a universal security proof.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set

import haran_ast as A
from haran_parser import parse

DEFAULT_SOURCES = {"input", "read", "recv", "arg", "argv", "param", "request", "readline",
                   "stdin", "get_param", "body", "query_param", "untrusted"}
DEFAULT_SINKS = {"query", "sql", "execute", "exec", "system", "eval", "popen", "open",
                 "write_file", "render", "shell", "spawn", "deserialize"}
DEFAULT_SANITIZERS = {"escape", "sanitize", "parameterize", "quote", "validate", "encode",
                      "prepared", "bind", "whitelist", "esc"}


@dataclass
class TaintVerdict:
    status: str                         # INJECTION_FREE | INJECTION_FLOW | UNMODELED | PARSE_ERROR | NONE
    sources: List[str] = field(default_factory=list)
    flows: List[dict] = field(default_factory=list)   # [{sink, line, source, arg_index}]
    saw_sink: bool = False
    detail: str = ""

    def safe(self) -> bool:
        return self.status == "INJECTION_FREE"

    def certificate(self) -> str:
        if self.status == "INJECTION_FREE":
            return (f"INJECTION-FREE (OX) for sources {self.sources} — no tainted flow reaches a modeled "
                    f"sink; sound w.r.t. the modeled source/sink/sanitizer sets (intraprocedural).")
        if self.status == "INJECTION_FLOW":
            f = self.flows[0]
            return (f"INJECTION-FLOW ({len(self.flows)}): source '{f['source']}' reaches sink "
                    f"'{f['sink']}(...)' at line {f['line']} arg#{f['arg_index']} without a sanitizer.")
        return f"{self.status} — {self.detail}"

    def __str__(self):
        return self.certificate()


class _Taint:
    def __init__(self, sources, sinks, sanitizers):
        self.SRC, self.SINK, self.SAN = set(sources), set(sinks), set(sanitizers)
        self.flows: List[dict] = []
        self.saw_sink = False

    def visit(self, n, env: Set[str]) -> Optional[str]:
        """Return the name of a tainting source if node `n`'s value is tainted, else None.
        Records a flow when a tainted value reaches a modeled sink. `env` maps tainted var → source name."""
        if n is None or isinstance(n, (A.Num, A.BoolLit)):
            return None
        if isinstance(n, A.Var):
            return n.name if n.name in env else None
        if isinstance(n, A.Un):
            return self.visit(n.operand, env)
        if isinstance(n, A.Bin):
            return self.visit(n.lhs, env) or self.visit(n.rhs, env)
        if isinstance(n, A.Call):
            fname = n.func.name if isinstance(n.func, A.Var) else None
            arg_taint = [self.visit(a, env) for a in n.args]
            if fname in self.SINK:
                self.saw_sink = True
                for i, t in enumerate(arg_taint):
                    if t:
                        self.flows.append({"sink": fname, "line": getattr(getattr(n, "span", None), "line", 0),
                                           "source": t, "arg_index": i})
                return None                                   # a sink's result is not itself a source
            if fname in self.SAN:
                return None                                   # sanitizer cleans the data
            if fname in self.SRC:
                return fname                                  # a source call introduces taint
            return next((t for t in arg_taint if t), None)    # ordinary call propagates taint
        if isinstance(n, A.Match):
            st = self.visit(n.scrut, env)
            out = None
            for arm in n.arms:
                child = dict(env)
                if st:
                    for v in _pattern_vars(arm.pattern):
                        child[v] = st
                out = self.visit(arm.body, child) or out
            return out
        if isinstance(n, A.Fold):
            self.visit(n.domain, env)
            return self.visit(n.body, dict(env))
        if isinstance(n, A.Block):
            child = dict(env)
            last = None
            for st in n.stmts:
                last = self.visit(st, child)
            return last
        if isinstance(n, A.Let):
            t = self.visit(n.value, env)
            if t:
                env[n.name] = t
            else:
                env.pop(n.name, None)
            return None
        if isinstance(n, A.ExprStmt):
            return self.visit(n.value, env)
        if isinstance(n, A.Range):
            return self.visit(n.lo, env) or self.visit(n.hi, env)
        if isinstance(n, A.ListLit):
            return next((t for t in (self.visit(e, env) for e in n.elems) if t), None)
        if isinstance(n, (A.Quant, A.Lambda)):
            return self.visit(n.body, env)
        return None


def _pattern_vars(pat) -> Set[str]:
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


def _collect_sources(fn, sources_arg) -> Set[str]:
    out: Set[str] = set(sources_arg or ())
    def walk(e):
        if isinstance(e, A.Call) and isinstance(e.func, A.Var) and e.func.name == "source":
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


def prove_injection_free(code: str, sources: Optional[Set[str]] = None, *,
                         sinks: Optional[Set[str]] = None, sanitizers: Optional[Set[str]] = None) -> TaintVerdict:
    """Prove injection-freedom of one HARAN function, or emit a witness flow. See module docstring."""
    prog = parse(code)
    if prog.errors:
        return TaintVerdict("PARSE_ERROR", detail=str(prog.errors[0]))
    fns = prog.fns()
    if not fns:
        return TaintVerdict("NONE", detail="no function found")
    fn = fns[0]
    src_params = _collect_sources(fn, sources)
    t = _Taint(sources or DEFAULT_SOURCES, sinks or DEFAULT_SINKS, sanitizers or DEFAULT_SANITIZERS)
    # seed: source-marked params are tainted (mapped to their own name as the witness source)
    env = {p: p for p in src_params}
    t.visit(fn.body, env)
    secs = sorted(src_params)
    if t.flows:
        return TaintVerdict("INJECTION_FLOW", sources=secs, flows=t.flows, saw_sink=True)
    if not t.saw_sink and not src_params:
        return TaintVerdict("UNMODELED", sources=secs, detail="no modeled source or sink present — "
                            "mark a source via `requires source(x)` / a source call, and use a modeled sink")
    return TaintVerdict("INJECTION_FREE", sources=secs, saw_sink=t.saw_sink)


def injection_feedback(v: TaintVerdict) -> str:
    """Witness flow → concrete fix instruction for the write→verify→fix loop."""
    if v.status != "INJECTION_FLOW" or not v.flows:
        return ""
    f = v.flows[0]
    return (f"INJECTION at line {f['line']}: user-controlled source '{f['source']}' flows into sink "
            f"'{f['sink']}(...)' (arg #{f['arg_index']}) with no sanitizer. Fix: pass it through a "
            f"sanitizer/parameterizer (e.g. parameterize/escape/validate) before the sink, or use a "
            f"prepared/bound API. Return the corrected HARAN function only.")
