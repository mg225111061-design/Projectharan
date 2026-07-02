# NEWENGINE5_MEASURE — §BN measured (honest)

★ Every §BN engine clears the directive's discipline: an EXACT verdict is granted ONLY when an independently
re-checked certificate passes, and the cost of CHECKING the certificate is far below the cost of producing the
answer (the proposer-verifier asymmetry). The undecidable / not-known-poly residual DECLINEs — never a guess.

## End-to-end verdict time (decide + build certificate + re-check) — CPU, this build
| engine | input | time |
|---|---|---|
| hasse_minkowski (real obstruction) | x²+y²+z²=0 ⇒ unsolvable | 0.0013 ms |
| wl_refine (non-iso) | P₃ vs K₃ | 0.0044 ms |
| hasse_minkowski (explicit zero) | x²+y²−z²=0 ⇒ (0,1,1) | 0.0044 ms |
| morse_inequalities | S² perfect c=[1,0,1] | 0.0079 ms |
| tree_automata (membership) | even-g automaton on g(g(a)) | 0.0107 ms |
| parikh_image (achievable) | (ab)* with v={a:2,b:2} ⇒ "abab" | 0.0182 ms |
| smith_homology | ℝP² (Betti [1,0,0] ⊕ ℤ/2) | 0.0502 ms |
| alexander_poly | trefoil Δ=t²−t+1, det 3 | 0.1334 ms |

All ≪ 1 ms on the example inputs. (The order of magnitude is the point: re-checking a certificate — one
bottom-up run, one matrix identity, one substitution, one congruence — is far cheaper than the underlying
solve.) Larger inputs scale with the engine's stated complexity and DECLINE past the cost cap, never overclaim.

## Correctness (the false-EXACT-0 guarantee, measured by the batteries)
`newengine5.adversarial_battery()` ⇒ **7/7 engines all_ok**. Each battery includes a NEGATIVE control that must
DECLINE or refute:
- tree_automata: a disequality-constrained spec ⇒ DECLINE (undecidable guard); an automaton with no 0-ary seed ⇒
  EXACT empty.
- wl_refine: the WL-blind pair **C₆ vs 2·C₃** ⇒ DECLINE (never a false "isomorphic"); a relabeling ⇒ EXACT iso
  with the permutation re-checked against the edge sets.
- smith_homology: a **non-complex (∂∂≠0)** ⇒ DECLINE; ℝP² torsion ℤ/2 EXACT; S¹ Betti [1,1].
- morse_inequalities: too-few critical cells (weak inequality violated) ⇒ DECLINE.
- alexander_poly: the **identity matrix** (Δ(1)=0, not a knot Seifert matrix) ⇒ DECLINE; trefoil & figure-eight
  match the known Δ and knot determinants (3, 5).
- hasse_minkowski: positive-definite (real obstruction) and x²+y²=3z² (Legendre congruence) ⇒ EXACT unsolvable;
  over the coefficient cap ⇒ DECLINE.
- parikh_image: an **ε-transition** ⇒ DECLINE; unequal counts ⇒ EXACT not-achievable (exhaustive closed DP).

## Axis separation (never summed)
- **Axis A (execution removed / fold)**: smith_homology (Smith NF replaces enumerating cycles/boundaries),
  tree_automata emptiness (closed-form reachable fixpoint), parikh (bounded DP replaces word enumeration),
  hasse_minkowski (Legendre theorem replaces unbounded search).
- **Axis B (cheap verifier)**: wl_refine (a color histogram refutes iso in O((n+m)n)), morse_inequalities
  (verify proposed Morse data in O(#dims)), alexander_poly (Δ(1)=±1 + palindrome re-check), hasse_minkowski
  (substitute an explicit zero).
These are distinct ledgers; the §BN tranche spans both.

## Honesty (§4)
- certificate-or-DECLINE, false-EXACT 0: a construction bug ⇒ failed re-check ⇒ DECLINE.
- **decidable-fragment guards FIRST**: tree-automata disequality, general GI (WL-blind), #P-hard Jones (excluded),
  non-squarefree Hasse residual, ε-Parikh — all DECLINE, never a guessed verdict.
- 0 new mechanism, 0 new disposer (NEWENGINE5_INDEX classifies each as a branch of m03/m04/m05/m09/m10).
- reuse, re-build 0: native_lattice (Smith NF), mech_knot (Laurent/Kauffman, amplified by Alexander),
  mech_persistence/mech_sheaf (amplified by smith_homology+morse), presburger_qe (semilinear backing).
- the full-repo inventory stays **gap == 0** after adding `newengine5` to `_WIRED_PACKAGES`.
- zero-dep (z3 + stdlib + numpy); class groups / modular forms / large-rank LLL excluded.
- ★ Sandbox blocks the live server ⇒ end-to-end production use is author-validated on Render; the engines + their
  certificates are unit-tested here (test_bn) — code + push only, no false "verified".
