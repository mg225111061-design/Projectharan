# v40 PHASE 1 — router skeleton + grade ADT + number-theory/PRNG core

Branch `claude/funny-maxwell-im9x07`, on top of v39. First cycle of the v40→v47 campaign. Citations verified
first (CITATIONS_v40.md). All claims measured (Constitution §0.1).

## Delivered
- **§4.1 citation verification** — 5 flagged citations re-checked against primary sources: Kovacic = **Jerald**
  (1986, not "Robert"); Haase Presburger QE = **2024 ICALP** (survey 2018); Displacement = Kailath-Kung-Morf
  1979; sparse FT = Hassanieh-Indyk-Katabi-Price STOC 2012; tropical = Simon MFCS 1988. All confirmed.
- **1B grade ADT** (`kernel_verdict.py`) — EXACT / PROBABILISTIC(ε,δ) / DECLINE, ENFORCED at construction:
  non-DECLINE ⇒ passed cert; grade==cert.grade; PROBABILISTIC ⇒ δ stated; **EXACT cannot carry a probabilistic
  δ**. Rule-of-three: a sampling count earns δ=3/n and DECLINEs if the caller needs tighter (§0.2).
- **1A router** (`kernel_router.py`) — cheap (µs) classification → first applicable VERIFIED kernel; else
  honest DECLINE/fallback. Each kernel carries a HARAN contract (requires/ensures+grade); `verify_contracts()`
  dogfoods well-formedness; UNVERIFIED kernels are never auto-selected.
- **1C/1D kernels** (`kernels_numtheory.py`), all EXACT (integer/bit-exact), each with the 5 obligations:
  modexp(19), CRT/Garner(11), Zeckendorf(18), best-rational/continued-fractions(15), PRNG counter-replay(29).

## Measured (§0.1) — crossovers are REAL, not theoretical
| kernel | what collapses (§0.1) | measured | grade |
|---|---|---|---|
| modexp | **compute** O(b)→O(log b) | b=4096: naive 489µs → 2.0µs (crossover b=16) | EXACT |
| best_rational | **compute** O(D)→O(log q) | D=10⁴: search 2168µs → CF 24µs; finds π=355/113 | EXACT |
| prng_seed | **random-access** O(k)→O(1) | k=10⁶: sequential **651ms → 2µs, bit-exact** (crossover k=100) | EXACT |
| zeckendorf | **repr-size + compute** O(log n) | crossover n=10⁵ vs O(n) table (point op, low Amdahl — honest) | EXACT |
| crt | **modular decomposition** | reconstruct+verify 20–54µs for k=3..15 residues | EXACT |
- router decision latency: **2–34 µs** per dispatch.

## §0.1 honesty self-check (mandatory)
1. **O(1)/O(log N) = cost or output-size?** Labelled per kernel: modexp/best_rational = COMPUTE collapse;
   prng = RANDOM-ACCESS collapse; zeckendorf = REPR-SIZE+compute (stated as a representation kernel, not a
   value collapse); crt = modular decomposition. Never conflated.
2. **Which domain?** Pure numeric / number-theory (exact integer & rational). No claim about general code.
3. **Crossover measured or theoretical?** MEASURED (tables above), on this container, with N.
4. **Grade enforced or labelled?** ENFORCED — the ADT raises on a fake pass or an EXACT-carrying-δ; tested.
5. **Amdahl p?** Reported per kernel: prng/crt high p when stream-regen / big-int modular ops dominate;
   modexp depends on caller; zeckendorf/best_rational low p (point ops) — collapsing them barely moves an
   end-to-end wall-clock unless they dominate. Stated honestly, not hidden.

## Regression
102 (v39) + 1 new (test_v40_phase1_router_and_kernels) = **103 tests, measured 0 regression** (full suite
re-run, not "by construction"). No phone-home; kernels are pure/in-memory; keys untouched; PQC 0.

## Scope honesty
This is **cycle 1 of a 9-phase campaign**. PHASE 1 lays the spine (router + grade ADT) and the EXACT
number-theory core. The existing v37–v39 kernels (Freivalds, SZ, ABFT, sparse_fft, prony, cfinite, kovacic,
benortiwari, q_fold, decline_recovery, …) already cover much of groups A/B/D/G/H and will be **registered into
this router** in subsequent cycles rather than rebuilt. Later phases (structured matrices, succinct structures,
the hard "other-rules" classes, the verifier suite, and the MR.JEFFREY site) are not yet built — they will be
delivered cycle-by-cycle with the same measured discipline, never stubbed or faked.
