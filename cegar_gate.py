"""
PHASE 3 (CODE correctness) — CEGAR / spurious-counterexample gating + differential soundness.
=============================================================================================
The write→verify→fix loop's dominant failure mode is acting on a counterexample that is an ARTIFACT of the
abstraction (wrong width, wrong modeling), or trusting a "proof" from an unsound abstraction. Two sound gates:

  • COUNTEREXAMPLE GATE (spurious-cex rejection): a solver claims orig ≠ opt with witness `cex`. Before declaring
    the transform unsound, CONCRETELY EXECUTE orig(cex) and opt(cex) under real machine (two's-complement, width-w)
    semantics. Only a counterexample that GENUINELY differs concretely is a real refutation ⇒ certified DECLINE
    (keep the original). If orig(cex)==opt(cex) concretely, the counterexample was SPURIOUS ⇒ rejected.
  • SOUNDNESS SPOT-CHECK (defense in depth): when a transform is "proven equivalent", differential-test it on
    random concrete inputs. A single concrete mismatch means the proof/abstraction was UNSOUND — surfaced as a
    correctness bug, never silently trusted.

Both gates are CONCRETE EXECUTION (the smallest possible TCB): the machine itself adjudicates. Sound/conservative —
a transform is accepted only if no real counterexample exists AND the concrete spot-check agrees.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import kernel_verdict as KV


def _wrap(v: int, bits: int, signed: bool = True) -> int:
    """Two's-complement wrap of v to `bits` (signed interpretation by default)."""
    m = (1 << bits)
    v &= (m - 1)
    if signed and (v >> (bits - 1)) & 1:
        v -= m
    return v


def _concrete(fn: Callable, args: List[int], bits: int) -> int:
    """Evaluate fn over machine-int args (already wrapped) and wrap the result to `bits`."""
    return _wrap(int(fn(*args)), bits)


@dataclass
class GateResult:
    verdict: KV.Verdict
    real_counterexample: Optional[Dict[str, int]] = None
    spurious: bool = False


def gate_counterexample(orig: Callable, opt: Callable, cex: Dict[str, int], bits: int,
                        argnames: List[str]) -> GateResult:
    """Confirm or reject a candidate counterexample by CONCRETE machine execution. A genuine concrete difference
    ⇒ the transform is UNSOUND (certified DECLINE, keep original). Agreement ⇒ the counterexample was SPURIOUS."""
    args = [_wrap(int(cex.get(n, 0)), bits) for n in argnames]
    o = _concrete(orig, args, bits)
    p = _concrete(opt, args, bits)
    if o != p:
        cert = KV.Cert(KV.EXACT, "concrete_counterexample", passed=True, check_cost="two machine evaluations",
                       detail=f"REAL counterexample {dict(zip(argnames, args))}: orig={o} ≠ opt={p} "
                              f"(concrete {bits}-bit two's-complement) ⇒ transform UNSOUND, keep original")
        return GateResult(KV.decline(f"cegar: transform refuted by concrete counterexample {dict(zip(argnames, args))} "
                                     f"(orig={o}≠opt={p}) ⇒ DECLINE (keep original)", "cegar"),
                          real_counterexample=dict(zip(argnames, args)))
    return GateResult(KV.exact({"spurious": True}, "cegar.gate", "spurious-cex rejection",
                               KV.Cert(KV.EXACT, "spurious_rejected", True, "two machine evaluations",
                                       detail=f"counterexample {dict(zip(argnames, args))} is SPURIOUS: "
                                              f"orig=opt={o} concretely ⇒ rejected (abstraction artifact)")),
                      spurious=True)


def differential_soundness(orig: Callable, opt: Callable, bits: int, nargs: int, trials: int = 256,
                           seed: int = 0) -> KV.Verdict:
    """Spot-check a 'proven equivalent' transform on random concrete inputs. A concrete mismatch ⇒ the proof was
    UNSOUND (correctness bug). All-agree over the trials ⇒ a concrete soundness witness (defense in depth)."""
    rng = random.Random(seed ^ (bits << 8) ^ nargs)
    lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    for _ in range(trials):
        args = [rng.randint(lo, hi) for _ in range(nargs)]
        if _concrete(orig, args, bits) != _concrete(opt, args, bits):
            return KV.decline(f"cegar.soundness: 'proven' transform DIFFERS concretely at {args} ⇒ the proof was "
                              f"UNSOUND (correctness bug surfaced) ⇒ DECLINE", "cegar")
    cert = KV.Cert(KV.EXACT, "differential_soundness", passed=True, check_cost=f"{trials} machine evaluations",
                   detail=f"orig ≡ opt on {trials} random {bits}-bit inputs (concrete spot-check — defense in depth)")
    return KV.exact({"agree_trials": trials}, "cegar.soundness", "concrete soundness spot-check", cert)


def gate_with_solver(orig_bv: Callable, opt_bv: Callable, orig_fn: Callable, opt_fn: Callable,
                     bits: int, argnames: List[str]) -> KV.Verdict:
    """Full gate: ask the in-house bit-blasting SMT whether orig_bv ≡ opt_bv; if it returns a counterexample,
    CONCRETELY gate it; if it proves equivalence, differential-spot-check it. orig_bv/opt_bv take (bb, vars) where
    vars is a dict of SHARED BV variables (created once so both sides reference the SAME inputs); orig_fn/opt_fn
    are the concrete Python semantics for the gate."""
    import bitblast_smt as S

    def build(bb):
        shared = {n: bb.var(n) for n in argnames}            # ★ one variable per name, shared by both sides ★
        return orig_bv(bb, shared), opt_bv(bb, shared)
    r = S.prove_bv_identity(build, bits)
    if r.status == "INVALID":                                # solver found a counterexample → gate it concretely
        g = gate_counterexample(orig_fn, opt_fn, r.model, bits, argnames)
        if g.spurious:
            return KV.decline("cegar: solver counterexample was SPURIOUS (concrete agreement) — inconclusive ⇒ "
                              "DECLINE (do not accept the transform on a spurious refutation)", "cegar")
        return g.verdict                                     # real counterexample → certified DECLINE
    if r.status == "VALID":                                  # solver proved equivalence → defense-in-depth spot-check
        ds = differential_soundness(orig_fn, opt_fn, bits, len(argnames))
        if ds.status != KV.EXACT:
            return ds                                        # unsound "proof" surfaced
        cert = KV.Cert(KV.EXACT, "cegar_verified", passed=True, check_cost="in-house SMT proof + concrete spot-check",
                       detail=f"orig ≡ opt over {bits}-bit (in-house SMT VALID) AND concrete differential agrees ⇒ "
                              f"transform ACCEPTED (sound)")
        return KV.exact({"equivalent": True}, "cegar.gate_with_solver", "verified bitvector transform", cert)
    return KV.decline("cegar: solver inconclusive ⇒ DECLINE (conservative)", "cegar")
