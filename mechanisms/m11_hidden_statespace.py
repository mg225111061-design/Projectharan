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
    """M11 hidden state-space recovery. WIRED (this round): Prony/ESPRIT recovers the hidden linear-recurrence
    state space of a numeric signal — f(t)=Σ cⱼ βⱼᵗ, the βⱼ are the eigenvalues of the hidden state transition. A
    CLEAN exponential-sum signal is EXACTLY DETERMINED from O(k) samples (held-out residual ≈ machine-ε ⇒ EXACT —
    this is exact algebraic recovery, not statistical estimation). Noisy / non-exponential ⇒ honest DECLINE.
    Other latent instances (LFADS/EnKF/cointegration, genuinely PROBABILISTIC) remain deferred."""
    if isinstance(x, dict) and "koopman" in x:                       # heavy bypass call site: Koopman linear embedding
        from catalog import heavy_bypasses
        return heavy_bypasses.try_bypass("koopman", x)
    if isinstance(x, dict) and "recurrence_seq" in x:                # native Berlekamp–Massey minimal linear recurrence
        import native_sequence
        return native_sequence.bm_grade(x["recurrence_seq"])
    if isinstance(x, dict) and ("lcg" in x or "lfsr" in x):          # native weak-PRNG state recovery (secure → DECLINE)
        import native_prng
        return native_prng.prng_grade(x)
    if not (isinstance(x, (list, tuple)) and len(x) >= 6 and all(isinstance(v, (int, float, complex)) for v in x)):
        return honest_defer("M11.hidden_statespace",
                            "Prony state-space wired for numeric signals (len≥6); LFADS/EnKF/cointegration latent "
                            "estimation (PROBABILISTIC ε,δ) deferred (statsmodels/EnKF bridge)")
    import kernel_verdict as KV
    import prony
    v = prony.recover(list(x))
    if v.status != KV.EXACT:
        return KV.decline(f"M11.prony: {v.reason} (not an exactly-determined exponential sum ⇒ honest DECLINE)", "m11_prony")
    betas, coeffs, k = v.result["betas"], v.result["coeffs"], v.result["k"]
    coeffs_rec, cfinite_ok, rec_detail = prony.recover_recurrence(list(x))
    c = v.certificate
    cert = KV.Cert(KV.EXACT, "latent_residual", passed=True, check_cost=c.check_cost,
                   bound=c.bound, detail=f"hidden state space recovered: k={k} modes (eigenvalues βⱼ of the hidden "
                                         f"transition); {rec_detail}; held-out residual {c.bound:.2e} ≈ machine-ε ⇒ determined")
    return KV.exact({"k": k, "modes": [complex(b) for b in betas], "amplitudes": [complex(a) for a in coeffs],
                     "recurrence": coeffs_rec, "cfinite_agrees": cfinite_ok}, "m11_prony",
                    v.complexity, cert)


MECHANISM = Mechanism(
    num=11, name="hidden_statespace", probe=_probe, apply=_apply,
    cert_kinds=("latent_residual", "cointegration_rank", "covariance_estimate"),
    contract="requires an observation sequence with a low-dim latent dynamics; ensures the hidden state space; "
            "grade EXACT (Prony, when the exponential-sum recurrence is determined: held-out residual ≈ machine-ε) "
            "or PROBABILISTIC(ε,δ) for noisy estimation; non-determined ⇒ DECLINE",
    composable_with=(1, 9),
)
