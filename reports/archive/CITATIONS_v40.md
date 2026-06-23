# v40 §4.1 — citation verification (done BEFORE implementation; LLM citations hallucinate)

Per Constitution §0.3, the algorithm sources were re-verified against primary literature (WebSearch, June 2026)
before any kernel is implemented. ✓ = confirmed against a primary/authoritative source; flags noted.

| # | kernel | verified citation | note |
|---|---|---|---|
| 4 | Kovacic | **Jerald J. Kovacic**, "An algorithm for solving second order linear homogeneous differential equations", *J. Symbolic Computation* 2(1):3–43, **1986** | ✓ first name is **Jerald**, NOT "Robert" — the §0.3 flag was correct |
| 45 | Presburger QE | Haase, "A survival guide to Presburger arithmetic", *ACM SIGLOG News*, **2018** (survey); Haase, Krishna, Madnani, Mishra, Zetzsche, "An efficient quantifier elimination procedure for Presburger arithmetic", **ICALP 2024** (arXiv:2405.01183) | ✓ "Haase 2024" is the QE-procedure paper (real); survey is 2018 |
| 32 | Displacement Rank | Kailath, Kung, Morf, "Displacement ranks of matrices and linear equations", *J. Math. Anal. Appl.* 68:395–407, **1979** | ✓ exactly as cited |
| 7 | sparse FT | Hassanieh, Indyk, Katabi, Price, "Nearly optimal sparse Fourier transform", **STOC 2012**, pp.563–578 | ✓ exactly as cited |
| 50 | Tropical (min,+) | Imre Simon, "Recognizable sets with multiplicities in the tropical semiring", **MFCS 1988**, pp.107–120 | ✓ Simon; "tropical" named in his honour |

Additional sources confirmed from established literature for the PHASE-1 number-theory kernels actually built here:
- **Modular exponentiation** (square-and-multiply): Knuth, TAOCP Vol.2 §4.6.3 — standard, O(log b).
- **CRT** (Chinese Remainder, Garner's algorithm): Knuth TAOCP Vol.2 §4.3.2 — standard.
- **Continued fractions / best rational approximation**: Hardy & Wright, *An Introduction to the Theory of Numbers*, Ch.X; convergents are best approximations — standard.
- **Stern–Brocot / Farey**: Graham, Knuth, Patashnik, *Concrete Mathematics* §4.5 — standard.
- **Zeckendorf's theorem** (unique non-consecutive Fibonacci representation): Zeckendorf 1972 / Lekkerkerker 1952 — standard; greedy is O(log n).
- **PRNG counter-based random access**: Salmon, Moraes, Dror, Shaw, "Parallel random numbers: as easy as 1, 2, 3" (Philox/Threefry), **SC 2011** — counter-based ⇒ O(1) random access by construction.

★ Honesty: kernels whose primary source I could NOT confirm to first-source pseudocode in this cycle are NOT
implemented as EXACT/auto-selected; they will be tagged `@status("UNVERIFIED")` and excluded from the router
until their algorithm is confirmed (Constitution §0.1, §4.5). None of the PHASE-1 kernels below are in that bucket.
