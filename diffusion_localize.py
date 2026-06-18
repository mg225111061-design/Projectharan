"""
v27 STAGE 15 (layer 2 + funnel) — graph-Laplacian diffusion re-ranking, then SOUND confirmation.
=================================================================================================
Layer 1 (SBFL) gives a cheap statistical ranking. Layer 2 spreads that suspicion along the dependency
graph (a suspicious function makes its callers/callees a little suspicious too), then layer 3 CONFIRMS
the top candidates with a sound verifier — a witness per real bug, or a class-absence proof.

★ THE REAL MATH (§0.8, §5.6) ★: the heat equation ∂u/∂t = −L·u, the random walk, and spectral methods
all use the SAME graph Laplacian L = D − A. PRFL-style PageRank propagation is exactly one family of
this (its transition W relates to the random-walk Laplacian by L_rw = I − W). That shared L is the honest
content of "the equations are the same" — there is NO "entropy / temperature / free-energy" here (those
were the mirage, §5.6). We expose both `pagerank_diffuse` and `heat_diffuse` and they share L.

★ HONEST OUTPUT (§1.5) ★ per candidate:
    VULN_PROVEN    — a real bug of a modeled CLASS with an EXPLOIT WITNESS (from S3 incorrectness / S2 taint)
    ABSENCE_PROVEN — that class is proven absent, WITH the modeled class + bounds stated (Rice-bounded)
    RANKED         — ranking only; the sound layer could not model it ⇒ NOT confirmed (explicit label)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import incorrectness as IC
import sbfl as SB
import taint_ifds as TI

Graph = Dict[str, List[str]]   # element -> dependency neighbors (undirected for spreading)


# ── layer 2a: PageRank diffusion (PRFL-style) ───────────────────────────────────────────────────────
def pagerank_diffuse(scores: Dict[str, float], graph: Graph, damping: float = 0.85,
                     iters: int = 200, tol: float = 1e-12) -> Dict[str, float]:
    """Spread SBFL suspicion over the graph: r ← (1−d)·p + d·Σ_{m~n} r_m/deg(m), personalized by `p`
    (the normalized SBFL scores). This is PageRank with a personalization vector = random walk on L."""
    nodes = sorted(set(graph) | set(scores))
    pos = {n: max(scores.get(n, 0.0), 0.0) for n in nodes}
    total = sum(pos.values()) or 1.0
    p = {n: pos[n] / total for n in nodes}
    deg = {n: len([m for m in graph.get(n, []) if m != n]) for n in nodes}
    r = dict(p)
    for _ in range(iters):
        nxt = {}
        dangling = sum(r[n] for n in nodes if deg[n] == 0)
        for n in nodes:
            inflow = sum(r[m] / deg[m] for m in graph.get(n, []) if m != n and deg[m] > 0)
            nxt[n] = (1 - damping) * p[n] + damping * (inflow + dangling * p[n])
        delta = sum(abs(nxt[n] - r[n]) for n in nodes)
        r = nxt
        if delta < tol:
            break
    return r


# ── layer 2b: heat-kernel diffusion (same L, explicit Euler approx of e^{−tL}) ──────────────────────
def heat_diffuse(scores: Dict[str, float], graph: Graph, t: float = 1.0, steps: int = 50) -> Dict[str, float]:
    """u(t) = e^{−tL} u0, approximated by `steps` explicit-Euler steps u ← u − (t/steps)·L·u. Same
    Laplacian L = D − A as PageRank / spectral — the honest shared object."""
    nodes = sorted(set(graph) | set(scores))
    u = {n: max(scores.get(n, 0.0), 0.0) for n in nodes}
    dmax = max((len([m for m in graph.get(n, []) if m != n]) for n in nodes), default=1)
    dt = min(t / max(steps, 1), 1.0 / (2 * dmax + 1))            # stable: dt < 1/λ_max bound
    for _ in range(steps):
        lu = {n: len([m for m in graph.get(n, []) if m != n]) * u[n]
                 - sum(u[m] for m in graph.get(n, []) if m != n) for n in nodes}
        u = {n: u[n] - dt * lu[n] for n in nodes}
    return u


# ── layer 3: sound confirmation (reuse S3 incorrectness + S2 taint) ─────────────────────────────────
@dataclass
class Finding:
    element: str
    status: str                       # VULN_PROVEN | ABSENCE_PROVEN | RANKED
    bug_class: str = "-"
    witness: Optional[dict] = None
    score: float = 0.0
    detail: str = ""

    def __str__(self):
        if self.status == "VULN_PROVEN":
            return f"VULN_PROVEN [{self.bug_class}] {self.element} witness={self.witness}"
        if self.status == "ABSENCE_PROVEN":
            return f"ABSENCE_PROVEN [{self.bug_class}] {self.element} ({self.detail})"
        return f"RANKED {self.element} (score={self.score:.3f}) — NOT confirmed ({self.detail})"


def _confirm(element: str, code: str, score: float) -> Finding:
    """Sound layer-3 gate for one candidate: a witness (VULN_PROVEN), an absence proof, or RANKED."""
    bug = IC.check_reachable_bugs(code)
    if bug.status == "BUG_REACHABLE":
        b = bug.bugs[0]
        return Finding(element, "VULN_PROVEN", b.get("cls", "reachable_bug"), b.get("witness"), score,
                       f"line {b.get('line')}")
    taint = TI.prove_injection_free(code)
    if taint.status == "INJECTION_FLOW":
        f = taint.flows[0]
        return Finding(element, "VULN_PROVEN", "injection", f, score, f"{f.get('source')}→{f.get('sink')}")
    if bug.status == "NO_BUG_FOUND" or taint.status == "INJECTION_FREE":
        cls = "div/mod-by-zero" if bug.status == "NO_BUG_FOUND" else "injection"
        return Finding(element, "ABSENCE_PROVEN", cls, None, score,
                       "absent within the MODELED class on the path-condition bounds (Rice-bounded)")
    return Finding(element, "RANKED", "-", None, score, "sound layer could not model this element")


# ── the funnel: statistics → diffusion → sound verification ─────────────────────────────────────────
@dataclass
class FunnelResult:
    findings: List[Finding] = field(default_factory=list)
    ranked_order: List[str] = field(default_factory=list)
    diffused: Dict[str, float] = field(default_factory=dict)
    note: str = ""

    @property
    def proven(self) -> List[Finding]:
        return [f for f in self.findings if f.status == "VULN_PROVEN"]


def funnel(tests: Sequence[SB.Test], graph: Graph, code_map: Dict[str, str],
           metric: str = "op2", topk: int = 3, diffuse: str = "pagerank") -> FunnelResult:
    """Run the 3-layer funnel: SBFL rank → graph-Laplacian diffusion re-rank → sound confirm the top-k.
    `code_map` supplies HARAN source per element so layer 3 can emit a witness or an absence proof."""
    rank = SB.suspiciousness(tests, metric)
    if diffuse == "pagerank":
        diff = pagerank_diffuse(rank.scores, graph)
    elif diffuse == "heat":
        diff = heat_diffuse(rank.scores, graph)
    else:
        diff = dict(rank.scores)
    order = [e for e, _ in sorted(diff.items(), key=lambda kv: (-kv[1], kv[0]))]
    findings: List[Finding] = []
    for e in order[:topk]:
        if e in code_map:
            findings.append(_confirm(e, code_map[e], diff.get(e, 0.0)))
        else:
            findings.append(Finding(e, "RANKED", score=diff.get(e, 0.0), detail="no source mapped"))
    note = (f"layer1={metric} (RANKED, not proof) → layer2={diffuse} diffusion (shared Laplacian L) → "
            f"layer3 sound confirm. Rice-bounded: not all bugs are findable; multi-fault degrades SBFL.")
    return FunnelResult(findings, order, diff, note)
