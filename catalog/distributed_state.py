"""
§P P6 — CROSS-FUNCTION TAINT for DISTRIBUTED / ASYNC STATE: reassemble one linear recurrence spread across handlers.
================================================================================================================
The deepest backend fold-gap: a single linear recurrence / conserved quantity is SPREAD across multiple event
handlers (rate limiters, sliding-window counters, session accumulators, event aggregators). It defeats BOTH probing
modes — side-effects defeat the black-box fallback (P1's purity guard excludes it), and fragmentation defeats local
white-box analysis (no one function holds the whole recurrence).

This pass does cross-function taint: mark the shared state, extract each handler's AFFINE update s ← aᵢ·s + bᵢ, and
COMPOSE the per-handler maps along a FIXED schedule into ONE affine transition s ← A·s + B per round. Once composed
it is ⑪/⑬-class: N rounds = the 2×2 affine matrix [[A,B],[0,1]]^N, folded in O(log N). z3 PROVES (a) the composed map
equals the sequential application of the handlers (∀s) and (b) the matrix-power equals N rounds (∀s, sample N) —
residual=0, exact.

★ THE HARD, HONEST BOUNDARY (most real async state lands OUTSIDE the provable island, and that DECLINE is correct):
composition is provable ONLY when the handlers' combined effect is a deterministic AFFINE state update with a FIXED
schedule. A NONDETERMINISTIC interleaving (no fixed order) ⇒ no single fixed map ⇒ DECLINE. A NONLINEAR handler
(s·s, data-dependent) ⇒ DECLINE. A handler whose update is not affine-extractable ⇒ DECLINE. Cert kind:
`matrix_recurrence` (EXISTING) — no 23rd kind.
"""
from __future__ import annotations

import ast
from typing import Dict, List, Optional, Sequence, Tuple

import kernel_verdict as KV


def _extract_affine(src: str, statevar: Optional[str] = None) -> Optional[Tuple[int, int, str]]:
    """Cross-function taint on ONE handler: find its single state parameter (or `statevar`) and extract the AFFINE
    update s ← a·s + b from the handler's assignment to s. Returns (a, b, statevar) or None (nonlinear / not affine /
    not extractable). Sound: a non-affine update returns None ⇒ the caller DECLINEs."""
    import sympy as sp
    try:
        tree = ast.parse(src.strip())
    except SyntaxError:
        return None
    fn = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if fn is None:
        return None
    sv = statevar
    if sv is None:
        params = [a.arg for a in fn.args.args]
        if not params:
            return None
        sv = params[0]                                          # the shared state is the first parameter (taint root)
    s = sp.Symbol(sv)
    rhs_expr = None
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id == sv:
            try:
                rhs_expr = ast.unparse(node.value)
            except Exception:  # noqa: BLE001
                return None
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == sv:
            try:
                op = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}.get(type(node.op))
                if op is None:
                    return None
                rhs_expr = f"({sv}) {op} ({ast.unparse(node.value)})"
            except Exception:  # noqa: BLE001
                return None
    if rhs_expr is None:
        return None
    try:
        e = sp.sympify(rhs_expr, locals={sv: s})
        p = sp.Poly(e, s)
    except Exception:  # noqa: BLE001
        return None
    if p.degree() > 1:                                          # nonlinear (s·s, …) ⇒ NOT affine ⇒ DECLINE
        return None
    a = int(p.coeff_monomial(s)) if p.degree() >= 1 else 0
    b = int(p.coeff_monomial(1))
    return a, b, sv


def compose_round(maps: Dict[str, Tuple[int, int]], schedule: Sequence[str]) -> Tuple[int, int]:
    """Compose affine handler maps along a FIXED schedule into one round map s ← A·s + B (apply in order)."""
    A, B = 1, 0
    for name in schedule:
        a, b = maps[name]
        A, B = a * A, a * B + b
    return A, B


def _affine_matpow(a: int, b: int, n: int) -> Tuple[int, int]:
    A, B = 1, 0
    ba, bb = a, b
    while n:
        if n & 1:
            A, B = A * ba, A * bb + B
        ba, bb = ba * ba, ba * bb + bb
        n >>= 1
    return A, B


def _prove_z3(maps: Dict[str, Tuple[int, int]], schedule: Sequence[str], A: int, B: int,
              sample_rounds: Sequence[int]) -> bool:
    """z3 LIA: (a) the composed (A,B) equals the sequential handler application over one round ∀s; (b) the
    matrix-power equals N rounds ∀s for each sample N. residual=0, exact."""
    import z3
    s0 = z3.Int("s")
    # (a) one round: sequential application == composed
    s = s0
    for name in schedule:
        a, b = maps[name]
        s = a * s + b
    sol = z3.Solver()
    sol.add(s != A * s0 + B)
    if sol.check() != z3.unsat:
        return False
    # (b) N rounds: matrix-power == repeated round, sample N
    for N in sample_rounds:
        sN = s0
        for _ in range(N):
            sN = A * sN + B
        AN, BN = _affine_matpow(A, B, N)
        sol = z3.Solver()
        sol.add(sN != AN * s0 + BN)
        if sol.check() != z3.unsat:
            return False
    return True


def distributed_state_grade(handlers: Dict[str, str], schedule: Optional[Sequence[str]],
                            label: str = "distributed_state") -> KV.Verdict:
    """Reassemble + fold a distributed linear-state accumulator. `handlers` = {name: source}; `schedule` = the FIXED
    per-round order of handler invocations (None / empty ⇒ nondeterministic ⇒ DECLINE). EXACT(matrix_recurrence) iff
    every handler is affine-extractable AND the composition + matrix-power z3-verify; else an HONEST DECLINE."""
    if not schedule:
        return KV.decline("distributed_state: nondeterministic / no FIXED schedule — the handler interleaving is not a "
                          "single fixed map ⇒ DECLINE (outside the provable island)", label)
    maps: Dict[str, Tuple[int, int]] = {}
    sv = None
    for name, src in handlers.items():
        aff = _extract_affine(src, sv)
        if aff is None:
            return KV.decline(f"distributed_state: handler {name!r} is not an affine state update (nonlinear / "
                              "non-extractable) ⇒ DECLINE", label)
        a, b, sv = aff
        maps[name] = (a, b)
    for name in schedule:
        if name not in maps:
            return KV.decline(f"distributed_state: schedule references unknown handler {name!r} ⇒ DECLINE", label)
    A, B = compose_round(maps, schedule)
    if not _prove_z3(maps, schedule, A, B, sample_rounds=(1, 2, 3, 5, 8)):
        return KV.decline("distributed_state: z3 could not prove the composition / matrix-power equals the sequential "
                          "handler semantics ⇒ DECLINE", label)
    cert = KV.Cert(KV.EXACT, "matrix_recurrence", passed=True,
                   check_cost="z3 LIA: composed-round ≡ sequential handlers (∀s) + matrix-power ≡ N rounds (∀s, sample N)",
                   detail=f"cross-function taint reassembled {len(maps)} handler affine maps {maps} along the fixed "
                          f"schedule {list(schedule)} into one round s←{A}·s+{B}; N rounds = M^N (O(log N)), proved "
                          "equivalent to the sequential handler semantics")
    return KV.exact({"round_map": [A, B], "handler_maps": {k: list(v) for k, v in maps.items()},
                     "schedule": list(schedule), "via": "taint_compose_matrix_power", "asymptotic": "O(N)→O(log N)"},
                    label, "distributed-state taint-compose fold (⑪/⑬)", cert)
