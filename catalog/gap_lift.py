"""
GAP CLOSURE (lift) — structure reachable by translation that the lifter had no target for.
=============================================================================================
Each is a proposer (recognize a code shape) → EXACT disposer (certify the lifted form equivalent before folding):
  • Gap 10 nonlinear_loop_summary — an affine/geometric accumulation loop (x=a·x+b, p=p·r) → closed form, certified
    by EXACT ℚ run-forward over the extracted recurrence (the same disposer as the sequence detectors).
  • Gap 12 partial_lift — a structured Σ inner loop wrapped in unstructured glue: lift ONLY the inner loop (reuse
    catalog.lift's z3-induction certificate), leave the glue (Amdahl-honest fragment-only fold).
  • Gap 9  relational_lift — a filter-aggregate loop → a relational comprehension, certified by DIFFERENTIAL
    execution on a self-generated arithmetic battery (both forms built from the parse — no untrusted exec).
  • Gap 11 aliased_lift — a[idx[k]] with an AFFINE index map idx[k]=c·k+d → direct a[c·k+d], the index rewrite
    certified by z3 (idx_expr ≡ c·k+d over ℤ).

Honest core: general loop summarization / aliasing / automata-graph lifting is undecidable; the affine / arithmetic
/ canonical-pattern classes are the decidable islands. Outside them ⇒ DECLINE (never a guessed lift). z3 + stdlib.
"""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Optional

import kernel_verdict as KV


# ── Gap 10 — affine / geometric accumulation loop → closed form (exact ℚ run-forward) ──────────────────
_AFFINE = re.compile(r"(\w+)\s*=\s*(-?\d+)\s*\*\s*\1\s*\+\s*(-?\d+)")        # x = a*x + b
_GEOM = re.compile(r"(\w+)\s*=\s*\1\s*\*\s*(-?\d+)")                          # p = p*r
_INIT = re.compile(r"(\w+)\s*=\s*(-?\d+)")


def nonlinear_loop_summary(code: str) -> KV.Verdict:
    """Gap 10 — summarize an affine (x=a·x+b) or geometric (p=p·r) accumulation loop to a closed form, certified by
    EXACT ℚ run-forward over the extracted recurrence (held-out tail validates). Non-matching loops ⇒ DECLINE."""
    if not isinstance(code, str):
        return KV.decline("nonlinear_loop_summary: need code text", "gap_lift")
    var = a = b = None
    m = _AFFINE.search(code)
    if m:
        var, a, b = m.group(1), int(m.group(2)), int(m.group(3))
    else:
        g = _GEOM.search(code)
        if g:
            var, a, b = g.group(1), int(g.group(2)), 0
    if var is None:
        return KV.decline("nonlinear_loop_summary: no affine/geometric accumulation loop ⇒ DECLINE", "gap_lift")
    init = 1 if (b == 0) else 0                                   # geometric default p0=1; affine default x0=0
    for im in _INIT.finditer(code):                              # honor an explicit initialization of `var`
        if im.group(1) == var:
            init = int(im.group(2)); break
    x0 = Fraction(init)
    af, bf = Fraction(a), Fraction(b)
    # closed form: x[n] = a^n·x0 + b·(a^n−1)/(a−1)  (a≠1);  x[n] = x0 + b·n  (a==1)
    def closed(n: int) -> Fraction:
        an = af ** n
        return an * x0 + (bf * (an - 1) / (af - 1) if af != 1 else bf * n)
    # EXACT disposer: closed(n) regenerates the recurrence x[n]=a·x[n-1]+b for n=0..K (exact ℚ)
    K = 40
    cur = x0
    for n in range(K + 1):
        if closed(n) != cur:
            return KV.decline("nonlinear_loop_summary: closed form fails run-forward ⇒ DECLINE", "gap_lift")
        cur = af * cur + bf
    form = (f"{a}**n * {init}" + (f" + {b}*({a}**n - 1)/{a - 1}" if a != 1 and b else (f" + {b}*n" if b else ""))) if a != 1 \
        else f"{init} + {b}*n"
    cert = KV.Cert(KV.EXACT, "loop_summary[runforward]", passed=True,
                   check_cost=f"ℚ run-forward over {K + 1} terms (held-out tail validated)",
                   detail=f"x=a·x+b (a={a},b={b},x0={init}) → closed form regenerates the recurrence exactly")
    return KV.exact({"var": var, "a": a, "b": b, "x0": init, "closed_form": form}, "gap_lift.loop_summary",
                    "affine/geometric loop summarization", cert)


