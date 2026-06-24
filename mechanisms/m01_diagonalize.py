"""Mechanism 1 — DIAGONALIZE / spectral decomposition (eigen/SVD/PCA, simultaneous diagonalization, Hecke
eigenforms, free-probability R-transform, Wigner/representation decomposition). Ur-form of the diagonal lemma
(shared with M14). Output: eigen-structure + residual certificate."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "matrix" in f.tags:
        s += 0.6
    if "symmetry" in f.tags:
        s += 0.3
    if "recurrence" in f.tags:
        s += 0.2
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M1.diagonalize", "spectral apply lands in PHASE F (eigendecomp residual / companion replay cert)")


MECHANISM = Mechanism(
    num=1, name="diagonalize", probe=_probe, apply=_apply,
    cert_kinds=("eigendecomp_residual", "companion_replay", "sturm_bound"),
    contract="requires self-adjoint/normal operator or linear recurrence; ensures eigen-structure with "
            "residual ‖Ax−λx‖≤ε (EXACT interval) or companion≡naive (EXACT); grade EXACT",
    composable_with=(2, 9),
    ur_form="diagonal lemma (Cantor/Gödel/Turing self-reference) is the logical shadow of spectral self-maps",
)
