"""
§AE — SEVEN HARD-BARRIER DECIDABLE ISLANDS: fold the decidable fragment inside each proven-hard barrier; DECLINE the rest.
================================================================================================================
The deepest directive. Seven barriers are PROVABLY hard in general — undecidable (Hilbert-10, Rice, Turing), intractable
(z3 IEEE-754 blow-up, Risch/Zeilberger non-termination), uncomputable (Kolmogorov). We do NOT claim to solve any in
general — that would be a lie. For each, we implement the DECIDABLE ISLAND inside it: a production-common fragment that
reduces to a z3-TERMINATING theory (QF_LRA / QF_NRA / QF_BV) and folds at precision 1.0 (or a universally-proven ε).
Outside each island we DECLINE — and that DECLINE is the proof that what remains is forbidden by Turing/Hilbert/Kolmogorov,
not by our laziness.

★ THE UNIFYING INSIGHT (governs all seven): synthesis is the PROPOSER's job (hard — FPTaylor/Gosper/Karr/Farkas/SCT/
Berlekamp-Massey); verification is z3's job (easy, under a TERMINATING theory — never IEEE-754 bit-blasting). This is why
the islands are tractable where the barriers are not.

  • ISLAND 1 float_eps        — real-abstraction + affine arithmetic + QF_NRA (avoid bit-blast) → APPROX_FOLD (universal ε)
  • ISLAND 2 nonlinear_int    — 5 decidable fragments of Hilbert-10 (classifier; modular/Möbius reused zero-new) → EXACT
  • ISLAND 3 exppoly_eq       — exp-poly equality by basis independence + Vereshchagin Skolem≤4 → EXACT
  • ISLAND 4 holonomic_sum    — Gosper/Zeilberger/Karr/C-finite terminating summation (the largest) → EXACT
  • ISLAND 5 invariant_synth  — Karr/Farkas/Gröbner COMPLETE synthesis (replaces §X CEGAR guessing) → EXACT
  • ISLAND 6 termination      — LRF/SCT/decreases decidable islands of the halting problem → EXACT  ★HALTING OATH
  • ISLAND 7 kolmogorov_enum  — enumerated decidable classes + MDL (registry = 22+gaps) → EXACT/DECLINE  ★KOLMOGOROV OATH

★ THE TWO HONESTY OATHS (binding): the halting problem (Turing) and K(x) (Kolmogorov) are PROVEN impossible in general —
we fold ONLY their decidable islands and DECLINE the rest. "Terminates because it has a ranking function," NEVER "this
loop terminates." "Best match among a finite enumerated list," NEVER "any structure." A build claiming a general solution
to Turing/Hilbert/Kolmogorov FAILS. ★ Repo-first / no-double-count: reuse interval.py, foldaxes APPROX_FOLD, Galois/§Z-Möbius,
the C-finite path, holonomic_sum, synthesize_guard, the 22+gaps registry — overlaps counted at ZERO new, surfaced not buried.
LLM-free; zero-dep (grandfathered sympy for symbolic steps); the 22-mechanism / certificate-kind taxonomy unchanged.
Never imported by test_build. Modules: float_eps · nonlinear_int · exppoly_eq · holonomic_sum · invariant_synth ·
termination · kolmogorov_enum · barrierfold_report.
"""
