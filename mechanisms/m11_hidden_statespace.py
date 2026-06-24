"""Mechanism 11 — HIDDEN STATE-SPACE recovery (neural manifold LFADS/CEBRA, Johansen cointegration, EnKF data
assimilation, tipping-point early-warning via critical slowing-down, grid-cell representation geometry). Output:
a low-dimensional latent state + estimation covariance. PROBABILISTIC by nature (estimation, not proof)."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "timeseries" in f.tags:
        s += 0.6
    if "matrix" in f.tags:
        s += 0.2
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M11.hidden_statespace", "latent state-space applies land in PHASE F (PROBABILISTIC ε,δ; statsmodels/EnKF)")


MECHANISM = Mechanism(
    num=11, name="hidden_statespace", probe=_probe, apply=_apply,
    cert_kinds=("latent_residual", "cointegration_rank", "covariance_estimate"),
    contract="requires a high-dim observation sequence with a low-dim latent dynamics; ensures a state estimate + "
            "covariance; grade PROBABILISTIC(ε,δ) — never EXACT (estimation)",
    composable_with=(1, 9),
)
