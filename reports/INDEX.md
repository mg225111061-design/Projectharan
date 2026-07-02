# reports/INDEX — what each `*_report.py` actually is (§BF FIX-5/6, navigability)

The doc-17 critique was right that the root `*_report.py` names are opaque (`aj` vs `ak` tells you nothing). This
index fixes that **without moving the files** — because a measured check shows they are NOT dead clutter:

> **All 15 root `*_report.py` (2,079 lines) are LIVE TEST FIXTURES** — `test_catalog.py` imports all 15, and
> `test_build.py` imports the 3 dogfood batteries (`dogfood`, `dogfood_v36`, `dogfood_v37`, which are *distinct
> version-pinned regression fixtures*, not stale copies). Physically moving/renaming them to `reports/archive/`
> would break 15+ imports and require the archive to be import-resolvable — that is a **refactor, not surgery**,
> and it would risk the verified gate (the §BF invariant is *zero regression*). So the move is **deferred**; this
> index delivers the navigability the critique wanted at zero risk. (Genuinely historical, non-fixture reports were
> already archived under `reports/archive/` back in §0.5/C2.)

## the 15 root report scripts (campaign § → meaning)
| script | campaign | what it measures / reports |
|---|---|---|
| `molecule_report.py` | §AI | grow the fold-rate NUMERATOR by recall only (denominator + 22/14 mechanisms fixed) |
| `aj_report.py` | §AJ | four auxiliary layers on §AI's conjecture-verify (precheck · router · soundness-aux · Viterbi) |
| `ak_report.py` | §AK | measure 2000 codes unfakeably; map what we can't fold and why (the honest fold-rate baseline) |
| `al_report.py` | §AL | recall to the physical limit (disguise-strip ×8, depth, multi-scale held-out), measured |
| `an_report.py` | §AN | close the measured k-regular gap (R=44) the same way it was found |
| `ao_report.py` | §AO | accelerate the non-foldable majority (verified), Axis-A/B kept separate |
| `ap_report.py` | §AP | 4-way cross-validated recall ×6, measured (S-3), precision held |
| `aq_report.py` | §AQ | math fragments in non-math code, dual-metric measured |
| `as_report.py` | §AS | adversarial hardening — external soundness criticisms treated as proposed bugs |
| `au_report.py` | §AU | second classical-simulation island (free-fermion / Gaussian) + hooks |
| `ay_report.py` | §AY | quantum linear-structure fold (12+1 recognition branches; 14/22 mechanism saturation unchanged) |
| `pc_report.py` | §AT | proof-carrying verification (Clock B fast-lane); measurement+routing track |
| `theory_audit_report.py` | §AG | 30-theory repo-first audit + the one net-new (SyGuS) |
| `upgrade_ah_report.py` | §AH | multilang intake · verified codegen · recall integration · self-fold · super-scaling |
| `mrjeffrey_gap_report.py` | FINISH-T4 | real-usage end-to-end test of MR.JEFFREY + the honest gap report |

Run any of them directly (`python3 <name>.py`) to reproduce its measurement; each is also asserted green by a
`test_catalog.py` fixture, so the numbers can't silently drift.

## dogfood (3 are intentional, not redundant — §BF FIX-5 honest finding)
`dogfood.py` / `dogfood_v36.py` / `dogfood_v37.py` are **three distinct version-pinned regression fixtures** (each
imported by a different `test_build.py` test: lines ~1308 / ~2778 / ~2925). They feed forced-wrong inputs to the
trusted cores and assert each REJECTS (no rubber-stamp). They are kept separate on purpose (a version-pinned
regression history); collapsing them would lose that history and break three tests — so they are **not** merged.

## e-graph: why 5 files (§BF FIX-6 — documented, consolidation deferred)
The e-graph appears in 5 places because they are **layered, not copies** (STATUS.md's standing claim, re-confirmed):
- `egraph.py` — the core e-graph / e-class union-find + rebuild.
- `egraph_native.py` — the std-only native lowering of the hot path (the §1 native-core layer).
- `fold_egraph.py` — the fold-engine *adapter* (canonicalize-before-fold lens), a different caller.
- `pillar3/egraph_simplify.py` — the CODE-mode equality-saturation *simplifier* (a pillar3 pass).
- `pillar3/superopt.py` — the superoptimizer that *uses* equality saturation (consumer, not a copy).
Each has a distinct caller/role; merging them is a refactor with real regression risk (they sit on the verified
CODE path), so per the §BF "low-risk only / no core-engine files" rule it is **documented here, not consolidated**.

## honest scope (§BF)
This is FIX-5/6 done as *navigability + honesty*, not a physical reorg: the report scripts are live fixtures (not
dead), so the truthful fix is to name what they are — which is what this file does — and to defer the import-breaking
move. The root still has 212 `.py` files; that flatness is real, but the specific "dead report clutter" the critique
inferred is mostly live measurement infrastructure.
