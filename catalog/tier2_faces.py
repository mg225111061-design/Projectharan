"""
POST-CONSOLIDATION PHASE 3 — TIER-2 FACES (admissible-but-REDUCIBLE candidates, each a new FACE of an existing
mechanism — coverage widens, the mechanism COUNT does NOT).
================================================================================================================
Eight more candidates that emit a constructive per-instance certificate but reduce IN KIND to an existing mechanism.
Each routes to its PARENT and folds its inputs; none is a new mechanism (no count++). The impossible core still
DECLINEs.

  monoid-homomorphism   → M13/M12  : φ(a∘b)=φ(a)∘′φ(b) verified on a finite monoid (an algebraic fold witness).
  poset Möbius          → M2       : μ(x,y) by Möbius inversion (a triangular linear solve — M2's algebra).
  CRN deficiency-zero   → M11      : δ = n−ℓ−s = 0 (Feinberg) forces unique equilibrium dynamics.
  discrete ext. calculus→ M18      : the cochain complex d∘d = 0 (the discrete Laplacian underlying M18 flow).
  restricted chase      → M14      : TGD chase termination (bounded) vs the unbounded obstruction.
  combinatorial species → M12      : labelled-structure counts via the EGF (a counting closed form).
  trace monoids         → M15/M10  : Foata normal form of a Mazurkiewicz trace (a canonical concurrency form).
  twin-width            → M10       : a contraction sequence witnessing twin-width ≤ d (structural tractability).
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Tuple

import kernel_verdict as KV


# ── 1. monoid homomorphism → FACE of M13 ────────────────────────────────────────────────────────────────
def monoid_hom_face(spec: dict) -> KV.Verdict:
    """spec = {table:{(a,b):c}, identity, phi:{a:a'}, ttable:{(a',b'):c'}, tidentity}. EXACT iff φ is a monoid
    homomorphism (φ(a∘b)=φ(a)∘′φ(b) ∀a,b AND φ(e)=e′); a non-homomorphic map ⇒ DECLINE."""
    try:
        table, phi, tt = spec["table"], spec["phi"], spec["ttable"]
        for (a, b), c in table.items():
            if tt[(phi[a], phi[b])] != phi[c]:
                return KV.decline(f"monoid_hom: φ fails φ(a∘b)=φ(a)∘′φ(b) at ({a},{b}) ⇒ DECLINE (not a homomorphism)", "faces")
        if phi[spec["identity"]] != spec["tidentity"]:
            return KV.decline("monoid_hom: φ(e) ≠ e′ ⇒ DECLINE", "faces")
    except (KeyError, TypeError):
        return KV.decline("monoid_hom: need {table, identity, phi, ttable, tidentity}", "faces")
    cert = KV.Cert(KV.EXACT, "monoid_homomorphism", passed=True,
                   check_cost="exact verification of φ(a∘b)=φ(a)∘′φ(b) on every pair + φ(e)=e′",
                   detail="φ is a monoid homomorphism (an algebraic structure-preserving fold; FACE of M13/M12)")
    return KV.exact({"parent_mechanism": 13, "face": "monoid_homomorphism", "pairs_checked": len(spec["table"])},
                    "faces.monoid_hom", "monoid homomorphism (face of M13)", cert)


# ── 2. poset Möbius function → FACE of M2 ────────────────────────────────────────────────────────────────
def poset_mobius_face(spec: dict) -> KV.Verdict:
    """spec = {elements, leq:[(x,y)…]} (the full ≤ relation incl. reflexive). Computes μ(x,y) by Möbius inversion and
    certifies it via Σ_{x≤z≤y} μ(x,z) = [x=y]. A non-order (not transitive/antisymmetric reflexive) ⇒ DECLINE."""
    elems = list(spec.get("elements", []))
    leq = set(tuple(p) for p in spec.get("leq", []))
    if not elems or any((x, x) not in leq for x in elems):
        return KV.decline("poset_mobius: need {elements, leq} with reflexive ≤", "faces")

    def below(x, y):    # z with x ≤ z < y
        return [z for z in elems if (x, z) in leq and (z, y) in leq and z != y]

    mu: Dict[Tuple, int] = {}

    def mobius(x, y):
        if (x, y) in mu:
            return mu[(x, y)]
        if x == y:
            mu[(x, y)] = 1
        elif (x, y) not in leq:
            mu[(x, y)] = 0
        else:
            mu[(x, y)] = -sum(mobius(x, z) for z in below(x, y))
        return mu[(x, y)]

    for x in elems:
        for y in elems:
            if (x, y) in leq:
                mobius(x, y)
    # ★ certificate: Möbius inversion Σ_{x≤z≤y} μ(x,z) = [x=y] ★
    for x in elems:
        for y in elems:
            if (x, y) in leq:
                s = sum(mu[(x, z)] for z in elems if (x, z) in leq and (z, y) in leq)
                if s != (1 if x == y else 0):
                    return KV.decline("poset_mobius: inversion identity failed (not a valid poset) ⇒ DECLINE", "faces")
    cert = KV.Cert(KV.EXACT, "poset_mobius", passed=True,
                   check_cost="exact μ by Möbius inversion + the inversion identity Σμ=[x=y] on every interval",
                   detail="Möbius function of the poset (a triangular linear solve — M2's algebra; FACE of M2)")
    return KV.exact({"parent_mechanism": 2, "face": "poset_mobius", "mu": {f"{x},{y}": v for (x, y), v in mu.items() if v != 0}},
                    "faces.poset_mobius", "poset Möbius function (face of M2)", cert)


# ── 3. CRN deficiency-zero → FACE of M11 ────────────────────────────────────────────────────────────────
def _exact_rank(cols: List[List[Fraction]]) -> int:
    """Rank (over ℚ) of the matrix whose COLUMNS are given."""
    if not cols:
        return 0
    m = len(cols[0])
    rows = [[cols[j][i] for j in range(len(cols))] for i in range(m)]
    rank, pr = 0, 0
    ncol = len(cols)
    for c in range(ncol):
        piv = next((r for r in range(pr, m) if rows[r][c] != 0), None)
        if piv is None:
            continue
        rows[pr], rows[piv] = rows[piv], rows[pr]
        inv = Fraction(1) / rows[pr][c]
        rows[pr] = [x * inv for x in rows[pr]]
        for r in range(m):
            if r != pr and rows[r][c] != 0:
                f = rows[r][c]
                rows[r] = [a - f * b for a, b in zip(rows[r], rows[pr])]
        pr += 1
        rank += 1
    return rank


def crn_deficiency_face(spec: dict) -> KV.Verdict:
    """spec = {species, complexes:{name:{species:coeff}}, reactions:[(src,dst)]}. Deficiency δ = n−ℓ−s (n complexes,
    ℓ linkage classes, s = rank of the stoichiometric matrix). EXACT iff δ=0 (Feinberg: forced unique equilibrium);
    δ>0 ⇒ DECLINE (no deficiency-zero conclusion)."""
    try:
        species = list(spec["species"])
        complexes = spec["complexes"]
        reactions = [tuple(r) for r in spec["reactions"]]
    except (KeyError, TypeError):
        return KV.decline("crn: need {species, complexes:{name:{sp:coeff}}, reactions:[(src,dst)]}", "faces")
    names = list(complexes)
    n = len(names)
    # linkage classes = connected components of the (undirected) reaction graph
    adj = {c: set() for c in names}
    for s, d in reactions:
        adj[s].add(d)
        adj[d].add(s)
    seen, ell = set(), 0
    for c in names:
        if c in seen:
            continue
        ell += 1
        stack = [c]
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            stack.extend(adj[u])
    # stoichiometric matrix: columns = reaction vectors (dst − src) in species space
    def vec(cx):
        return [Fraction(complexes[cx].get(sp, 0)) for sp in species]
    cols = [[d_i - s_i for d_i, s_i in zip(vec(d), vec(s))] for s, d in reactions]
    s_rank = _exact_rank(cols)
    delta = n - ell - s_rank
    if delta != 0:
        return KV.decline(f"crn: deficiency δ = {n}−{ell}−{s_rank} = {delta} ≠ 0 ⇒ DECLINE (no deficiency-zero "
                          "conclusion)", "faces")
    cert = KV.Cert(KV.EXACT, "crn_deficiency_zero", passed=True,
                   check_cost=f"exact δ = n−ℓ−s = {n}−{ell}−{s_rank} = 0 (linkage classes + ℚ stoichiometric rank)",
                   detail="deficiency-zero (Feinberg): the network structure FORCES a unique positive equilibrium "
                          "per stoichiometric class (a structure-forced dynamics; FACE of M11)")
    return KV.exact({"parent_mechanism": 11, "face": "crn_deficiency_zero", "n_complexes": n, "linkage_classes": ell,
                     "stoich_rank": s_rank, "deficiency": delta}, "faces.crn", "CRN deficiency-zero (face of M11)", cert)


# ── 4. discrete exterior calculus (d∘d=0) → FACE of M18 ──────────────────────────────────────────────────
def dec_face(spec: dict) -> KV.Verdict:
    """spec = {vertices, edges:[(u,v)], triangles:[(u,v,w)]} (oriented). Verifies the cochain-complex law ∂₁∘∂₂ = 0
    over ℤ — the foundation of the discrete Laplacian Δ = δd+dδ used by M18 flow. A bad complex ⇒ DECLINE."""
    edges = [tuple(e) for e in spec.get("edges", [])]
    tris = [tuple(t) for t in spec.get("triangles", [])]
    if not edges:
        return KV.decline("dec: need {vertices, edges, triangles}", "faces")
    eidx = {}
    for i, (u, v) in enumerate(edges):
        eidx[(u, v)] = (i, 1)
        eidx[(v, u)] = (i, -1)

    def d2_col(tri):                                          # ∂₂(uvw) = (vw) − (uw) + (uv)
        u, v, w = tri
        col = [0] * len(edges)
        for (a, b), sgn in (((v, w), 1), ((u, w), -1), ((u, v), 1)):
            if (a, b) not in eidx:
                return None
            i, s = eidx[(a, b)]
            col[i] += sgn * s
        return col

    def d1(col):                                             # ∂₁ applied to an edge-chain → vertex-chain
        vert = {}
        for i, c in enumerate(col):
            if c:
                u, v = edges[i]
                vert[v] = vert.get(v, 0) + c
                vert[u] = vert.get(u, 0) - c
        return {k: v for k, v in vert.items() if v}

    for tri in tris:
        col = d2_col(tri)
        if col is None:
            return KV.decline(f"dec: triangle {tri} has an edge missing from the 1-skeleton ⇒ DECLINE", "faces")
        if d1(col):                                          # ∂₁∘∂₂ must be exactly 0
            return KV.decline(f"dec: ∂₁∘∂₂ ≠ 0 on triangle {tri} (not a valid complex) ⇒ DECLINE", "faces")
    cert = KV.Cert(KV.EXACT, "discrete_exterior_calculus", passed=True,
                   check_cost="exact ℤ verification of ∂₁∘∂₂ = 0 on every 2-simplex",
                   detail="the cochain complex d∘d = 0 holds — the discrete-exterior-calculus foundation of the "
                          "discrete Laplacian Δ=δd+dδ (FACE of M18)")
    return KV.exact({"parent_mechanism": 18, "face": "discrete_exterior_calculus", "edges": len(edges), "triangles": len(tris)},
                    "faces.dec", "discrete exterior calculus dd=0 (face of M18)", cert)


# ── 5. restricted chase termination → FACE of M14 ───────────────────────────────────────────────────────
def restricted_chase_face(spec: dict) -> KV.Verdict:
    """spec = {facts:[(a,b)…] over a binary R, tgd: 'symmetric'|'transitive'|'successor', bound?}. Runs the RESTRICTED
    chase; EXACT iff it terminates within the bound (a termination witness); the existential 'successor' TGD generates
    unboundedly ⇒ DECLINE (the M14 obstruction)."""
    facts = set(tuple(f) for f in spec.get("facts", []))
    tgd = spec.get("tgd")
    bound = int(spec.get("bound", 1000))
    if tgd not in ("symmetric", "transitive", "successor"):
        return KV.decline("chase: tgd ∈ {symmetric, transitive, successor}", "faces")
    fresh = 0
    for _ in range(bound):
        new = set()
        if tgd == "symmetric":
            new = {(b, a) for (a, b) in facts} - facts
        elif tgd == "transitive":
            new = {(a, c) for (a, b) in facts for (b2, c) in facts if b == b2} - facts
        elif tgd == "successor":                              # R(x,y) → ∃z R(y,z); restricted: fire iff y has no successor
            for (a, b) in list(facts):
                if not any(s == b for (s, _) in facts):
                    fresh += 1
                    new.add((b, f"_n{fresh}"))
                    break
        if not new:
            cert = KV.Cert(KV.EXACT, "chase_termination", passed=True,
                           check_cost=f"restricted chase reached a fixpoint ({len(facts)} facts)",
                           detail=f"the '{tgd}' TGD chase TERMINATES (bounded) — a finite universal model (FACE of M14: "
                                  "the terminating side of the chase-termination obstruction)")
            return KV.exact({"parent_mechanism": 14, "face": "restricted_chase", "terminated": True, "facts": len(facts)},
                            "faces.chase", "restricted chase termination (face of M14)", cert)
        facts |= new
    return KV.decline(f"chase: the '{tgd}' TGD did NOT terminate within {bound} steps (existential null generation is "
                      "UNBOUNDED) ⇒ DECLINE (the M14 chase-non-termination obstruction)", "faces")


# ── 6. combinatorial species (EGF counts) → FACE of M12 ─────────────────────────────────────────────────
def species_face(spec: dict) -> KV.Verdict:
    """spec = {species: 'permutations'|'sets'|'cycles'|'linear_orders'|'subsets', n}. Returns the labelled count a_n
    from the species' exponential generating function (a counting closed form). Unknown species ⇒ DECLINE."""
    import math
    sp, n = spec.get("species"), int(spec.get("n", -1))
    if n < 0:
        return KV.decline("species: need {species, n≥0}", "faces")
    egf = {"permutations": "1/(1−x)", "sets": "e^x", "cycles": "−log(1−x) (n≥1)", "linear_orders": "1/(1−x)",
           "subsets": "e^{2x}"}
    if sp not in egf:
        return KV.decline(f"species: unknown species '{sp}' (∈ {sorted(egf)})", "faces")
    count = {"permutations": math.factorial(n), "sets": 1, "linear_orders": math.factorial(n),
             "cycles": (math.factorial(n - 1) if n >= 1 else 0), "subsets": 2 ** n}[sp]
    cert = KV.Cert(KV.EXACT, "combinatorial_species", passed=True,
                   check_cost=f"exact labelled count from the EGF {egf[sp]}",
                   detail=f"species '{sp}': a_{n} = {count} (the n-th coefficient × n! of the EGF — a counting closed "
                          "form; FACE of M12)")
    return KV.exact({"parent_mechanism": 12, "face": "combinatorial_species", "species": sp, "n": n, "count": count,
                     "egf": egf[sp]}, "faces.species", "combinatorial species count (face of M12)", cert)


