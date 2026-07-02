"""
§AP §6 — CHC ARRAY-DEPENDENCE REMOVAL: invariant_find → scalarize. An array loop whose update reads only fixed
================================================================================================================
negative offsets a[i−k] is a recurrence in disguise; the scalarizability invariant (§6.1, with a z3 inductive proof
for the affine case) licenses collapsing the O(n) array loop into the O(1)/O(log n) closed form (§6.2, disposed by the
existing z3-gated conjecturers). A loop that reads external data, or a non-fixed offset, is an honest DECLINE — it does
not fold to a closed form in n. No new mechanism, no new certificate kind.
"""
from __future__ import annotations

from recall.chc_strip import invariant_find as IF, scalarize as SC


def fold(src: str, entry: str = "f"):
    """invariant_find gates; scalarize disposes via the existing conjecturers."""
    info = IF.analyze(src)
    if not info.scalarizable:
        return SC.ScalarizeResult(False, "", "★ " + info.detail)
    return SC.scalarize(src, entry)


def adversarial_battery() -> dict:
    """★ a self-referential array loop a[i]=a[i−1]+i scalarizes and folds (triangular); ★ a Fibonacci array
    a[i]=a[i−1]+a[i−2] scalarizes (order 2) and folds; ★★ a DATA-dependent loop a[i]=a[i−1]+data[i] is an honest
    DECLINE (depends on input ⇒ no closed form in n); ★★ a GLOBAL-offset loop a[i]=a[i−1]+a[n−i] DECLINEs (not a
    single-index recurrence); ★★ the z3 CHC inductive invariant PROVES the triangular closed form and REFUTES a wrong
    one."""
    from fractions import Fraction
    tri = ("def f(n):\n a=[0]*(n+1)\n for i in range(1,n+1):\n  a[i]=a[i-1]+i\n return a[n]")
    fibarr = ("def f(n):\n a=[0,1]+[0]*(n+1)\n for i in range(2,n+1):\n  a[i]=a[i-1]+a[i-2]\n return a[n]")
    datadep = ("def f(n, data):\n a=[0]*(n+1)\n for i in range(1,n+1):\n  a[i]=a[i-1]+data[i]\n return a[n]")
    glob = ("def f(n):\n a=[1]*(n+1)\n for i in range(1,n+1):\n  a[i]=a[i-1]+a[n-i]\n return a[n]")

    rt = fold(tri)
    rf = fold(fibarr)
    rd = fold(datadep)
    rg = fold(glob)

    # ★ the z3 CHC inductive invariant: triangular g(i)=i/2 + i²/2 satisfies a[i]=a[i-1]+i ; a wrong g=i does not
    ind_ok = IF.verify_inductive_z3([Fraction(0), Fraction(1, 2), Fraction(1, 2)], 1, 1, 0)
    ind_wrong = not IF.verify_inductive_z3([Fraction(0), Fraction(1)], 1, 1, 0)        # g(i)=i is NOT inductive here

    cases = {
        "self_recurrence_scalarizes_and_folds": rt.folded,
        "fibonacci_array_scalarizes": rf.folded,
        "data_dependent_declines": not rd.folded,                # ★★ honest: input-dependent ⇒ no closed form in n
        "global_offset_declines": not rg.folded,                 # ★★ not a single-index recurrence
        "z3_inductive_invariant_proves": ind_ok,                 # ★★ the CHC core
        "z3_refutes_wrong_invariant": ind_wrong,                 # ★★ S-2: a wrong invariant is refuted
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
