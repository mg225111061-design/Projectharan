"""
MATH-Ascent §3 (arsenal) — GEOMETRY: exact rational computational geometry (no float, so no epsilon-fudging).
=============================================================================================================
Every predicate is an EXACT sign of an integer/rational determinant — orientation, in-polygon, intersection —
so there is never a floating-point tie-break to get wrong. Each answer carries a SELF-CERTIFYING check:
  • polygon area (shoelace)   → cross-checked against an independent triangulation-fan sum (exact agreement).
  • convex hull (monotone)    → certified: EVERY input point is inside-or-on the hull (exact half-plane tests)
                                AND the hull is convex (all turns one orientation) — a wrong hull cannot pass.
  • segment intersection      → the returned rational point lies on BOTH segments (exact); parallel/disjoint ⇒
                                honest DECLINE (no fabricated crossing).
  • point-in-polygon          → two independent methods (ray cast + winding) must agree (exact).
Offload the casework from the LLM; the determinant signs are exact and re-checked. No float ever.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Sequence, Tuple

import kernel_verdict as KV

Pt = Tuple[Fraction, Fraction]


def _P(pts: Sequence[Sequence]) -> List[Pt]:
    return [(Fraction(x), Fraction(y)) for x, y in pts]


def _orient(o: Pt, a: Pt, b: Pt) -> int:
    """Exact orientation sign of (o→a, o→b): +1 CCW, −1 CW, 0 collinear."""
    v = (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    return (v > 0) - (v < 0)


def _on_segment(p: Pt, a: Pt, b: Pt) -> bool:
    """p lies on segment a–b (exact): collinear AND within the bounding box."""
    return (_orient(a, b, p) == 0 and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))


# ── polygon area (shoelace), certified by triangulation ──────────────────────────────────────────────────
def polygon_area_grade(pts) -> KV.Verdict:
    P = _P(pts)
    n = len(P)
    if n < 3:
        return KV.decline("polygon_area: need ≥ 3 vertices ⇒ DECLINE", "geometry.area")
    sh = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    area = abs(sh) / 2
    # independent cross-check: fan triangulation from P[0] (signed), must match the shoelace signed area
    fan = sum(_cross(P[0], P[i], P[i + 1]) for i in range(1, n - 1))
    if abs(fan) / 2 != area:
        return KV.decline("polygon_area: shoelace ≠ triangulation ⇒ DECLINE", "geometry.area")
    cert = KV.Cert(KV.EXACT, "shoelace_vs_triangulation", passed=True, check_cost="O(n) fan sum",
                   detail=f"area = {area} (shoelace ≡ fan triangulation, exact rationals)")
    return KV.exact(area, "geometry.area", "O(n) exact", cert)


def _cross(o: Pt, a: Pt, b: Pt) -> Fraction:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


# ── convex hull (Andrew's monotone chain), certified by containment + convexity ─────────────────────────
def convex_hull_grade(pts) -> KV.Verdict:
    P = sorted(set(_P(pts)))
    if len(P) < 3:
        return KV.decline("convex_hull: need ≥ 3 distinct points ⇒ DECLINE", "geometry.hull")
    lower: List[Pt] = []
    for p in P:
        while len(lower) >= 2 and _orient(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: List[Pt] = []
    for p in reversed(P):
        while len(upper) >= 2 and _orient(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    # ★ certificate (1): the hull is convex — every consecutive triple turns the same way (CCW, no reflex) ★
    h = len(hull)
    convex = all(_orient(hull[i], hull[(i + 1) % h], hull[(i + 2) % h]) >= 0 for i in range(h))
    # ★ certificate (2): EVERY input point is inside-or-on the hull (left-of-or-on every CCW edge) ★
    contains = all(all(_orient(hull[i], hull[(i + 1) % h], q) >= 0 for i in range(h)) for q in _P(pts))
    if not (convex and contains):
        return KV.decline("convex_hull: failed convexity/containment certificate ⇒ DECLINE", "geometry.hull")
    cert = KV.Cert(KV.EXACT, "hull_convex_and_contains", passed=True, check_cost="O(n·h) exact orientation",
                   detail=f"{h}-gon hull; convex (all CCW turns) ∧ contains all {len(_P(pts))} inputs (exact)")
    return KV.exact(hull, "geometry.hull", "O(n log n) exact", cert)


# ── segment intersection (exact rational point) ──────────────────────────────────────────────────────────
def segment_intersection_grade(p1, p2, p3, p4) -> KV.Verdict:
    a, b, c, d = (Fraction(p1[0]), Fraction(p1[1])), (Fraction(p2[0]), Fraction(p2[1])), \
                 (Fraction(p3[0]), Fraction(p3[1])), (Fraction(p4[0]), Fraction(p4[1]))
    denom = (b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])
    if denom == 0:
        return KV.decline("segment_intersection: parallel/collinear ⇒ no unique crossing ⇒ DECLINE",
                          "geometry.intersect")
    t = ((c[0] - a[0]) * (d[1] - c[1]) - (c[1] - a[1]) * (d[0] - c[0])) / denom
    px = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    if not (_on_segment(px, a, b) and _on_segment(px, c, d)):     # ★ point lies on BOTH segments (exact) ★
        return KV.decline("segment_intersection: lines cross outside the segments ⇒ DECLINE",
                          "geometry.intersect")
    cert = KV.Cert(KV.EXACT, "point_on_both_segments", passed=True, check_cost="O(1) exact collinearity+bbox",
                   detail=f"intersection {px} verified on both segments (exact)")
    return KV.exact(px, "geometry.intersect", "O(1) exact", cert)


# ── point in polygon (ray cast ⟂ winding, two methods agree) ─────────────────────────────────────────────
def point_in_polygon_grade(pt, poly) -> KV.Verdict:
    q = (Fraction(pt[0]), Fraction(pt[1]))
    P = _P(poly)
    n = len(P)
    if n < 3:
        return KV.decline("point_in_polygon: need ≥ 3 vertices ⇒ DECLINE", "geometry.pip")
    for i in range(n):                                            # on the boundary ⇒ exact "on"
        if _on_segment(q, P[i], P[(i + 1) % n]):
            cert = KV.Cert(KV.EXACT, "pip_boundary", passed=True, check_cost="O(n) exact",
                           detail="point lies on the polygon boundary (exact)")
            return KV.exact("boundary", "geometry.pip", "O(n) exact", cert)
    # ray cast (parity) — exact
    inside = False
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        if (a[1] > q[1]) != (b[1] > q[1]):
            xint = a[0] + (q[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if q[0] < xint:
                inside = not inside
    # winding number — exact, independent method
    wind = 0
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        if a[1] <= q[1] < b[1] and _orient(a, b, q) > 0:
            wind += 1
        elif b[1] <= q[1] < a[1] and _orient(a, b, q) < 0:
            wind -= 1
    if inside != (wind != 0):                                    # ★ two independent methods must agree ★
        return KV.decline("point_in_polygon: ray-cast ≠ winding ⇒ DECLINE", "geometry.pip")
    cert = KV.Cert(KV.EXACT, "pip_raycast_vs_winding", passed=True, check_cost="O(n) two methods",
                   detail=f"inside={inside} (ray-cast parity ≡ winding number, exact)")
    return KV.exact(inside, "geometry.pip", "O(n) exact", cert)


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    if op == "area":
        return polygon_area_grade(problem["pts"])
    if op == "hull":
        return convex_hull_grade(problem["pts"])
    if op == "intersect":
        return segment_intersection_grade(problem["p1"], problem["p2"], problem["p3"], problem["p4"])
    if op == "pip":
        return point_in_polygon_grade(problem["pt"], problem["poly"])
    return KV.decline(f"geometry: unknown op {op!r} ⇒ DECLINE", "geometry")
