"""Two CROSS-CUTTING PRIMITIVES (§3.1) shared by many mechanisms (not peers of the 14):
  P-L  Legendre / convex duality — pairs M4 (dualize), M5/M6 (mechanics/RG), large-deviations rate functions.
  P-S  symmetry reduction      — pairs M1 (representation), M2 (canonicalization), M9 (Buckingham Π, GCT orbits).
These are TECHNIQUES the mechanisms invoke, registered with num 0 (Legendre) and -1 (symmetry)."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe_legendre(x):
    f = feats(x)
    s = 0.0
    if "optimization" in f.tags or "physics" in f.tags:
        s += 0.3
    if "legendre" in f.text or "convex" in f.text or "large deviation" in f.text or "rate function" in f.text:
        s += 0.4
    return min(1.0, s)


def _probe_symmetry(x):
    f = feats(x)
    s = 0.0
    if "symmetry" in f.tags:
        s += 0.4
    if "buckingham" in f.text or "dimensional" in f.text or "orbit" in f.text:
        s += 0.3
    return min(1.0, s)


LEGENDRE = Mechanism(
    num=0, name="legendre_dual", probe=_probe_legendre,
    apply=lambda x, **kw: honest_defer("P.legendre", "convex/Legendre duality primitive — invoked by M4/M5/M6 in PHASE F"),
    cert_kinds=("convex_conjugate", "biconjugate_identity"),
    contract="requires a convex potential / cumulant; ensures the Legendre dual with f**=f on the convex hull; "
            "grade EXACT; a PRIMITIVE (not one of the 14)",
)

SYMMETRY = Mechanism(
    num=-1, name="symmetry_reduce", probe=_probe_symmetry,
    apply=lambda x, **kw: honest_defer("P.symmetry", "symmetry/representation reduction primitive — invoked by M1/M2/M9 in PHASE F"),
    cert_kinds=("orbit_normal_form", "invariant_ring"),
    contract="requires a group action; ensures a reduction to orbit representatives / invariant coordinates, "
            "machine-checked; grade EXACT; a PRIMITIVE (not one of the 14)",
)

PRIMITIVES = {LEGENDRE.name: LEGENDRE, SYMMETRY.name: SYMMETRY}
