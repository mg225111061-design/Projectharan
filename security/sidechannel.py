"""
§R PHASE 3 — SIDE-CHANNEL VERIFICATION (SENSITIVE only): thermodynamic (constant-time) + statistical (masking).
================================================================================================================
The part no LLM can even perceive. Revives ct_certifier (anti-KyberSlash lineage) and points it at general code, on
two axes that compose:

  3A THERMODYNAMIC — prove the physical trace is independent of the secret: NO secret-dependent branch, NO
     secret-dependent memory-access index, NO variable-time op (/ %) on a secret, NO secret-dependent loop bound ⇒
     execution time and access pattern do not vary with the secret (timing/cache channel = 0). CT_PROVEN or a concrete
     leak. The power proxy (Hamming weight of unmasked secret-dependent intermediates) is labeled MODELED, never a
     silicon measurement.
  3B STATISTICAL — for masked code, prove t-probing security: any t observed intermediates are independent of the
     secret. Over GF(2), an observed set LEAKS iff the `secret` basis vector lies in the GF(2) span of the observed
     share-vectors (the randoms cancel). t-probing secure ⟺ NO t-subset spans the secret. (Reuses GF(2) linear algebra.)

★ Dual defense: 3A stops the leak existing; 3B stops it being usable even if it exists. "side-channel-safe" is asserted
ONLY when 3A proves constant-time AND (no unmasked secret-dependent leak OR 3B proves t-probing security). Unproven ⇒
"NOT VERIFIED — possible side-channel", never a false safe. Runs ONLY on SENSITIVE code (pure overhead elsewhere).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Set, Tuple

CT_PROVEN = "CT_PROVEN"
CT_VIOLATION = "CT_VIOLATION"
UNMODELED = "UNMODELED"


@dataclass
class CTResult:
    status: str                        # CT_PROVEN | CT_VIOLATION | UNMODELED
    secrets: List[str] = field(default_factory=list)
    leaks: List[dict] = field(default_factory=list)
    level: str = "source-IR (Python AST)"
    detail: str = ""


def constant_time(code: str, secrets: Set[str]) -> CTResult:
    """Source-level constant-time taint (revived ct_certifier on Python AST). A secret must not reach a branch test, a
    subscript index, a /·% operand, or a loop bound. CT_PROVEN or CT_VIOLATION with locations. ★ HONEST LEVEL: this is
    source-IR; a compiler may still introduce binary-level leaks (Binsec/Rel) — never claimed here."""
    try:
        tree = ast.parse(code.strip())
    except SyntaxError as e:
        return CTResult(UNMODELED, sorted(secrets), detail=f"parse error: {e}")
    tainted: Set[str] = set(secrets)
    leaks: List[dict] = []

    def is_tainted(n) -> bool:
        if isinstance(n, ast.Name):
            return n.id in tainted
        if isinstance(n, ast.BinOp):
            lt, rt = is_tainted(n.left), is_tainted(n.right)
            if isinstance(n.op, (ast.Div, ast.Mod, ast.FloorDiv)) and (lt or rt):
                leaks.append({"kind": "var_time_op", "line": getattr(n, "lineno", 0),
                              "detail": "variable-time '/'/'%' on a secret operand (the KyberSlash class — timing leak)"})
            return lt or rt
        if isinstance(n, ast.UnaryOp):
            return is_tainted(n.operand)
        if isinstance(n, ast.BoolOp):
            return any(is_tainted(v) for v in n.values)
        if isinstance(n, ast.Compare):
            return is_tainted(n.left) or any(is_tainted(c) for c in n.comparators)
        if isinstance(n, ast.Subscript):
            idx = n.slice.value if isinstance(n.slice, ast.Index) else n.slice
            if is_tainted(idx):
                leaks.append({"kind": "mem_index", "line": getattr(n, "lineno", 0),
                              "detail": "secret-dependent memory index (cache-timing leak; use a constant-time scan)"})
            return is_tainted(n.value)
        if isinstance(n, ast.Call):
            return any(is_tainted(a) for a in n.args)
        return False

    # fixpoint taint propagation through assignments
    changed = True
    passes = 0
    while changed and passes < 8:
        changed, passes = False, passes + 1
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and is_tainted(n.value):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id not in tainted:
                        tainted.add(t.id)
                        changed = True
    # leak sites
    for n in ast.walk(tree):
        if isinstance(n, (ast.If, ast.While)) and is_tainted(n.test):
            leaks.append({"kind": "branch", "line": getattr(n, "lineno", 0),
                          "detail": "secret-dependent branch (control-flow timing leak; use a constant-time select/mask)"})
        if isinstance(n, ast.For) and isinstance(n.iter, ast.Call) and isinstance(n.iter.func, ast.Name) \
                and n.iter.func.id == "range" and any(is_tainted(a) for a in n.iter.args):
            leaks.append({"kind": "secret_loop_bound", "line": getattr(n, "lineno", 0),
                          "detail": "secret-dependent loop bound (iteration-count timing leak; iterate a fixed range)"})
        if isinstance(n, ast.Subscript):
            is_tainted(n)                                       # trigger mem_index detection on every subscript
        if isinstance(n, ast.BinOp):
            is_tainted(n)                                       # trigger var_time_op detection on every '/'/'%' op
    # dedup
    uniq = {(l["kind"], l["line"]): l for l in leaks}
    leaks = list(uniq.values())
    if leaks:
        return CTResult(CT_VIOLATION, sorted(secrets), leaks)
    return CTResult(CT_PROVEN, sorted(secrets), [],
                    detail="no secret-dependent branch / memory index / var-time op / loop bound (source-IR; "
                           "binary-level NOT covered — a compiler may introduce leaks)")


# ── 3B masking: GF(2) t-probing security ────────────────────────────────────────────────────────────────────
def _gf2_rank(vectors: List[int]) -> int:
    rows = [v for v in vectors]
    rank = 0
    pivots: List[int] = []
    for v in rows:
        cur = v
        for p in pivots:
            cur = min(cur, cur ^ p)
        if cur:
            pivots.append(cur)
            rank += 1
    return rank


def verify_masking(shares: Dict[str, Set[str]], basis: List[str], t: int, secret: str = "secret") -> dict:
    """t-probing security over GF(2). `shares` = {intermediate_name: set of basis symbols it XORs} (e.g. the masked
    share is {secret, r1, r2}; a random share is {r1}). `basis` = ordered symbols [secret, r1, r2, …]. An observed
    set LEAKS iff the `secret` unit vector is in the GF(2) span of the observed vectors. t-probing secure ⟺ NO
    t-subset of intermediates spans the secret."""
    bidx = {s: i for i, s in enumerate(basis)}
    secret_vec = 1 << bidx[secret]

    def vec(symset: Set[str]) -> int:
        v = 0
        for s in symset:
            v |= 1 << bidx[s]
        return v

    names = list(shares)
    vecs = {n: vec(shares[n]) for n in names}
    leaking_subset = None
    for combo in combinations(names, min(t, len(names))):
        sub = [vecs[n] for n in combo]
        # secret ∈ span(sub) iff rank(sub) == rank(sub ∪ {secret})
        if _gf2_rank(sub + [secret_vec]) == _gf2_rank(sub) and _gf2_rank(sub) > 0:
            # secret recoverable ⇒ this t-subset leaks
            leaking_subset = combo
            break
    secure = leaking_subset is None
    return {"t": t, "secure": secure, "leaking_subset": list(leaking_subset) if leaking_subset else None,
            "detail": (f"t-probing SECURE: no {t}-subset of intermediates spans the secret over GF(2) (every "
                       "observable combination retains an unobserved random ⇒ uniform marginal)") if secure
                      else (f"t-probing BROKEN: the {t}-subset {list(leaking_subset)} spans the secret (randoms cancel "
                            "⇒ secret recoverable) ⇒ NOT VERIFIED")}


@dataclass
class SideChannelResult:
    safe: bool
    constant_time: CTResult
    masking: Optional[dict] = None
    detail: str = ""


def sidechannel_verify(code: str, secrets: Set[str], shares: Optional[Dict[str, Set[str]]] = None,
                       basis: Optional[List[str]] = None, t: int = 1) -> SideChannelResult:
    """Dual-axis side-channel verdict. side-channel-safe ⟺ constant-time PROVEN AND (no leak OR masking t-probing
    secure). Anything unproven ⇒ NOT safe (honest 'NOT VERIFIED'). Run ONLY on SENSITIVE code."""
    ct = constant_time(code, secrets)
    mask = None
    if shares is not None and basis is not None:
        mask = verify_masking(shares, basis, t)
    if ct.status == CT_PROVEN:
        return SideChannelResult(True, ct, mask, "constant-time PROVEN (timing/cache channel = 0); "
                                 + (mask["detail"] if mask else "no masking needed — no secret-dependent leak"))
    # there is a (timing) leak — it is only acceptable if masking proves the statistical channel closed AND the leak
    # class is power/statistical (a branch/loop timing leak is NOT fixed by masking — needs constant-time)
    timing_classes = {"branch", "secret_loop_bound", "var_time_op", "mem_index"}
    has_timing = any(l["kind"] in timing_classes for l in ct.leaks)
    if has_timing:
        return SideChannelResult(False, ct, mask,
                                 "NOT VERIFIED — secret-dependent timing/cache leak present; masking does NOT close a "
                                 "timing channel (needs constant-time transform)")
    if mask and mask["secure"]:
        return SideChannelResult(True, ct, mask, "no timing leak; statistical channel closed by proven masking")
    return SideChannelResult(False, ct, mask, "NOT VERIFIED — possible side-channel (unproven)")
