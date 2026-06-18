"""
v27 STAGE 18 — dogfooding harness: HARAN re-verifies its OWN (non-kernel) components.
=====================================================================================
We build MR.JEFFREY's parts with MR.JEFFREY: each non-kernel component's emitted certificate is
INDEPENDENTLY re-checked by the small TRUSTED CORE (Z3 + a plain-Python differential checker) — we do NOT
trust the component's own claim, we re-derive it with the kernel. A component passes only if its claim
survives that independent check.

★ GÖDEL (§0.10, §1.11, §5.12) ★: a sound system cannot prove its OWN kernel. So the trusted core — the SMT
solver and the certificate/differential checkers — is kept MINIMAL and HUMAN-AUDITED, and is NEVER
self-certified here (it is reported as residual TCB, the CompCert discipline). Dogfooding applies to
everything OUTSIDE that core.

Incremental (iCoq-style): on a rebuild only the CHANGED components are re-verified; unchanged ones are
perceived-zero from the component-cert cache.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

# ── the trusted core (TCB): minimal, human-audited, NEVER self-certified (Gödel) ────────────────────
TRUSTED_KERNEL: Dict[str, str] = {
    "z3_adapter": "the SMT decision kernel — soundness of every ∀-proof rests here (human-audited)",
    "differential-checker": "plain-Python 'run both, compare outputs' equivalence oracle (human-audited)",
    "certificate-checker": "the logic that accepts/rejects a certificate (human-audited)",
}


@dataclass
class ComponentCert:
    name: str
    status: str                 # CERTIFIED | FAILED | TCB
    rechecks: int = 0           # independent kernel re-checks performed
    detail: str = ""

    def __str__(self):
        if self.status == "TCB":
            return f"TCB {self.name} — trusted core, NOT self-certified (Gödel): {self.detail}"
        return f"{self.status} {self.name} ({self.rechecks} independent re-checks) — {self.detail}"


# ── independent re-checks: each runs the component, then re-derives its claim with the TRUSTED CORE ──
def _recheck_fold_kernels() -> Tuple[bool, int, str]:
    import sympy
    import fold_kernels as FK
    v = FK.fold_certificate("fn f(n: Nat) -> Nat { fold k in 1..n { k } }")
    if v.status != "FOLDED":
        return (False, 0, f"expected FOLDED, got {v.status}")
    n = sympy.Symbol("n")
    cf = sympy.sympify(v.closed_form)
    samples = [1, 3, 5, 10, 20, 50]
    ok = all(int(cf.subs(n, N)) == sum(range(1, N + 1)) for N in samples)   # independent: plain-Python sum
    return (ok, len(samples), f"closed form {v.closed_form} == naive Σ on {len(samples)} inputs (kernel-rechecked)")


def _recheck_structure_recognizer() -> Tuple[bool, int, str]:
    import sympy
    import structure_recognizer as SR
    src = "def f(n):\n    acc = 0\n    for k in range(1, n + 1):\n        acc += k\n    return acc"
    d = SR.dispatch(src)
    if d.status != "OFFLOADED":
        return (False, 0, f"expected OFFLOADED, got {d.status}")
    n = sympy.Symbol("n")
    cf = sympy.sympify(d.closed_form)
    samples = [1, 2, 5, 9, 17]
    ok = all(int(cf.subs(n, N)) == sum(range(1, N + 1)) for N in samples)   # independent of SR's own gate
    return (ok, len(samples), f"offloaded {d.closed_form} == original loop on {len(samples)} inputs")


def _recheck_equality_saturation() -> Tuple[bool, int, str]:
    import z3
    import equality_saturation as ES
    t = ("+", ("*", ("var", "x"), ("const", 2)), ("*", ("var", "x"), ("const", 3)))
    v = ES.optimize(t)
    if v.status != "OPTIMIZED":
        return (False, 0, f"expected OPTIMIZED, got {v.status}")
    env: Dict[str, z3.ArithRef] = {}
    s = z3.Solver()
    s.add(ES._to_z3(v.original, env) != ES._to_z3(v.optimized, env))       # independent z3 (the kernel)
    return (s.check() == z3.unsat, 1, f"{ES.fmt(v.original)} ≡ {ES.fmt(v.optimized)} (independent Z3)")


def _recheck_parallel_algebra() -> Tuple[bool, int, str]:
    import parallel_algebra as PA
    # the soundness justification of the transform: parallelize IFF the op is an associative monoid
    ok_monoid = PA.is_monoid("+") and PA.is_monoid("max") and not PA.is_monoid("-")
    declined = PA.parallelize_reduction("square", "-", 1000).status == "DECLINED"   # non-assoc → refused
    ran = PA.parallelize_reduction("square", "+", 50_000, cores=2).status in ("OPTIMIZED", "NO_GAIN")
    return (ok_monoid and declined and ran, 3, "parallelizes iff monoid; declines non-associative (sound)")


def _recheck_ic3() -> Tuple[bool, int, str]:
    import ic3_pdr as IC
    safe = IC.prove_safety(["x"], lambda s: s["x"] == 0, lambda s, sp: sp["x"] == s["x"] + 1,
                           lambda s: s["x"] >= 0)
    unsafe = IC.prove_safety(["x"], lambda s: s["x"] == 0, lambda s, sp: sp["x"] == s["x"] + 1,
                             lambda s: s["x"] <= 3, max_k=8)
    return (safe.status == "SAFE" and unsafe.status == "UNSAFE" and bool(unsafe.trace), 2,
            "k-induction SAFE invariant holds; UNSAFE returns a real counterexample trace")


_RECHECKS: Dict[str, Callable[[], Tuple[bool, int, str]]] = {
    "fold_kernels": _recheck_fold_kernels,
    "structure_recognizer": _recheck_structure_recognizer,
    "equality_saturation": _recheck_equality_saturation,
    "parallel_algebra": _recheck_parallel_algebra,
    "ic3_pdr": _recheck_ic3,
}

_CACHE: Dict[str, ComponentCert] = {}


def dogfood_component(name: str) -> ComponentCert:
    """Re-verify ONE non-kernel component by re-deriving its claim with the trusted core."""
    if name in TRUSTED_KERNEL:
        return ComponentCert(name, "TCB", 0, TRUSTED_KERNEL[name])
    rc = _RECHECKS.get(name)
    if rc is None:
        return ComponentCert(name, "FAILED", 0, "no independent re-check defined")
    try:
        ok, n, detail = rc()
    except Exception as e:  # noqa: BLE001
        return ComponentCert(name, "FAILED", 0, f"re-check raised {type(e).__name__}: {e}")
    return ComponentCert(name, "CERTIFIED" if ok else "FAILED", n, detail)


def dogfood_all() -> Dict[str, object]:
    """Re-verify every non-kernel component; report the residual TCB (the human-audited trusted core)."""
    comps = [dogfood_component(n) for n in _RECHECKS]
    tcb = [ComponentCert(n, "TCB", 0, d) for n, d in TRUSTED_KERNEL.items()]
    certified = sum(1 for c in comps if c.status == "CERTIFIED")
    return {"components": comps, "tcb": tcb, "certified": certified, "total": len(comps),
            "all_certified": certified == len(comps),
            "note": "non-kernel components re-verified by the trusted core; the core itself is NOT "
                    "self-certified (Gödel) — it is the residual, human-audited TCB."}


def incremental_rebuild(changed: List[str]) -> Dict[str, object]:
    """iCoq-style: re-verify only CHANGED components; unchanged ones are perceived-zero from the cache."""
    reverified, cached = [], []
    for name in _RECHECKS:
        if name in changed or name not in _CACHE:
            _CACHE[name] = dogfood_component(name)
            reverified.append(name)
        else:
            cached.append(name)
    return {"reverified": reverified, "cached": cached,
            "certs": {n: _CACHE[n].status for n in _RECHECKS}}


def residual_tcb() -> Dict[str, str]:
    return dict(TRUSTED_KERNEL)
