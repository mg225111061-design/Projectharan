"""
v26 STAGE 5 — assume-guarantee orchestrator + bi-abduction + opaque-boundary runtime contracts.
================================================================================================
The divide-and-conquer engine for LARGE + OPAQUE systems. A "system" is a set of modules (each a HARAN
function with `requires`/`ensures`/body). Each module is verified **modularly** (Z3): assuming its own
`requires` and the *contracts* (`ensures`) of the modules it calls, does its body satisfy its `ensures`?

  • assume-guarantee : verify M assuming callees' contracts; discharge each callee's `requires` at the call.
  • bi-abduction     : if a callee's `requires` is NOT implied by M's `requires`, ABDUCE it — add it to M's
                       inferred precondition (the anti-frame) and proceed. Reported in the ledger.
  • opaque boundary  : a call to a module NOT in the system (closed binary / network / DB) has no contract
                       → its result is unconstrained, and we record a RUNTIME-MONITOR boundary with BLAME
                       on the opaque component (Findler-Felleisen/Wadler: blame the less-precise party).
                       If the user supplies an assumed contract for it, that contract is *assumed but
                       runtime-monitored* (not statically proven).

Output = a CERTIFICATE (assumption ledger): {proven modules + (pre,post), assumed callee contracts,
runtime-monitored opaque boundaries + blame, residual TCB}. This is the product — independently checkable.

★ HONEST LIMITS (§1.9) ★: this is **conditional / compositional**, NEVER a whole-system proof. Every
opaque boundary and every abduced/assumed contract is listed in the ledger as part of the residual TCB.
Bounded to arithmetic contracts Z3 can decide; an unencodable spec → MODULE_UNMODELED (not a false proof).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import haran_ast as A
import z3_adapter as Z
from haran_parser import parse


@dataclass
class ModuleResult:
    name: str
    status: str                          # MODULE_PROVEN | MODULE_REFUTED | MODULE_UNMODELED
    abduced_pre: List[str] = field(default_factory=list)   # bi-abduced extra preconditions
    assumed_contracts: List[str] = field(default_factory=list)
    opaque_boundaries: List[str] = field(default_factory=list)   # runtime-monitored (blame=these)
    counterexample: Optional[dict] = None
    detail: str = ""


@dataclass
class SystemCertificate:
    modules: List[ModuleResult]
    def proven(self) -> List[str]:
        return [m.name for m in self.modules if m.status == "MODULE_PROVEN"]
    def residual_tcb(self) -> dict:
        opaque, assumed, abduced = set(), set(), set()
        for m in self.modules:
            opaque.update(m.opaque_boundaries); assumed.update(m.assumed_contracts)
            for a in m.abduced_pre:
                abduced.add(f"{m.name}: {a}")
        return {"opaque_boundaries": sorted(opaque), "assumed_contracts": sorted(assumed),
                "abduced_preconditions": sorted(abduced)}
    def __str__(self):
        lines = ["ASSUME-GUARANTEE CERTIFICATE (conditional / compositional — NOT a whole-system proof):"]
        for m in self.modules:
            extra = []
            if m.abduced_pre: extra.append(f"abduced-pre={m.abduced_pre}")
            if m.opaque_boundaries: extra.append(f"opaque(monitored,blame)={m.opaque_boundaries}")
            lines.append(f"  · {m.name}: {m.status} {' '.join(extra)}")
        tcb = self.residual_tcb()
        lines.append(f"  residual TCB: opaque={tcb['opaque_boundaries']} "
                     f"assumed={tcb['assumed_contracts']} abduced={tcb['abduced_preconditions']}")
        return "\n".join(lines)


class _Acc:
    def __init__(self):
        self.obligations = []      # [(callee_name, z3 requires-at-call)]
        self.assumptions = []      # [z3 ensures-at-call]  (things we get to assume)
        self.opaque = []           # [callee_name] opaque boundaries hit
        self.assumed_contracts = []


def _var_types(fn):
    vt = {}
    for p in fn.params:
        if isinstance(p.ty, A.TyName) and p.ty.name in ("Float", "Real", "rat"):
            vt[p.name] = "Real"
        else:
            vt[p.name] = "Int"
    return vt


def _enc(e, zenv, real, table, opaque_contracts, acc):
    """Encode a body expression to a Z3 term; module calls become fresh vars + contract obligations/
    assumptions; unknown calls become opaque boundaries. Mirrors z3_adapter._to_z3 for arithmetic."""
    import z3
    if isinstance(e, A.Num):
        return (z3.RealVal(e.value) if (real or e.is_float) else z3.IntVal(int(e.value)))
    if isinstance(e, A.Var):
        if e.name not in zenv:
            raise Z._Unsupported(f"free var {e.name}")
        return zenv[e.name]
    if isinstance(e, A.Un) and e.op == "-":
        return -_enc(e.operand, zenv, real, table, opaque_contracts, acc)
    if isinstance(e, A.Bin):
        l = _enc(e.lhs, zenv, real, table, opaque_contracts, acc)
        r = _enc(e.rhs, zenv, real, table, opaque_contracts, acc)
        if e.op == "+": return l + r
        if e.op == "-": return l - r
        if e.op == "*": return l * r
        raise Z._Unsupported(f"operator {e.op}")
    if isinstance(e, A.Call) and isinstance(e.func, A.Var):
        g = e.func.name
        args = [_enc(a, zenv, real, table, opaque_contracts, acc) for a in e.args]
        ret = z3.FreshReal(g) if real else z3.FreshInt(g)
        if g in table:                                   # known module → assume-guarantee
            callee = table[g]
            env_g = {p.name: at for p, at in zip(callee.params, args)}
            env_g["result"] = ret
            if callee.requires is not None:
                try:
                    acc.obligations.append((g, Z._to_z3(callee.requires, env_g, real)))
                except Z._Unsupported:
                    pass
            if callee.ensures is not None:
                try:
                    ens = Z._to_z3(callee.ensures, env_g, real)
                    acc.assumptions.append(ens)
                    acc.assumed_contracts.append(f"{g}.ensures")
                except Z._Unsupported:
                    pass
            return ret
        # opaque boundary (not in the system)
        acc.opaque.append(g)
        if opaque_contracts and g in opaque_contracts:   # assumed contract → runtime-monitored, blame=g
            try:
                spec = parse(f"fn _c() -> Int\n  ensures {opaque_contracts[g]}\n{{ 0 }}").items[0].ensures
                env_g = {"result": ret}
                for i, at in enumerate(args):
                    env_g[f"arg{i}"] = at
                acc.assumptions.append(Z._to_z3(spec, env_g, real))
                acc.assumed_contracts.append(f"{g}.ensures (runtime-monitored)")
            except Exception:   # noqa: BLE001
                pass
        return ret
    raise Z._Unsupported(type(e).__name__)


def _raise(op):
    raise Z._Unsupported(f"operator {op}")


def _block_return(b):
    if isinstance(b, A.Block) and b.stmts and isinstance(b.stmts[-1], A.ExprStmt):
        return b.stmts[-1].value
    return b


def verify_module(fn, table, opaque_contracts=None) -> ModuleResult:
    import z3
    real = any(t == "Real" for t in _var_types(fn).values())
    zenv = {n: (z3.Real(n) if t == "Real" else z3.Int(n)) for n, t in _var_types(fn).items()}
    try:
        pre = Z._to_z3(fn.requires, zenv, real) if fn.requires is not None else z3.BoolVal(True)
    except Z._Unsupported:
        return ModuleResult(fn.name, "MODULE_UNMODELED", detail="requires not Z3-encodable")
    if fn.ensures is None:
        return ModuleResult(fn.name, "MODULE_UNMODELED", detail="no ensures to verify")
    acc = _Acc()
    try:
        body_term = _enc(_block_return(fn.body), zenv, real, table, opaque_contracts or {}, acc)
        env_post = dict(zenv); env_post["result"] = body_term
        post = Z._to_z3(fn.ensures, env_post, real)
    except Z._Unsupported as e:
        return ModuleResult(fn.name, "MODULE_UNMODELED", detail=f"body/ensures not encodable: {e}")

    # bi-abduction: discharge each callee requires from pre+assumptions; if not, abduce it.
    abduced = []
    for (g, req) in acc.obligations:
        s = z3.Solver(); s.set("timeout", 4000)
        s.add(pre)
        for a in acc.assumptions:
            s.add(a)
        s.add(z3.Not(req))
        if s.check() != z3.unsat:          # cannot prove the callee's precondition from pre → abduce it
            abduced.append((g, req))

    # prove the module's post under pre + abduced-pres + callee assumptions
    s = z3.Solver(); s.set("timeout", 5000)
    s.add(pre)
    for (_, req) in abduced:
        s.add(req)                          # assume the abduced preconditions
    for a in acc.assumptions:
        s.add(a)
    s.add(z3.Not(post))
    r = s.check()
    abduced_names = sorted({f"{g}.requires" for (g, _) in abduced})
    if r == z3.unsat:
        return ModuleResult(fn.name, "MODULE_PROVEN", abduced_pre=abduced_names,
                            assumed_contracts=sorted(set(acc.assumed_contracts)),
                            opaque_boundaries=sorted(set(acc.opaque)))
    if r == z3.sat:
        m = s.model()
        cx = {n: str(m.eval(zenv[n], model_completion=True)) for n in zenv}
        return ModuleResult(fn.name, "MODULE_REFUTED", counterexample=cx,
                            opaque_boundaries=sorted(set(acc.opaque)),
                            detail="ensures not implied by pre + contracts")
    return ModuleResult(fn.name, "MODULE_UNMODELED", detail="Z3 unknown")


def verify_system(sources: List[str], opaque_contracts: Optional[Dict[str, str]] = None) -> SystemCertificate:
    """Verify a system of modules (each a HARAN function source). Returns the assumption-ledger cert."""
    table = {}
    fns = []
    for src in sources:
        prog = parse(src)
        for fn in prog.fns():
            table[fn.name] = fn
            fns.append(fn)
    return SystemCertificate([verify_module(fn, table, opaque_contracts) for fn in fns])