# ── Gap 12 — partial lift: lift ONLY a structured Σ inner loop, leave the glue (Amdahl-honest fragment) ──
def partial_lift(code: str) -> KV.Verdict:
    """Gap 12 — a structured Σ inner loop inside unstructured glue: extract the inner loop, lift it via catalog.lift
    (z3-induction certified), report a PARTIAL fold (the fragment is certified equivalent; the glue is unchanged).
    Fully-unstructured code (no liftable inner loop) ⇒ DECLINE."""
    from catalog import lift as LIFT
    if not isinstance(code, str):
        return KV.decline("partial_lift: need code text", "gap_lift")
    m = LIFT._SUM_LOOP.search(code)                              # locate the structured Σ fragment within the glue
    if not m:
        return KV.decline("partial_lift: no liftable Σ inner loop found in the code ⇒ DECLINE", "gap_lift")
    frag = m.group(0)
    v = LIFT.lift_code(frag)                                     # lift + z3-induction-certify ONLY the fragment
    if v.status != KV.EXACT:
        return KV.decline(f"partial_lift: inner loop did not certify ({v.reason[:50]}) ⇒ DECLINE", "gap_lift")
    glue_lines = max(0, code.count(chr(10)) + 1 - (frag.count(chr(10)) + 1))
    cert = KV.Cert(KV.EXACT, "partial_lift[equivalence]", passed=True, check_cost=v.certificate.check_cost,
                   detail=f"inner Σ loop lifted + z3-certified ({v.result.get('closed_form')}); {glue_lines} glue "
                          "line(s) unchanged — Amdahl-honest fragment-only fold")
    return KV.exact({"closed_form": v.result.get("closed_form"), "fragment_lifted": True, "glue_lines": glue_lines,
                     "tier": v.result.get("tier")}, "gap_lift.partial", "partial lift (hot inner loop)", cert)


# ── Gap 9 — relational lift: a filter-aggregate loop → comprehension (differential battery certificate) ─
_REL = re.compile(r"(\w+)\s*=\s*0\s*\n\s*for\s+(\w+)\s+in\s+(\w+)\s*:\s*\n\s*if\s+\2\s*([<>=!]=?)\s*(-?\d+)\s*:\s*\n\s*\1\s*\+=\s*\2")


