# NEWENGINE_MEASURE — §BM measured (honest)

★ The directive's hard gate: a verifier that cannot produce its certificate in **< 1 ms** must DECLINE. Every
delivered engine clears it by ~20–50× — the certificate is a single matrix/residual/sift check, not a re-solve.

## Certificate-verification time (the Axis-B win: cheap to CHECK)
| engine | certificate checked | time |
|---|---|---|
| farkas | y≥0 ∧ Aᵀy=0 ∧ bᵀy<0 (one matvec) | 0.013 ms |
| kasteleyn | Pf(K)² = det(K) | 0.022 ms |
| schreier_sims | every generator sifts to identity (|S₄| order) | 0.045 ms |
| markov_exact | πP = π re-check | 0.049 ms |

All **≪ 1 ms** ⇒ none has to DECLINE on the time gate. (CPU numbers on this build; the point is the order of
magnitude — checking a certificate is far cheaper than producing the answer, the proposer-verifier asymmetry.)

## Correctness (the false-EXACT-0 guarantee, measured by the batteries)
`newengine.adversarial_battery()` ⇒ **10/10 engines all_ok**. Each battery includes a NEGATIVE control that must
DECLINE (a bad Farkas y, a reachable Petri marking, a non-group for Burnside, a wrong Riccati P, a non-planar /
non-antisymmetric Kasteleyn input, a suboptimal LP pair) — confirming the certificate gate actually rejects, so an
EXACT is never granted without a passing re-checked certificate.

## Axis separation (never summed)
- **Axis A (execution removed / fold)**: schreier_sims order ∏|orbitᵢ|, markov stationary, kalman matrix-exp,
  burnside orbits, kasteleyn Pfaffian — a closed form replaces enumeration.
- **Axis B (cheap verifier)**: farkas, petri_invariant, resultant, thermo, riccati, schreier_sims membership —
  verify a proposed answer in O(check) ≪ O(solve).
These are distinct ledgers; the §BM tranche is dominated by Axis B (the under-mined axis the research flagged).

## Honesty (§4)
- certificate-or-DECLINE, false-EXACT 0: a construction bug ⇒ failed re-check ⇒ DECLINE, never a faked EXACT.
- 0 new mechanism, 0 new disposer (NEWENGINE_INDEX classifies each as a branch of m02/m03/m04/m05/m09/m10).
- decidable-only: Petri general reachability (Ackermann-hard) and submodular maximization (NP-hard) are NOT
  attempted; numeric-alone Riccati is forbidden (exact-ℚ residual required).
- preconditions verified first (Kasteleyn planarity + antisymmetry, Legendre convexity, exact-ℚ Riccati).
- NEW-6/7/8/13/15 deferred to the next tranche with their mechanism branch + reason (NEWENGINE_INDEX) — honest
  scope, not a silent gap.
- ★ Sandbox blocks the live server ⇒ end-to-end production use is author-validated on Render; the engines + their
  certificates are unit-tested here — code + push only, no false "verified".
