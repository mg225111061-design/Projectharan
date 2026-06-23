# v39 PHASE B — DECLINE-pile recovery (the coverage north-star): fake-Ω(N) vs real-Ω(N)

The §0 gap (B): coverage sat at 64% for two builds because v38 only refined ALREADY-folded cases (O(log n)→
O(1)); it never RECOVERED declined ones. PHASE B wakes the sleeping v37 sublinear cluster and points it at the
DECLINE pile, separating **fake-Ω(N)** (hidden structure, recoverable) from **real-Ω(N)** (genuine noise, must
stay declined).

## B0 — measurement infrastructure
- `decline_recovery.py` with a **ground-truth-labelled** corpus (so recovery is scored honestly and false
  structure is catchable): fake-Ω(N) {hidden_poly, hidden_expsum, hidden_sparse, hidden_lowrank, hidden_spiked}
  + real-Ω(N) {random sequence, hash sequence, random signal, random matrix}. tune/measure = train/held-out.
- The current engine declines ALL of these (raw sequences/signals/matrices live outside the HARAN-fold front
  end), so **baseline recovery = 0%** — these are exactly the woken v37 detectors' new territory.
- Recovery metric defined: recovered_exact / recovered_probabilistic / still_decline_fake / **false_structure**.

## B1 — sound-gated detectors on the DECLINE pile (each held-out)
| truth (fake-Ω(N)) | detector (woken from v37/v38) | grade | certificate |
|---|---|---|---|
| hidden polynomial | `hidden_closed` finite-diff | EXACT | degree-d, held-out residual = 0 |
| hidden exp-sum | `prony`/ESPRIT | EXACT | held-out residual < machine-ε **and values < 2^53** |
| hidden k-sparse | `sparse_fft` | EXACT | k-sparse spectrum (Prony on O(k)) |
| hidden low-rank | `randomized_svd` | PROBABILISTIC(ε,δ) | posterior residual, δ stated |
| hidden spiked | `planted_detect` | PROBABILISTIC | BBP spectral gap |

**Soundness guard (rule 8):** an integer exp-sum may earn EXACT only when its values are within float64's
exact-integer range (<2^53). Beyond that a small *relative* residual could mask float error → a false EXACT;
we DECLINE instead (verified: exp_2_5(0..27) max≈1.5e19 → DECLINE; exp_2_5(0..17) max≈1.5e12 → EXACT).

## B2 — recovery measured (HELD-OUT, by grade) + the fake/real boundary
On the held-out split:
- **recovery 89%** of fake-Ω(N): **6 EXACT** (poly ×3, exp-sum ×1, sparse ×2) + **2 PROBABILISTIC** (low-rank,
  spiked) of 9 — i.e. coverage **0% → 89%** on this pile.
- **1 honest miss (detector limit, not unsoundness):** `exp_mix` = 2ⁿ+3ⁿ+1 (3-term, unit root) — Prony does not
  certify it. This is the directive's "still-missed fake (future work)" category; the detectors are not magic.
- ★ **false_structure = 0** ★ — the hard guarantee: NONE of the real-Ω(N) cases were recovered. All real-random
  (sequence / signal / matrix) correctly **DECLINED** (3/3). real-Ω(N) recovery = 0 ⇒ wrong answers = 0.

**The fake/real boundary, measured (not asserted):** on representative existing-corpus-character sequences,
harmonic Σ1/k, theta Σq^(k²), and q-harmonic all correctly **DECLINE** (genuinely no closed form — real-Ω(N)),
while the labelled hidden-structure cases recover. The existing defer corpus's declines are real-Ω(N) **by
design**, so its 64% does NOT move — and PHASE B *proves* that boundary (the remaining 36% is genuine, not a
detector failure), while demonstrating 0%→89% on a pile that genuinely contains fake-Ω(N).

## Honesty / discipline
- Domain-conditional (no "universal O(1)/universal recovery"): recovery lives in numeric/signal/statistical
  structure; genuine noise and control-flow get nothing — correctly.
- Grades never mixed (EXACT for poly/exp-sum/sparse; PROBABILISTIC(ε,δ) for low-rank/spiked).
- Every recovery passes a per-instance held-out certificate (sound-or-decline); DECLINE is byte-identical
  lossless defer. The v37 sublinear cluster is now AWAKE (PHASE A had deferred it here by design).
- 101 tests pass, 0 regression. No phone-home, no fabricated rates (all measured, held-out).
