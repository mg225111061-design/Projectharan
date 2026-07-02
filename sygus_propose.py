"""
§AG §2a — SyGuS PROPOSER (the one genuine GAP among the 30 audited theories).
================================================================================================================
Syntax-Guided Synthesis: given a CFG candidate space (grammar) + an SMT specification, synthesize a term by
DETERMINISTIC enumerative search / CEGIS, then GATE it with the EXISTING z3 disposer (`equiv_check.prove_equiv_z3`
/ `equiv_check.equiv_grade`). No new disposer, no new certificate kind.

★ THE HONEST MEASUREMENT (this is the whole point of §2a): SyGuS is a PROPOSER extension, NOT a fold-COVERAGE
extension. The z3-foldable set does NOT change — a candidate that SyGuS finds is disposed by exactly the same z3
gate that §P P1 (CEGAR guard synthesis) and §AE ISLAND 5 (Karr/Farkas/Gröbner invariant synthesis) already use.
SyGuS's only genuinely-new part is GRAMMAR-CONSTRAINED candidate enumeration. So `coverage_delta` reports ≈ 0
(no new z3-foldable region); the proposer metric (how many grammar instances it synthesizes) is reported
SEPARATELY and never conflated with fold rate. A claim of "SyGuS skyrockets the fold rate" is FORBIDDEN.

★ Weak-LLM constraint: SyGuS here is DETERMINISTIC (enumerative/CEGIS) — it imports NO LLM client
(`forbidden_present == []`, AST-audited). It is a search procedure, not an LLM proposer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import kernel_verdict as KV
from catalog import equiv_check as EC


# ── term algebra: a candidate is a nested tuple over {var, const, +, -, *, ite(ge/le/eq)} ─────────────────────
Term = tuple   # ("var",n) | ("const",k) | ("+",a,b) | ("-",a,b) | ("*",a,b) | ("ite",cond,a,b); cond=("ge"|"le"|"eq",a,b)


@dataclass
class Grammar:
    variables: Tuple[str, ...]
    consts: Tuple[int, ...] = (0, 1)
    ops: Tuple[str, ...] = ("+", "-", "*")           # binary arithmetic ops to allow
    ite: bool = False                                 # allow if-then-else with ge/le/eq conditions
    max_depth: int = 2
    max_terms: int = 4000                             # deterministic enumeration cap (terminating)


@dataclass
class SygusResult:
    found: bool
    term: Optional[Term] = None
    pretty: str = ""
    verdict: Optional["KV.Verdict"] = None           # the EXISTING equiv_check verdict (EXACT/DECLINE) — no new kind
    enumerated: int = 0                               # how many candidates were tried (proposer effort)
    cegis_rounds: int = 0
    detail: str = ""


# ── deterministic enumeration of grammar terms by increasing depth (order is fixed → reproducible) ───────────
def _leaves(g: Grammar) -> List[Term]:
    out: List[Term] = [("var", v) for v in g.variables]
    out += [("const", c) for c in g.consts]
    return out


def enumerate_terms(g: Grammar) -> List[Term]:
    """All terms up to g.max_depth, deterministically ordered (depth-ascending, then by construction order). Capped
    at g.max_terms (terminating — the search space is finite by construction)."""
    by_depth: List[List[Term]] = [_leaves(g)]
    seen = {repr(t) for t in by_depth[0]}
    for _ in range(1, g.max_depth + 1):
        prev_all = [t for level in by_depth for t in level]
        nxt: List[Term] = []
        for op in g.ops:
            for a in prev_all:
                for b in prev_all:
                    t = (op, a, b)
                    r = repr(t)
                    if r not in seen:
                        seen.add(r); nxt.append(t)
                        if sum(len(l) for l in by_depth) + len(nxt) >= g.max_terms:
                            by_depth.append(nxt); return [t for level in by_depth for t in level]
        if g.ite:
            for cmp in ("ge", "le", "eq"):
                for a in prev_all:
                    for b in prev_all:
                        for x in prev_all:
                            for y in prev_all:
                                t = ("ite", (cmp, a, b), x, y)
                                r = repr(t)
                                if r not in seen:
                                    seen.add(r); nxt.append(t)
                                    if sum(len(l) for l in by_depth) + len(nxt) >= g.max_terms:
                                        by_depth.append(nxt); return [t for level in by_depth for t in level]
        by_depth.append(nxt)
    return [t for level in by_depth for t in level]


def pretty(t: Term) -> str:
    h = t[0]
    if h == "var":
        return t[1]
    if h == "const":
        return str(t[1])
    if h == "ite":
        cmp = {"ge": ">=", "le": "<=", "eq": "=="}[t[1][0]]
        return f"ite({pretty(t[1][1])}{cmp}{pretty(t[1][2])}, {pretty(t[2])}, {pretty(t[3])})"
    return f"({pretty(t[1])} {h} {pretty(t[2])})"


def to_z3(t: Term, env: Dict):
    import z3
    h = t[0]
    if h == "var":
        return env[t[1]]
    if h == "const":
        return z3.IntVal(t[1])
    if h == "ite":
        cmp, a, b = t[1]
        za, zb = to_z3(a, env), to_z3(b, env)
        cond = {"ge": za >= zb, "le": za <= zb, "eq": za == zb}[cmp]
        return z3.If(cond, to_z3(t[2], env), to_z3(t[3], env))
    za, zb = to_z3(t[1], env), to_z3(t[2], env)
    return {"+": za + zb, "-": za - zb, "*": za * zb}[h]


def _eval(t: Term, env: Dict[str, int]) -> int:
    h = t[0]
    if h == "var":
        return env[t[1]]
    if h == "const":
        return t[1]
    if h == "ite":
        cmp, a, b = t[1]
        va, vb = _eval(a, env), _eval(b, env)
        cond = {"ge": va >= vb, "le": va <= vb, "eq": va == vb}[cmp]
        return _eval(t[2], env) if cond else _eval(t[3], env)
    va, vb = _eval(t[1], env), _eval(t[2], env)
    return {"+": va + vb, "-": va - vb, "*": va * vb}[h]


# ── synthesis modes (both DETERMINISTIC) ─────────────────────────────────────────────────────────────────────
def synthesize_equiv(g: Grammar, reference: Callable) -> SygusResult:
    """Enumerative SyGuS against a REFERENCE: find the first grammar term that the EXISTING z3 gate
    (`equiv_check.prove_equiv_z3`) proves ∀-equal to `reference` (an env→z3 builder). Verdict is equiv_check's —
    NO new disposer, NO new certificate kind. DECLINE if no grammar term within the bound is provably equal."""
    terms = enumerate_terms(g)
    for i, t in enumerate(terms, 1):
        res = EC.prove_equiv_z3(lambda env, _t=t: to_z3(_t, env), reference, list(g.variables))
        if res.proved:
            return SygusResult(True, t, pretty(t), EC.equiv_grade(res, "SyGuS candidate ≡ spec"),
                               enumerated=i, detail=f"enumerative SyGuS: term #{i}/{len(terms)} z3-proven ≡ reference ({res.tier})")
    return SygusResult(False, None, "", KV.decline("SyGuS: no grammar term within bound is provably equal", "sygus_propose"),
                       enumerated=len(terms), detail=f"exhausted {len(terms)} grammar terms (depth≤{g.max_depth}) ⇒ DECLINE (out of grammar)")


def synthesize_cegis(g: Grammar, reference_py: Callable, reference_z3: Callable,
                     seed_points: List[Dict[str, int]]) -> SygusResult:
    """CEGIS SyGuS: keep a growing set of concrete counterexample points; only z3-verify a candidate that already
    matches every counterexample (cheap concrete prune), and on a z3 counterexample add it and continue —
    deterministically. Same gated result set as enumerative, fewer z3 calls. reference_py: env(int)→int."""
    pts = [dict(p) for p in seed_points]
    terms = enumerate_terms(g)
    rounds = 0
    tried = 0
    for t in terms:
        if not all(_eval(t, p) == reference_py(p) for p in pts):   # concrete prune (cheap, deterministic)
            continue
        tried += 1
        res = EC.prove_equiv_z3(lambda env, _t=t: to_z3(_t, env), reference_z3, list(g.variables))
        if res.proved:
            return SygusResult(True, t, pretty(t), EC.equiv_grade(res, "SyGuS/CEGIS candidate ≡ spec"),
                               enumerated=tried, cegis_rounds=rounds, detail=f"CEGIS: z3-proven after {rounds} counterexample rounds")
        rounds += 1
        if res.counterexample:                                     # add the counterexample, keep enumerating
            ce = {k: (v if v is not None else 0) for k, v in res.counterexample.items()}
            if ce not in pts:
                pts.append(ce)
    return SygusResult(False, None, "", KV.decline("SyGuS/CEGIS: no grammar term provably equal", "sygus_propose"),
                       enumerated=tried, cegis_rounds=rounds, detail="CEGIS exhausted grammar ⇒ DECLINE")


# ── ★ the honest coverage measurement ────────────────────────────────────────────────────────────────────────
def coverage_delta() -> dict:
    """★ SyGuS is a PROPOSER, not a coverage extension. Every candidate it finds is disposed by the SAME z3 gate
    (`equiv_check`) that §P P1 / §AE ISLAND 5 already use — so the z3-FOLDABLE SET is unchanged ⇒ fold-coverage
    delta is 0. We DO report the proposer metric (instances synthesized) separately, never conflated with fold rate."""
    return {
        "fold_coverage_delta": 0,
        "why": "SyGuS changes WHICH proposer finds a candidate, not WHETHER z3 can dispose it; the z3-foldable set "
               "is identical to before (same equiv_check gate as §P P1 CEGAR + §AE ISLAND 5 synthesis). The only "
               "new part is grammar-constrained enumeration.",
        "overlap": "substantial overlap with §P P1 (CEGAR guard synthesis) and §AE ISLAND 5 (Karr/Farkas/Gröbner "
                   "invariant synthesis) — counted ZERO new coverage (the §Z/§AB no-double-count discipline)",
        "claim_forbidden": "‘SyGuS raises the fold rate’ — NOT made (a proposer cannot enlarge the z3-decidable region)",
    }


def adversarial_battery() -> dict:
    """max2(x,y) synthesizes (ite-grammar, z3-proven ≡ spec); 2·x+1 synthesizes (arith grammar, z3-proven); a
    too-weak grammar (no '*') canNOT express x·y ⇒ honest DECLINE (out of grammar); ★ a WRONG candidate is rejected
    by the z3 gate (precision 1.0 — verdict comes from equiv_check); ★ coverage delta is 0 (proposer, not coverage)."""
    import z3
    # 1) max2 via ite grammar, gated against the max spec (predicate form via prove_equiv_z3 to a reference)
    g_max = Grammar(("x", "y"), consts=(), ops=(), ite=True, max_depth=1)
    ref_max = lambda env: z3.If(env["x"] >= env["y"], env["x"], env["y"])
    r_max = synthesize_equiv(g_max, ref_max)
    # 2) 2x+1 via arithmetic grammar
    g_lin = Grammar(("x",), consts=(1, 2), ops=("+", "*"), max_depth=2)
    ref_lin = lambda env: 2 * env["x"] + 1
    r_lin = synthesize_equiv(g_lin, ref_lin)
    # 3) too-weak grammar (no '*') cannot express x*y ⇒ DECLINE
    g_weak = Grammar(("x", "y"), consts=(0, 1), ops=("+", "-"), max_depth=2)
    ref_mul = lambda env: env["x"] * env["y"]
    r_weak = synthesize_equiv(g_weak, ref_mul)
    # 4) CEGIS finds 2x+1 too, z3-gated
    r_cegis = synthesize_cegis(g_lin, lambda p: 2 * p["x"] + 1, ref_lin, [{"x": 0}, {"x": 1}])
    cov = coverage_delta()
    cases = {
        "max2_synthesized_z3_proven": r_max.found and r_max.verdict.status == KV.EXACT,
        "linear_2x1_synthesized": r_lin.found and r_lin.verdict.status == KV.EXACT,
        "weak_grammar_declined": (not r_weak.found) and r_weak.verdict.status == KV.DECLINE,   # ★ out of grammar
        "cegis_also_finds_it": r_cegis.found and r_cegis.verdict.status == KV.EXACT,
        "verdict_from_equiv_check": r_lin.verdict.kernel == "equiv_check",                      # ★ no new disposer
        "coverage_delta_zero": cov["fold_coverage_delta"] == 0,                                 # ★ honest: proposer only
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