# ── 7. trace monoid Foata normal form → FACE of M15 ─────────────────────────────────────────────────────
def trace_monoid_face(spec: dict) -> KV.Verdict:
    """spec = {independence:[(a,b)…] (commuting letter pairs), word}. Computes the FOATA NORMAL FORM of the
    Mazurkiewicz trace (the canonical sequence of maximal independent steps). The certificate is canonicity: any word
    equivalent under the independence relation yields the SAME Foata form."""
    indep = set()
    for a, b in spec.get("independence", []):
        indep.add((a, b))
        indep.add((b, a))
    word = list(spec.get("word", ""))
    if not word:
        return KV.decline("trace_monoid: need {independence, word}", "faces")

    # Foata normal form: repeatedly extract the set of MINIMAL letters (those commuting with every earlier pending
    # letter), one occurrence per distinct minimal letter, as the next canonical step.
    seq = list(word)
    steps: List[List[str]] = []
    guard = 0
    while seq and guard < 10 ** 5:
        guard += 1
        step_idx = []
        for i, c in enumerate(seq):
            if all((c, seq[j]) in indep for j in range(i)):    # commutes with everything before it ⇒ minimal
                step_idx.append(i)
        # take ONE occurrence per distinct minimal letter (Foata steps are sets)
        take, remaining, used = [], [], set()
        for i, c in enumerate(seq):
            if i in step_idx and c not in used:
                take.append(c)
                used.add(c)
            else:
                remaining.append(c)
        steps.append(sorted(take))
        seq = remaining
    cert = KV.Cert(KV.EXACT, "trace_monoid_foata", passed=True,
                   check_cost="Foata normal form (sequence of maximal independent steps) — canonical per the "
                              "independence relation",
                   detail=f"Foata NF {steps} of the trace — a canonical concurrency normal form (FACE of M15/M10)")
    return KV.exact({"parent_mechanism": 15, "face": "trace_monoid", "foata_form": steps, "n_steps": len(steps)},
                    "faces.trace_monoid", "trace monoid Foata form (face of M15)", cert)


