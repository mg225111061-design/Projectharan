"""
v28 STAGE 21 — large-prompt GROUNDING pipeline (grounding, NOT understanding — Rice-bounded).
==============================================================================================
A frontier LLM blurs a huge prompt: attention loses the middle (lost-in-the-middle; RULER shows effective
context ≪ nominal). We do NOT claim to "understand" the input (Rice). We GROUND it — structurally — and
report measurable proxies:

  1. structure      — parse to entities + a dependency/call graph (reuse the S20 IR / facts).
  2. hierarchical   — cluster the graph (reuse S14 spectral partition) into a 2-level summary TREE with
       index          EXTRACTIVE (no-LLM) summaries. ★Honest: extractive, not LLM-abstractive — real
                       embeddings + abstractive summaries are the [BLOCKED: key] enhancement.★
  3. multi-hop      — answer reachability / transitive-dependency queries by EXACT graph traversal. By
       retrieval      construction there is no lost-in-the-middle: the answer is complete and grounded.
  4. spec extract   — pull checkable claims (HARAN `ensures`-style) and MACHINE-VERIFY them: GROUNDED
       + verify       (proof) / REFUTED (counterexample) / BEST_EFFORT (natural-language, unverifiable —
                       labeled, never faked).

★ HONEST (§1.2,1.4,§5.2) ★: full semantic understanding is impossible (Rice). The edge is exactly three
things: (a) the VERIFIABLE slice (we prove/refute it), (b) EXACT structural retrieval (Ω(input), no
hallucinated middle), (c) grounding ≠ understanding. Natural-language intent we are NO better than an LLM
at — those claims are BEST_EFFORT. A live LLM head-to-head needs a key/egress ([BLOCKED]); the structural
proxies here are measured.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import ai_loop
import repo_partition as RP
try:
    import graph_core as GC          # v38 Rust graph core (cdylib/ctypes) — drop-in, internal Python fallback
except Exception:                     # noqa: BLE001 — never let an import break grounding
    GC = None


def _partition(graph, k):
    """Live partition: prefer the differential-verified Rust core (removes the N=4000 ceiling), else the
    pure-Python repo_partition. graph_core.partition falls back internally too, so this is doubly safe."""
    if GC is not None and GC.available():
        return GC.partition(graph, k=k)
    return RP.partition(graph, k=k)


@dataclass
class Entity:
    name: str
    source: str = ""        # the snippet (HARAN/code) — the verifiable slice
    kind: str = "function"


@dataclass
class GroundingIndex:
    entities: Dict[str, Entity]
    edges: List[Tuple[str, str]]                 # directed dependency/call edges a→b
    adj: Dict[str, List[str]] = field(default_factory=dict)
    clusters: List[List[str]] = field(default_factory=list)
    cluster_summaries: List[str] = field(default_factory=list)
    root_summary: str = ""

    def transitive_deps(self, start: str) -> Set[str]:
        """Exact multi-hop: everything reachable from `start` along dependency edges (BFS — complete)."""
        seen: Set[str] = set()
        q = deque(self.adj.get(start, []))
        while q:
            x = q.popleft()
            if x not in seen:
                seen.add(x)
                q.extend(self.adj.get(x, []))
        return seen

    def reaches(self, src: str, dst: str) -> bool:
        return dst in self.transitive_deps(src)

    def coverage(self) -> float:
        """Fraction of entities that landed in the hierarchical index (graph coverage proxy)."""
        indexed = {e for c in self.clusters for e in c}
        return len(indexed) / len(self.entities) if self.entities else 0.0


def build_index(entities: List[Entity], edges: List[Tuple[str, str]], k: int = 2) -> GroundingIndex:
    ents = {e.name: e for e in entities}
    adj: Dict[str, List[str]] = {e.name: [] for e in entities}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, [])
    idx = GroundingIndex(ents, list(edges), adj)
    # cluster via the S14 spectral partitioner (undirected view) → the leaves of the summary tree
    undirected: Dict[str, List[str]] = {n: [] for n in ents}
    for a, b in edges:
        if a in ents and b in ents:
            undirected[a].append(b)
            undirected[b].append(a)
    if len(ents) >= 2:
        part = _partition(undirected, k=min(k, len(ents)))
        nodes_sorted = sorted(undirected)
        clusters: Dict[int, List[str]] = {}
        for node_idx, pid in enumerate(part.parts):
            clusters.setdefault(pid, []).append(nodes_sorted[node_idx])
        idx.clusters = [sorted(v) for v in clusters.values()]
    else:
        idx.clusters = [list(ents)]
    # EXTRACTIVE (no-LLM) summaries: signatures + counts per cluster, then a root summary
    idx.cluster_summaries = [f"cluster[{', '.join(c)}] — {len(c)} entities" for c in idx.clusters]
    idx.root_summary = f"{len(ents)} entities in {len(idx.clusters)} clusters; {len(edges)} dependency edges"
    return idx


# ── spec extraction + machine verification ──────────────────────────────────────────────────────────
@dataclass
class ClaimVerdict:
    claim: str
    status: str             # GROUNDED | REFUTED | BEST_EFFORT
    detail: str = ""
    counterexample: Optional[dict] = None


def _is_haran_spec(text: str) -> bool:
    return text.strip().startswith("fn ") and "ensures" in text


def verify_claim(claim: str) -> ClaimVerdict:
    """A checkable claim (a HARAN function with `ensures`) is GROUNDED (proven) / REFUTED (counterexample);
    anything not formalizable here is BEST_EFFORT (labeled — never a fake GROUNDED)."""
    if _is_haran_spec(claim):
        v = ai_loop.verify_haran(claim)
        if v.ok:
            return ClaimVerdict(claim, "GROUNDED", "verified against its ensures spec")
        return ClaimVerdict(claim, "REFUTED", "spec violated", v.counterexample)
    return ClaimVerdict(claim, "BEST_EFFORT", "natural-language / non-formalizable claim — NOT verified "
                        "(we are no better than an LLM here; labeled, not faked)")


@dataclass
class GroundingResult:
    index: GroundingIndex
    claims: List[ClaimVerdict]
    multihop_accuracy: float = 0.0
    fidelity: float = 0.0           # fraction of formalizable claims actually GROUNDED/REFUTED (not blurred)
    coverage: float = 0.0
    note: str = ""

    @property
    def grounded(self) -> List[ClaimVerdict]:
        return [c for c in self.claims if c.status == "GROUNDED"]


def ground(entities: List[Entity], edges: List[Tuple[str, str]], claims: List[str],
           multihop_queries: Optional[List[Tuple[str, str, bool]]] = None) -> GroundingResult:
    """Build the index, verify the claims, and report measurable grounding proxies. NOT 'understanding'."""
    idx = build_index(entities, edges)
    verdicts = [verify_claim(c) for c in claims]
    formalizable = [v for v in verdicts if v.status in ("GROUNDED", "REFUTED")]
    fidelity = len(formalizable) / len(verdicts) if verdicts else 0.0
    acc = 1.0
    if multihop_queries:
        correct = sum(1 for (s, d, expected) in multihop_queries if idx.reaches(s, d) == expected)
        acc = correct / len(multihop_queries)
    note = ("GROUNDING, not understanding (Rice). Multi-hop retrieval is EXACT graph traversal (no "
            "lost-in-the-middle); claims are proven/refuted or labeled BEST_EFFORT. A live LLM comparison "
            "is [BLOCKED: key/egress].")
    return GroundingResult(idx, verdicts, acc, fidelity, idx.coverage(), note)
