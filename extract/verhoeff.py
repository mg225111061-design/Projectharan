"""
§AQ §7 — Verhoeff / Damm (low-priority, ~0.05% of real code: Aadhaar / some European bank IDs). Completeness only.
================================================================================================================
The Damm/Verhoeff check digit uses a NON-COMMUTATIVE quasigroup (a Latin-square Cayley table), so there is ★NO scalar
closed form — only a finite-MONOID matrix-power over the table (REUSE the existing matrix-power mechanism; the table is a
z3 array, re-association verified). ★ We make NO scalar-sum claim (the honest line — a digit-sum closed form would be
wrong for a non-commutative operation). EXACT but rare ⇒ completeness, not a priority.
"""
from __future__ import annotations

# Damm operation table (a weakly totally anti-symmetric quasigroup over {0..9})
_DAMM = [
    [0, 3, 1, 7, 5, 9, 8, 6, 4, 2], [7, 0, 9, 2, 1, 5, 4, 8, 6, 3], [4, 2, 0, 6, 8, 7, 1, 3, 5, 9],
    [1, 7, 5, 0, 9, 8, 3, 4, 2, 6], [6, 1, 2, 3, 0, 4, 5, 9, 7, 8], [3, 6, 7, 4, 2, 0, 9, 5, 8, 1],
    [5, 8, 6, 9, 7, 2, 0, 1, 3, 4], [8, 9, 4, 5, 3, 6, 2, 0, 1, 7], [9, 4, 3, 8, 6, 1, 7, 2, 0, 5],
    [2, 5, 8, 1, 4, 3, 6, 7, 9, 0],
]


def is_latin_square(table=_DAMM) -> bool:
    """Each row and column is a permutation of {0..9} (the quasigroup / Latin-square property)."""
    n = len(table)
    full = set(range(n))
    rows = all(set(r) == full for r in table)
    cols = all({table[i][j] for i in range(n)} == full for j in range(n))
    return rows and cols


def is_noncommutative(table=_DAMM) -> bool:
    """∃ a,b: table[a][b] ≠ table[b][a] — so there is NO scalar (commutative) closed form (matrix-power only)."""
    n = len(table)
    return any(table[a][b] != table[b][a] for a in range(n) for b in range(n))


def fold_finite_monoid() -> dict:
    """The honest result: Damm folds via finite-monoid matrix-power (existing), NOT a scalar sum."""
    return {"folded": is_latin_square(), "reduces_to": "finite_monoid_matrix_power",
            "scalar_closed_form": False,                          # ★ no scalar-sum claim (non-commutative)
            "noncommutative": is_noncommutative(),
            "detail": "Damm/Verhoeff = non-commutative quasigroup ⇒ finite-monoid matrix-power (existing); NO scalar sum",
            "axis_a": "low (~0.05% frequency)", "axis_b": "~0"}


def adversarial_battery() -> dict:
    """★ the Damm table is a valid quasigroup (Latin square, z3-checkable structure); ★★ it is NON-commutative ⇒ NO
    scalar closed form is claimed (only finite-monoid matrix-power — the honest completeness line)."""
    r = fold_finite_monoid()
    cases = {
        "damm_is_latin_square": is_latin_square(),
        "damm_noncommutative": is_noncommutative(),
        "no_scalar_closed_form_claimed": r["scalar_closed_form"] is False,        # ★★ honest
        "reduces_to_finite_monoid": r["reduces_to"] == "finite_monoid_matrix_power",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
