"""
§AA WEAPON 1 — CANONICALIZATION (the multiplier; build first, measure before/after).
================================================================================================================
The same foldable structure gets written many ways — `x+a+b` vs `x+(a+b)`, `i*2` vs `2*i`, `(x+1)*(x-1)` vs `x*x-1` —
and a brittle pattern-matcher misses the variants. Normalizing code to a canonical form BEFORE fold makes every existing
lens and mechanism catch more AT ONCE — a MULTIPLIER on the whole engine's hit rate, where adding a lens lifts only one.

★ The proposer–disposer discipline: sympy PROPOSES a normal form (expand + AC-ordering); z3 DISPOSES — `prove_equiv_z3`
proves `∀ inputs. original == canonical`. A rewrite z3 cannot prove semantics-preserving is REJECTED (the original is
kept). A false rewrite FAILS the build.
★ THE FLOAT NON-ASSOCIATIVITY CAVEAT: floating-point addition is NOT associative ((a+b)+c ≠ a+(b+c) in IEEE-754), so
algebraic reassociation/distribution is sound ONLY for integer/rational (exact) operands. For float, the reassociation
is DECLINED (no rewrite) — proving it over ℝ would be UNSOUND for IEEE-754. Same caveat as the lenses.
★ Measured BEFORE/AFTER on the same corpus — the multiplier's real effect (how many more a brittle detector catches once
the form is normalized). LLM-free (deterministic rewriting + z3 proof). No new certificate kind (feeds existing folds).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CanonResult:
    original: str
    canonical: str
    proved: bool                            # z3-proved semantics-preserving (∀ inputs original == canonical)
    dtype: str = "integer"                  # "integer" | "rational" | "float"
    rule: str = ""
    detail: str = ""

    @property
    def rewritten(self) -> bool:
        return self.proved and self.canonical != self.original


def _sympy_to_z3(expr, env, sort: str):
    """Convert a sympy expression to a z3 expression using env = {name: z3 var}. Handles Add/Mul/Pow(int≥0)/Integer/
    Rational/Symbol — the closed arithmetic fragment canonicalization operates on. `sort` ∈ {Int, Real} picks literals."""
    import sympy as sp
    import z3
    num = z3.IntVal if sort == "Int" else z3.RealVal
    if expr.is_Integer:
        return num(int(expr))
    if expr.is_Rational:
        r = sp.Rational(expr)
        return z3.RealVal(int(r.p)) / z3.RealVal(int(r.q))            # rational ⇒ Real sort
    if expr.is_Symbol:
        return env[expr.name]
    if expr.is_Add:
        acc = _sympy_to_z3(expr.args[0], env, sort)
        for t in expr.args[1:]:
            acc = acc + _sympy_to_z3(t, env, sort)
        return acc
    if expr.is_Mul:
        acc = _sympy_to_z3(expr.args[0], env, sort)
        for t in expr.args[1:]:
            acc = acc * _sympy_to_z3(t, env, sort)
        return acc
    if expr.is_Pow and expr.exp.is_Integer and int(expr.exp) >= 0:
        base = _sympy_to_z3(expr.base, env, sort)
        out = num(1)
        for _ in range(int(expr.exp)):
            out = out * base
        return out
    raise ValueError(f"cannot encode {expr!r}")


def prove_semantics_preserving(orig, canon, var_names: List[str], dtype: str) -> bool:
    """z3 ∀ proof (via prove_equiv_z3) that the rewrite preserves semantics: ∀ vars. orig == canon. Int sort for
    integer, Real for rational. ★ Never called for float (reassociation is IEEE-754-unsound) — the caller declines float."""
    import catalog.equiv_check as EC
    sort = "Int" if dtype == "integer" else "Real"
    lhs = lambda env: _sympy_to_z3(orig, env, sort)
    rhs = lambda env: _sympy_to_z3(canon, env, sort)
    return EC.prove_equiv_z3(lhs, rhs, var_names, sort=sort).proved


def canonicalize_expr(expr_str: str, var_names: List[str], dtype: str = "integer") -> CanonResult:
    """Normalize an arithmetic expression to a canonical (expanded, AC-ordered) form, z3-proved equivalent. ★ float ⇒
    DECLINE the reassociation (IEEE-754 non-associative — no rewrite emitted). Unproved ⇒ keep the original."""
    if dtype == "float":
        return CanonResult(expr_str, expr_str, False, "float", "none",
                           "float arithmetic is non-associative (IEEE-754) ⇒ algebraic reassociation DECLINED (no rewrite); "
                           "only IEEE-754-proved-exact rewrites would be sound (out of scope here)")
    import sympy as sp
    syms = {n: sp.Symbol(n) for n in var_names}
    try:
        orig = sp.sympify(expr_str, locals=syms)
        canon = sp.expand(orig)                                  # the proposed normal form (distribute + AC-sort)
    except (sp.SympifyError, TypeError, SyntaxError) as e:
        return CanonResult(expr_str, expr_str, False, dtype, "none", f"parse error: {type(e).__name__}")
    proved = prove_semantics_preserving(orig, canon, var_names, dtype)
    if not proved:
        return CanonResult(expr_str, expr_str, False, dtype, "expand", "z3 could not prove equivalence ⇒ rewrite DECLINED")
    return CanonResult(expr_str, str(canon), True, dtype, "expand+AC-normal",
                       f"normalized to expanded AC-canonical form, z3 ∀-proved equivalent over {dtype} (EXACT)")


def _normalize_str(expr_str: str, var_names: List[str], dtype: str = "integer") -> str:
    """The canonical string a detector would see post-canonicalization (or the raw string if the rewrite is declined)."""
    r = canonicalize_expr(expr_str, var_names, dtype)
    return r.canonical if r.proved else expr_str


# ── the MULTIPLIER measurement: a brittle detector (knows only canonical spellings) + a corpus of variant spellings ──
def brittle_detect(expr_str: str, templates: set) -> bool:
    """A brittle pattern-matcher: it recognizes a foldable structure ONLY if the RAW string is one of its known canonical
    spellings. This models exactly why pattern-matching misses variants until the form is normalized."""
    return expr_str in templates


def multiplier_measurement() -> dict:
    """Run a brittle detector over a corpus of variant spellings WITHOUT and WITH canonicalization; the lift is the
    multiplier — every detector catches more once the form is normalized. ★ All rewrites z3-proved; a float variant is
    NOT rewritten (IEEE-754), so it stays a miss (the honest caveat, visible in the numbers)."""
    var_names = ["x", "i", "a", "b"]
    # foldable target structures, in canonical (expanded, sympy-str) form — what the brittle detector knows
    templates = {"2*i", "a + b + x", "x**2 - 1", "2*a + 2*b"}
    # corpus: each item is a variant spelling of one target (semantically equal), plus one float item (must NOT rewrite)
    corpus = [
        ("i*2", "integer"),            # → 2*i
        ("2*i", "integer"),            # already canonical
        ("i + i", "integer"),          # → 2*i
        ("x + a + b", "integer"),      # → a + b + x (AC-sorted) ; already-ish
        ("b + x + a", "integer"),      # → a + b + x
        ("(x+1)*(x-1)", "integer"),    # → x**2 - 1
        ("x*x - 1", "integer"),        # → x**2 - 1
        ("2*(a+b)", "integer"),        # → 2*a + 2*b
        ("i*2.0", "float"),            # ★ float ⇒ NOT rewritten ⇒ stays a miss (IEEE-754 honesty)
    ]
    hits_without = sum(1 for s, _ in corpus if brittle_detect(s, templates))
    hits_with = sum(1 for s, dt in corpus if brittle_detect(_normalize_str(s, var_names, dt), templates))
    n = len(corpus)
    return {
        "corpus_size": n,
        "hits_without_canon": hits_without,
        "hits_with_canon": hits_with,
        "rate_without": round(hits_without / n, 4),
        "rate_with": round(hits_with / n, 4),
        "multiplier": round(hits_with / hits_without, 3) if hits_without else None,
        "float_item_not_rewritten": _normalize_str("i*2.0", var_names, "float") == "i*2.0",  # honesty visible
    }


def adversarial_battery() -> dict:
    """A valid rewrite is z3-proved & applied; ★ an UNSOUND rewrite (claiming x+1 == x+2) is REJECTED by z3; ★ a float
    reassociation is DECLINED (not emitted as sound); the multiplier is real (with-canon > without-canon)."""
    import sympy as sp
    # (1) valid rewrite proved
    good = canonicalize_expr("i*2", ["i"], "integer")
    # (2) ★ unsound rewrite: force a wrong "canonical" and check z3 REJECTS it
    x = sp.Symbol("x")
    unsound_proved = prove_semantics_preserving(x + 1, x + 2, ["x"], "integer")
    # (3) ★ float reassociation declined
    flt = canonicalize_expr("a + b + x", ["a", "b", "x"], "float")
    # (4) the multiplier is real
    m = multiplier_measurement()
    cases = {
        "valid_rewrite_proved": good.proved and good.rewritten,
        "unsound_rewrite_rejected": not unsound_proved,
        "float_reassociation_declined": (not flt.proved) and "DECLINED" in flt.detail,
        "multiplier_real": m["hits_with_canon"] > m["hits_without_canon"],
        "float_item_not_rewritten": m["float_item_not_rewritten"],
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