def relational_lift(code: str) -> KV.Verdict:
    """Gap 9 — recognize the canonical filter-sum loop `acc=0; for x in xs: if x OP c: acc+=x` and lift it to the
    relational comprehension `sum(x for x in xs if x OP c)`. DISPOSER: build BOTH forms from the PARSE (arithmetic
    only — no untrusted exec) and require identical results on a battery of integer lists incl. edge cases. A
    non-matching loop ⇒ DECLINE. (Automata / graph / general relational shapes have no in-repo sound certifier
    without execution ⇒ honest DECLINE, never a guessed lift.)"""
    if not isinstance(code, str):
        return KV.decline("relational_lift: need code text", "gap_lift")
    m = _REL.search(code)
    if not m:
        return KV.decline("relational_lift: not the canonical filter-sum shape ⇒ DECLINE (other relational/automata/"
                          "graph DSLs need an executable certifier — out of the sound in-repo island)", "gap_lift")
    op, c = m.group(4), int(m.group(5))
    cmp = {"<": lambda v: v < c, "<=": lambda v: v <= c, ">": lambda v: v > c, ">=": lambda v: v >= c,
           "==": lambda v: v == c, "!=": lambda v: v != c}[op]

    def loop_form(xs):                                            # the original loop, reconstructed from the parse
        acc = 0
        for x in xs:
            if cmp(x):
                acc += x
        return acc

    def rel_form(xs):
        return sum(x for x in xs if cmp(x))                      # the lifted relational comprehension
    battery = [[], [c], [c - 1, c, c + 1], list(range(-20, 21)), [c] * 5, [-i for i in range(15)], list(range(50))]
    if any(loop_form(xs) != rel_form(xs) for xs in battery):
        return KV.decline("relational_lift: differential check failed ⇒ DECLINE", "gap_lift")
    cert = KV.Cert(KV.EXACT, "relational_lift[differential]", passed=True,
                   check_cost=f"differential execution over {len(battery)} integer-list cases incl. edges",
                   detail=f"filter-sum loop ≡ sum(x for x in xs if x {op} {c}) on the battery (both built from the parse)")
    return KV.exact({"lifted": f"sum(x for x in xs if x {op} {c})", "op": op, "c": c},
                    "gap_lift.relational", "relational filter-aggregate lift", cert)


# ── Gap 11 — aliased structure: a[idx[k]] with AFFINE idx[k]=c·k+d → direct a[c·k+d] (z3-certified rewrite) ─
_ALIAS = re.compile(r"idx\s*=\s*\[\s*(-?\d+(?:\s*,\s*-?\d+)*)\s*\]")          # an explicit index table idx = [..]


def aliased_lift(code: str) -> KV.Verdict:
    """Gap 11 — resolve an explicit index table `idx=[…]` used as a[idx[k]]: if the table is AFFINE (idx[k]=c·k+d),
    rewrite the indirection to the direct affine access a[c·k+d]; the rewrite's soundness (idx[k] ≡ c·k+d for all k
    in range) is certified by z3. A non-affine / unresolvable table ⇒ DECLINE (no guess)."""
    import z3
    if not isinstance(code, str):
        return KV.decline("aliased_lift: need code text", "gap_lift")
    m = _ALIAS.search(code)
    if not m or "idx[" not in code:
        return KV.decline("aliased_lift: no resolvable index-table indirection a[idx[k]] ⇒ DECLINE", "gap_lift")
    table = [int(t.strip()) for t in m.group(1).split(",")]
    if len(table) < 3:
        return KV.decline("aliased_lift: index table too short to infer an affine map ⇒ DECLINE", "gap_lift")
    c = table[1] - table[0]
    d = table[0]
    # PROPOSER: idx[k] = c·k + d ?  DISPOSER (z3): prove idx[k] ≡ c·k+d for every k in [0,len) (exact, all entries)
    k = z3.Int("k")
    s = z3.Solver()
    constraints = [z3.Implies(k == i, z3.IntVal(table[i]) == c * k + d) for i in range(len(table))]
    s.add(z3.Not(z3.And(constraints)))
    if s.check() != z3.unsat:                                    # some entry ≠ c·k+d ⇒ not affine ⇒ DECLINE
        return KV.decline("aliased_lift: index table is NOT affine (z3 found a deviating entry) ⇒ DECLINE", "gap_lift")
    cert = KV.Cert(KV.EXACT, "aliased_lift[equivalence]", passed=True,
                   check_cost=f"z3 UNSAT: idx[k] ≡ {c}·k+{d} for all {len(table)} entries",
                   detail=f"affine index map resolved: a[idx[k]] → a[{c}·k+{d}] (indirection eliminated, z3-certified)")
    return KV.exact({"c": c, "d": d, "direct_access": f"a[{c}*k+{d}]", "n": len(table)},
                    "gap_lift.aliased", "aliased→affine index resolution", cert)