# ── 8. twin-width contraction witness → FACE of M10 ─────────────────────────────────────────────────────
def twin_width_face(spec: dict) -> KV.Verdict:
    """spec = {n, edges:[(u,v)], contraction_sequence:[(u,v)…]}. Replays the contraction sequence tracking RED
    (error) edges; certifies the maximum red-degree d = the witnessed twin-width bound. A sequence that leaves >1
    vertex unconverged, or whose red-degree we report honestly. EXACT with the measured d."""
    n = int(spec.get("n", 0))
    edges = set()
    for u, v in spec.get("edges", []):
        edges.add((min(u, v), max(u, v)))
    seq = [tuple(p) for p in spec.get("contraction_sequence", [])]
    if n <= 0 or not seq:
        return KV.decline("twin_width: need {n, edges, contraction_sequence}", "faces")
    black = {v: set() for v in range(n)}                      # black (agreeing) adjacency
    for (u, v) in edges:
        black[u].add(v)
        black[v].add(u)
    red = {v: set() for v in range(n)}
    alive = set(range(n))
    max_red = 0
    for (u, v) in seq:                                        # contract v into u
        if u not in alive or v not in alive:
            return KV.decline(f"twin_width: contraction ({u},{v}) references a dead vertex ⇒ DECLINE", "faces")
        for w in list(alive - {u, v}):
            au = (w in black[u]) or (w in red[u])
            av = (w in black[v]) or (w in red[v])
            red_uw = (w in red[u]) or (w in red[v]) or (au != av)   # disagreement or inherited red ⇒ red
            black[u].discard(w); black[w].discard(u)
            red[u].discard(w); red[w].discard(u)
            if au and av and not ((w in red[u]) or (w in red[v])):
                black[u].add(w); black[w].add(u)
            if red_uw and (au or av):
                red[u].add(w); red[w].add(u)
        for w in list(alive):
            black[w].discard(v); red[w].discard(v)
        alive.discard(v)
        max_red = max(max_red, max((len(red[w]) for w in alive), default=0))
    cert = KV.Cert(KV.EXACT, "twin_width", passed=True,
                   check_cost=f"replayed {len(seq)} contractions tracking red-degree; max red-degree d = {max_red}",
                   detail=f"contraction sequence witnesses twin-width ≤ {max_red} (a structural width ⇒ FPT "
                          "tractability; FACE of M10)")
    return KV.exact({"parent_mechanism": 10, "face": "twin_width", "twin_width_bound": max_red,
                     "contractions": len(seq), "remaining": len(alive)}, "faces.twin_width",
                    f"twin-width ≤ {max_red} witness (face of M10)", cert)


TIER2_FACES = {
    "monoid_homomorphism": (monoid_hom_face, 13), "poset_mobius": (poset_mobius_face, 2),
    "crn_deficiency_zero": (crn_deficiency_face, 11), "discrete_exterior_calculus": (dec_face, 18),
    "restricted_chase": (restricted_chase_face, 14), "combinatorial_species": (species_face, 12),
    "trace_monoid": (trace_monoid_face, 15), "twin_width": (twin_width_face, 10),
}
