# PHASE S (v61) — extend-mode DEPTH: superopt + verified lifting, Z3-verified, the moat hardened

extend is the mode that always pays for the proof. PHASE S adds the deeper EXACT-or-DECLINE techniques — each a
real measured whole-program win carrying a machine-checked equivalence certificate (Z3 bounded translation
validation; no Lean/Coq/Isabelle).

## Delivered (`pillar3/superopt.py`)
- **verified lifting** (Tenspiler/Dexter spirit, restricted subset) — lift a hot reduction loop to its
  algebraic spec and re-synthesise the lower-cost equivalent: **Σ c·x_i ⇒ c·Σ x_i** (the distributive law). n
  multiplies become n adds + one multiply — a real win — **Z3-proven for all inputs at bounded size**. Measured
  **~6.5× EXACT**.
- **memoised DP** — an exponential self-recursion ⇒ a memoised/DP equivalent (EXACT by construction),
  O(2ⁿ)→O(n). Measured **~190,000× EXACT** on fib(28); a wrong base case → **DECLINE** (differential).
- **egg superoptimisation** — equality saturation over a hot expression, extract the lowest-cost equivalent
  ((x+x)+(x+x)+(x+x) ⇒ 6·x), **Z3-proven**. Measured **~2× EXACT**.

## The moat at depth
Three adversarial wrong swaps, each **Z3-REFUTED with a counterexample ⇒ DECLINE**:
- a transposed matmul `B[j][k]`,
- an off-by-one factoring `c·Σx + 1`,
- a wrong egg coefficient `5·x` vs `6·x`.

`grade_replacement` turns the Z3 refutation into a DECLINE — the bigger the change, the more the proof is worth,
and extend always pays for it.

## extend reaches what fast/normal cannot
`verified_lifting`, `egg_superopt`, and `algorithm_recognition` are **extend-only** (absent from
`FAST_DETECTORS` and `NORMAL_DETECTORS`), so the EXACT algorithmic wins here are reachable only in extend — the
mode-separation spine holds under the new depth.

## §0 self-check
measured whole-program (best-of-k); each carries hotspot fraction + ceiling; EXACT requires a proof (Z3) or a
by-construction identity (memoised DP) — never a δ; differential FIRST; a refuted swap → DECLINE, never shipped.

## Honest scope
The Z3 proofs are **bounded** translation validation (symbolic inputs at bounded sizes) — Alive2 in spirit,
not unbounded induction. Verified lifting is a **restricted subset** (integer reductions, no pointers/objects).
125+1 tests, 0 regression.
