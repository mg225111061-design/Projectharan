"""
§BQ NEW-1b — remove z3 from the TCB for the propositional/ground-EUF fragment of CHC.
=========================================================================================
`chc_solve.py` is NEVER imported-and-modified here (0 diff, verified by `test_bq_metakernel`'s git-diff
check) — this module is a PARALLEL entry point. `chc_grade_kernel()` runs Spacer itself (duplicating the
minimal invocation glue is unavoidable: chc_solve.py only exposes the synthesized invariant as a `str`,
and a string can't be safely re-parsed back into a checkable AST — see METAUPGRADE_INDEX.md item 1).

★ Safety-by-construction: `chc_grade_kernel` can ONLY emit a kernel-attributed EXACT certificate in the
narrow case where (a) init/trans/prop AND the synthesized invariant are ALL syntactically in the
propositional+ground-EUF fragment (no arithmetic, no quantifiers, no ITE/array ops — checked by
`classify_formula`, which fails CLOSED: any construct it does not explicitly recognize is rejected, never
silently admitted) AND (b) `metakernel.trusted_kernel.is_unsat_modulo_euf` independently confirms all three
re-derived Horn verification conditions. EVERY other case — out of fragment, kernel doesn't confirm, any
exception, Spacer not unsat — falls back to the EXACT SAME, unmodified `chc_solve.chc_grade()`. So this
bridge can only ADD a smaller-TCB certificate for the fragment it covers; it can never produce a verdict
the existing, already-trustworthy z3 path would not also produce.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

import z3

import chc_solve
import kernel_verdict as KV
from metakernel import trusted_kernel as TK


def _is_pure_term(t) -> bool:
    """A ground term built ONLY from constants/variables and uninterpreted function applications — no
    arithmetic, no ITE, no array select/store anywhere inside. Used to validate equality/disequality
    ARGUMENTS (the things being compared), not the Boolean formula structure around them."""
    if not z3.is_app(t):
        return False                                            # a bound/quantified variable we don't expect bare
    if z3.is_const(t):
        return True                                              # a 0-ary constant/variable, any sort — a valid EUF leaf
    if t.decl().kind() == z3.Z3_OP_UNINTERPRETED:
        return all(_is_pure_term(a) for a in t.children())
    return False                                                 # any INTERPRETED n-ary op (+,*,<=,ite,select,...) — reject


def classify_formula(e) -> str:
    """'in_fragment' iff `e` is built entirely from And/Or/Not/Implies/True/False/Bool-variables and
    Eq/Distinct atoms over pure EUF terms — else 'out_of_fragment'. FAILS CLOSED: any construct not
    explicitly recognized (arithmetic comparison, ITE, quantifier, array op, ...) is rejected, never
    silently admitted — this is the entire soundness argument for routing a VC to the kernel instead of z3."""
    try:
        if z3.is_quantifier(e) or not z3.is_app(e):
            return "out_of_fragment"
        if z3.is_true(e) or z3.is_false(e):
            return "in_fragment"
        if z3.is_const(e) and e.sort() == z3.BoolSort():
            return "in_fragment"
        if z3.is_not(e) or z3.is_and(e) or z3.is_or(e) or z3.is_implies(e):
            return "in_fragment" if all(classify_formula(c) == "in_fragment" for c in e.children()) else "out_of_fragment"
        if z3.is_eq(e) or z3.is_distinct(e):
            return "in_fragment" if all(_is_pure_term(a) for a in e.children()) else "out_of_fragment"
        return "out_of_fragment"
    except Exception:  # noqa: BLE001
        return "out_of_fragment"                                 # any introspection failure — fail closed, never guess


def _normalize(e):
    """Rewrite arity>2 Distinct into pairwise Not(Eq) conjunctions — a definitional z3-level rewrite (using
    z3's own builders, not hand-rolled semantics) so the rest of the pipeline only ever sees binary (dis)
    equality. Leaves anything classify_formula would reject untouched (it gets rejected downstream anyway)."""
    if z3.is_quantifier(e) or not z3.is_app(e):
        return e
    if z3.is_distinct(e) and e.num_args() > 2:
        args = list(e.children())
        pairs = [z3.Not(args[i] == args[j]) for i in range(len(args)) for j in range(i + 1, len(args))]
        return z3.And(*pairs)
    if z3.is_and(e):
        return z3.And(*[_normalize(c) for c in e.children()])
    if z3.is_or(e):
        return z3.Or(*[_normalize(c) for c in e.children()])
    if z3.is_not(e):
        return z3.Not(_normalize(e.children()[0]))
    if z3.is_implies(e):
        a, b = e.children()
        return z3.Implies(_normalize(a), _normalize(b))
    return e


def _term_of(t) -> TK.Term:
    if z3.is_const(t):
        return str(t.decl().name())
    return (str(t.decl().name()), tuple(_term_of(a) for a in t.children()))


class _Tseitin:
    """Tseitin transform: introduce one fresh propositional variable per distinct sub-formula node, with
    the standard biconditional-defining clauses, so a Boolean-connective tree becomes flat CNF the DPLL
    in trusted_kernel.py can search. Equality/disequality atoms are NOT Tseitin-encoded as propositional
    structure — they become entries in `eq_atoms`, handed to the EUF congruence checker instead."""

    def __init__(self) -> None:
        self.next_var = 1
        self.memo: Dict[int, int] = {}
        self.clauses: List[TK.Clause] = []
        self.eq_atoms: Dict[int, Tuple[TK.Term, TK.Term]] = {}

    def _fresh(self) -> int:
        v = self.next_var
        self.next_var += 1
        return v

    def visit(self, e) -> int:
        key = e.get_id()
        if key in self.memo:
            return self.memo[key]
        if z3.is_true(e):
            v = self._fresh(); self.clauses.append([v])
        elif z3.is_false(e):
            v = self._fresh(); self.clauses.append([-v])
        elif z3.is_const(e) and e.sort() == z3.BoolSort():
            v = self._fresh()                                    # a free Boolean variable — no defining clause needed
        elif z3.is_not(e):
            a = self.visit(e.children()[0])
            v = self._fresh()
            self.clauses += [[v, a], [-v, -a]]                    # v <-> ¬a
        elif z3.is_and(e):
            args = [self.visit(c) for c in e.children()]
            v = self._fresh()
            for a in args:
                self.clauses.append([-v, a])                       # v -> a_i  (each i)
            self.clauses.append([v] + [-a for a in args])          # (a1∧...) -> v
        elif z3.is_or(e):
            args = [self.visit(c) for c in e.children()]
            v = self._fresh()
            for a in args:
                self.clauses.append([-a, v])                       # a_i -> v  (each i)
            self.clauses.append([-v] + args)                       # v -> (a1∨...)
        elif z3.is_implies(e):
            a_t, b_t = e.children()
            a, b = self.visit(a_t), self.visit(b_t)
            v = self._fresh()
            self.clauses += [[a, v], [-b, v], [-v, -a, b]]          # v <-> (a -> b)
        elif z3.is_distinct(e):                                    # arity 2 only — _normalize expanded the rest
            a_t, b_t = e.children()
            w = self._fresh()                                      # w := (a == b)
            self.eq_atoms[w] = (_term_of(a_t), _term_of(b_t))
            v = self._fresh()
            self.clauses += [[v, w], [-v, -w]]                      # v <-> ¬w
        elif z3.is_eq(e):
            a_t, b_t = e.children()
            v = self._fresh()
            self.eq_atoms[v] = (_term_of(a_t), _term_of(b_t))
        else:
            raise ValueError(f"tseitin: unrecognized node {e} — should have been rejected by classify_formula")
        self.memo[key] = v
        return v


def fragment_check_and_extract(e) -> Optional[Tuple[List[TK.Clause], Dict[int, Tuple[TK.Term, TK.Term]], int]]:
    """Normalize, classify, and (only if in-fragment) Tseitin-extract — all on the SAME normalized formula,
    so classification and extraction can never disagree about what they examined. None ⇒ out of fragment."""
    e2 = _normalize(e)
    if classify_formula(e2) != "in_fragment":
        return None
    ts = _Tseitin()
    top = ts.visit(e2)
    return (ts.clauses, ts.eq_atoms, top)


def kernel_confirms_unsat(e) -> Optional[bool]:
    """None = out of fragment, no claim made. True/False = the kernel's EXACT verdict on whether `e` is
    UNSAT — decided by propositional+ground-EUF DPLL, ZERO z3 solver calls in this function."""
    extracted = fragment_check_and_extract(e)
    if extracted is None:
        return None
    clauses, eq_atoms, top = extracted
    return TK.is_unsat_modulo_euf(clauses + [[top]], eq_atoms)


def try_kernel_certify(init_f, trans_f, prop_f, xs: List, xps: List, inv_formula) -> Optional[KV.Verdict]:
    """Given the three state predicates and a CANDIDATE invariant (already a z3 AST — wherever it came
    from), try both de-Bruijn substitution orderings (the same sound disambiguation chc_solve.py uses: a
    candidate is accepted only for the ordering whose re-derived Horn conditions actually hold) and kernel-
    check the three resulting verification conditions. Returns the EXACT/kernel-attributed verdict on
    success, or None (try the next ordering / fall back to the unmodified z3 path) — never a guess."""
    n = len(xs)
    for perm in (list(range(n)), list(reversed(range(n)))):
        sub_x = [xs[perm[i]] for i in range(n)]
        sub_xp = [xps[perm[i]] for i in range(n)]
        I_x = z3.substitute_vars(inv_formula, *sub_x)
        I_xp = z3.substitute_vars(inv_formula, *sub_xp)
        vc0, vc1, vc2 = z3.And(init_f, z3.Not(I_x)), z3.And(I_x, trans_f, z3.Not(I_xp)), z3.And(I_x, z3.Not(prop_f))
        r0, r1, r2 = kernel_confirms_unsat(vc0), kernel_confirms_unsat(vc1), kernel_confirms_unsat(vc2)
        if r0 is True and r1 is True and r2 is True:
            cert = KV.Cert(KV.EXACT, "kernel_checked_chc_euf", passed=True,
                           check_cost="propositional+ground-EUF DPLL (metakernel.trusted_kernel) — zero z3 in this certificate's TCB",
                           detail=f"invariant independently re-verified by the kernel (no z3 solver call for the re-check): {inv_formula}")
            return KV.exact({"safe": True, "invariant": str(inv_formula)}, "chc_kernel", "CHC/Spacer+kernel", cert)
    return None


def chc_grade_kernel(varnames: List[str], init: Callable, trans: Callable, prop: Callable) -> KV.Verdict:
    """CHC safety, kernel-checked when possible. Falls back to the UNCHANGED chc_solve.chc_grade() for
    every case outside the propositional/ground-EUF fragment, or if anything about the kernel path fails —
    this function can only ever ADD a smaller-TCB certificate, never relax soundness.

    ★ Honest limitation (measured, not assumed): z3's Spacer defaults to LINEAR-ARITHMETIC invariant
    synthesis for IntSort Horn relations even when init/trans/prop themselves use only equality — see
    METAUPGRADE_MEASURE.md. So for chc_solve.py's current Int-only state interface, the in-fragment case
    fires less often than the "fragment of CHC" framing might suggest; `try_kernel_certify` (factored out
    above) is the part proven correct by direct test against a hand-supplied in-fragment invariant, and the
    safe-fallback behavior (this function degrading to the unmodified path whenever the precondition is not
    met) holds unconditionally regardless of how often Spacer's synthesis happens to land in-fragment."""
    try:
        n = len(varnames)
        xs = [z3.Int(v) for v in varnames]
        xps = [z3.Int(v + "!p") for v in varnames]
        s = {varnames[i]: xs[i] for i in range(n)}
        sprime = {varnames[i]: xps[i] for i in range(n)}
        init_f, trans_f, prop_f = init(s), trans(s, sprime), prop(s)
        if any(classify_formula(f) != "in_fragment" for f in (init_f, trans_f, prop_f)):
            return chc_solve.chc_grade(varnames, init, trans, prop)
        fp = z3.Fixedpoint()
        fp.set(engine="spacer")
        Inv = z3.Function("Inv", *([z3.IntSort()] * n + [z3.BoolSort()]))
        fp.register_relation(Inv)
        for v in xs + xps:
            fp.declare_var(v)
        fp.add_rule(Inv(*xs), init_f)
        fp.add_rule(Inv(*xps), z3.And(Inv(*xs), trans_f))
        res = fp.query(z3.And(Inv(*xs), z3.Not(prop_f)))
        if res != z3.unsat:
            return chc_solve.chc_grade(varnames, init, trans, prop)     # SAT(unsafe)/unknown — defer, unchanged behavior
        ans = fp.get_answer()
        body = ans.body() if z3.is_quantifier(ans) else ans
        if not (z3.is_app(body) and body.num_args() == 2):
            return chc_solve.chc_grade(varnames, init, trans, prop)
        inv_formula = body.arg(1)
        certified = try_kernel_certify(init_f, trans_f, prop_f, xs, xps, inv_formula)
        if certified is not None:
            return certified
        return chc_solve.chc_grade(varnames, init, trans, prop)         # Spacer's invariant wasn't in-fragment — defer, never invent a verdict
    except Exception:  # noqa: BLE001
        return chc_solve.chc_grade(varnames, init, trans, prop)         # any failure in the bridge — defer, never degrade soundness


def adversarial_battery() -> dict:
    """★ Cross-checks the kernel against z3 directly (test-time evidence, not a runtime dependency): for a
    battery of toy formulas, `kernel_confirms_unsat` must agree with `z3.Solver().check()`. ★ A genuinely
    propositional/EUF CHC instance (token-passing over 2 states, no arithmetic) gets the kernel-attributed
    certificate. ★ An arithmetic CHC instance (counter reaching a bound) correctly falls back unchanged."""
    import sos_cert  # noqa: F401  (import guard — unrelated; keep flake-clean if sos absent)

    b1, b2, b3 = z3.Bools("b1 b2 b3")
    x, y, zz = z3.Ints("x y z")
    f = z3.Function("f", z3.IntSort(), z3.IntSort())
    cross_formulas = [
        z3.And(b1, z3.Not(b1)),                                  # trivially UNSAT
        z3.Or(b1, z3.Not(b1)),                                   # trivially SAT (tautology, ask "is it SAT")
        z3.And(x == y, y == zz, x != zz),                         # EUF transitivity contradiction — UNSAT
        z3.And(x == y, y == zz, x == zz),                         # consistent — SAT
        z3.And(x == y, f(x) != f(y)),                             # function congruence contradiction — UNSAT
        z3.Implies(b1, b2),                                      # SAT (e.g. b1=F)
        z3.And(z3.Implies(b1, b2), b1, z3.Not(b2)),               # modus-ponens violation — UNSAT
        z3.Distinct(x, y, zz),                                    # SAT (3 distinct values, in-fragment via Distinct expansion)
    ]
    agree = []
    for f_ in cross_formulas:
        k = kernel_confirms_unsat(f_)
        s = z3.Solver(); s.add(f_)
        z3_sat = s.check() == z3.sat
        z3_unsat_expected = not z3_sat
        agree.append(k is not None and k == z3_unsat_expected)

    out_of_fragment = kernel_confirms_unsat(x + 1 == y)           # arithmetic ⇒ None (no claim)

    # toy CHC: 2-state token-passing, state encoded as an Int that only ever takes value 0 or 1 — compared
    # ONLY via equality (never arithmetic), so init/trans/prop are genuinely in the propositional/ground-EUF
    # fragment even though chc_solve.py's fixed interface always declares state variables as z3.Int(...).
    def init(s):
        return s["loc"] == 0

    def trans(s, sp):
        return z3.Or(z3.And(s["loc"] == 0, sp["loc"] == 1), z3.And(s["loc"] == 1, sp["loc"] == 0))

    def prop(s):
        return z3.Or(s["loc"] == 0, s["loc"] == 1)                # inductively true: trans always sets loc to 0 or 1

    v_bool = chc_grade_kernel(["loc"], init, trans, prop)
    # ★ measured (METAUPGRADE_MEASURE.md): z3's Spacer defaults to LINEAR-ARITHMETIC invariant synthesis for
    # IntSort relations even when init/trans/prop use only equality (it returns e.g. `¬(loc≥2) ∧ ¬(loc≤-1)`,
    # not `loc=0 ∨ loc=1`) — so chc_grade_kernel correctly falls back here, exercising the SAFE-FALLBACK path,
    # not the kernel-attribution path. That is itself the property under test for this call.
    safely_deferred = v_bool.status in ("EXACT", "PROBABILISTIC", "DECLINE") and (
        v_bool.certificate is None or v_bool.certificate.kind != "kernel_checked_chc_euf")
    # ★ the kernel-ATTRIBUTION mechanism itself, tested directly with a HAND-SUPPLIED in-fragment invariant
    # (bypassing Spacer's actual synthesis) — proves try_kernel_certify's permutation/VC/dispatch logic is
    # correct whenever its precondition (an in-fragment invariant) is met, independent of how often Spacer's
    # synthesis happens to land there for this particular instance.
    loc, locp = z3.Int("loc"), z3.Int("loc!p")
    init_f, trans_f, prop_f = init({"loc": loc}), trans({"loc": loc}, {"loc": locp}), prop({"loc": loc})
    bound = z3.Var(0, z3.IntSort())                                # de-Bruijn placeholder — matches fp.get_answer()'s shape
    hand_inv = z3.Or(bound == 0, bound == 1)                       # the EUF-shaped invariant Spacer did not choose
    certified = try_kernel_certify(init_f, trans_f, prop_f, [loc], [locp], hand_inv)
    kernel_attributed = (certified is not None and certified.status == "EXACT"
                         and certified.certificate.kind == "kernel_checked_chc_euf")

    # arithmetic CHC: counter x with x' = x+1, prop: x < 100 — NOT in fragment ⇒ must defer (no kernel attribution)
    def init_arith(s):
        return s["x"] == 0

    def trans_arith(s, sp):
        return sp["x"] == s["x"] + 1

    def prop_arith(s):
        return s["x"] >= 0                                        # true invariant but k-induction/CHC may say SAFE or UNKNOWN

    v_arith = chc_grade_kernel(["x"], init_arith, trans_arith, prop_arith)
    arith_not_kernel_attributed = not (v_arith.certificate is not None and v_arith.certificate.kind == "kernel_checked_chc_euf")

    cases = {
        "kernel_z3_agree_on_all_cross_checks": all(agree),
        "out_of_fragment_returns_none": out_of_fragment is None,
        "spacer_arith_bias_safely_deferred": safely_deferred,        # measured limitation, see METAUPGRADE_MEASURE.md
        "try_kernel_certify_works_given_in_fragment_invariant": kernel_attributed,
        "arithmetic_chc_never_kernel_attributed": arith_not_kernel_attributed,
        "arithmetic_chc_still_gets_a_verdict": v_arith.status in ("EXACT", "PROBABILISTIC", "DECLINE"),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2, default=str))
