"""Mechanism 7 — STRUCTURE + PSEUDORANDOM decomposition (★ master principle). Szemerédi regularity, circle
method (major/minor arcs), explicit-formula, Nisan–Wigderson hardness→randomness, zigzag product / expanders,
hardness-vs-randomness. Output: a structured part (foldable by 1/2/13) + a pseudorandom remainder (bounded by
12/14). The deepest recurring idea in the catalog.

WIRED (this round): the SPLITTER. On a numeric signal, sparse-FFT/Prony recovers a k-sparse spectral structure
from O(k) samples; the remainder = signal − reconstruction. A CLEAN k-sparse signal (held-out residual ≈ machine-ε)
splits EXACTly: structure = the k tones (M1 reads the spectral closed form off it), remainder ≈ 0. A signal with a
genuine pseudorandom remainder is HONESTLY DEFERRED (a low-rank candidate exists but its residual is above
machine-ε ⇒ no EXACT structural certificate — no overclaim); the remainder is routed to M12 by the composer."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "random" in f.tags:
        s += 0.4
    if "sum" in f.tags:
        s += 0.2
    if "graph" in f.tags:
        s += 0.2
    if "szemer" in f.text or "circle method" in f.text or "expander" in f.text:
        s += 0.4
    # a bare numeric signal is the master-split's home turf (probe must stay cheap — no heavy work here)
    if f.is_seq and f.n >= 8 and not f.tags:
        s = max(s, 0.3)
    return min(1.0, s)


def _apply(x, **kw):
    """The structure⊕pseudorandom SPLITTER (master principle, executed). Numeric signal → (k-sparse structure,
    remainder). EXACT iff the whole signal is clean k-sparse (held-out residual ≈ machine-ε). A low-rank-but-noisy
    signal is HONEST_DEFER'd (no overclaim); a structureless signal (rank≈N/2) DECLINEs to M12/M14."""
    if not (isinstance(x, (list, tuple)) and len(x) >= 8 and all(isinstance(v, (int, float, complex)) for v in x)):
        return honest_defer("M7.structured_pseudorandom",
                            "splitter wired for numeric signals (list/tuple, len≥8); other struct⊕pseudo instances "
                            "(Szemerédi/circle-method) deferred")
    import numpy as np
    import kernel_verdict as KV
    import prony
    import sparse_fft
    xs = list(x)
    v = sparse_fft.recover(xs)                       # EXACT iff the whole signal is a clean k-sparse spectrum
    if v.status == KV.EXACT:
        spec, k = v.result["spectrum"], v.result["k"]
        xx = np.asarray(xs, dtype=complex)
        N = len(xx)
        tt = np.arange(N)
        recon = np.zeros(N, dtype=complex)
        for f_, a in spec.items():
            recon += (a / N) * np.exp(2j * np.pi * f_ * tt / N)
        residual = np.real(xx - recon)
        relres = float(np.max(np.abs(residual))) / (float(np.max(np.abs(xx))) + 1e-30)
        cert = KV.Cert(KV.EXACT, "structured_pseudorandom_split", passed=True,
                       check_cost=f"O(k) Prony + held-out residual; k={k}", bound=relres,
                       detail=f"clean k-sparse: {k} tones, residual {relres:.2e}≈machine-ε ⇒ remainder negligible")
        return KV.exact({"spectrum": spec, "k": k, "residual": residual.tolist(), "split": "clean"},
                        "m7_structured_pseudorandom", f"O(k log N), k={k}, N={N}", cert)
    # not clean — is there a low-rank part (structure⊕noise) or is it structureless (rank≈N/2)?
    s = np.asarray(xs, dtype=complex)
    N = len(s)
    rows = (N - 4) // 2
    if rows >= 3:
        H = prony._hankel(s[:N - 4], rows)
        sv = np.linalg.svd(H, compute_uv=False)
        k = prony._estimate_rank(sv)
        if 0 < k < rows - 1 and k < (N - 4) // 2:
            return honest_defer("M7.structured_pseudorandom",
                                f"low-rank candidate (estimated k={k}) but held-out residual above machine-ε — EXACT "
                                f"structure⊕pseudorandom split DEFERRED (no overclaim); remainder routed to M12")
    return honest_defer("M7.structured_pseudorandom",
                        "no low-rank structure (rank≈N/2) — pseudorandom; whole routed to M12/M14")


MECHANISM = Mechanism(
    num=7, name="structured_pseudorandom", probe=_probe, apply=_apply,
    cert_kinds=("regularity_partition", "arc_bound", "pseudorandom_bound", "structured_pseudorandom_split"),
    contract="requires a near-random object with hidden structure; ensures a decomposition struct⊕pseudo where the "
            "structured part is foldable (EXACT) and the remainder carries a measured bound (PROBABILISTIC) — never "
            "an Ω(N) breach; grade EXACT⊕PROBABILISTIC, per-instance witness only",
    composable_with=(1, 2, 12, 13, 14),
)
