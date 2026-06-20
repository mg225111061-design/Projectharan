"""
Pillar 3 · PHASE M — the verifier-tier ladder + the Z3 invocation counter (Constitution Rules 4 & 5).
=====================================================================================================
The verifier is the *arbiter* — never the proposer (Rule 5). This module encodes the three-rung ladder a
`ModePolicy` selects from, and the single instrument that makes mode separation *checkable*: a global counter
of actual Z3 solver invocations. `fast` must run at tier MICRO and **never invoke Z3** — the counter proves it
(`z3_check_count() == 0` after a fast run). `equiv.prove_equiv` reports every `solver.check()` here, so the
count reflects real SMT work no matter which path reached it.

  • MICRO       — differential test on recorded I/O + probabilistic checks (Freivalds / Schwartz–Zippel
                  spirit). µs-class. NEVER invokes Z3. Never blocks. (fast)
  • CHEAP_CERT  — MICRO + small-region Z3 (bounded translation validation on a *small* region only). (normal)
  • FULL_CERT   — full Z3/SMT translation-validation on every algorithm swap, exhaustive where tractable.
                  EXACT-or-DECLINE lives here. (extend)
"""
from __future__ import annotations

import enum
from typing import Callable, Optional, Tuple


class VerifierTier(enum.IntEnum):
    """Ordered rungs (IntEnum so `policy.verifier_tier >= CHEAP_CERT` is meaningful)."""
    MICRO = 1        # differential + probabilistic, µs-class, NO Z3
    CHEAP_CERT = 2   # + small-region Z3
    FULL_CERT = 3    # full Z3/SMT translation validation


# ── the Z3 invocation counter — the instrument that makes mode separation checkable ───────────────────
_Z3_CHECKS = 0


def note_z3_check() -> None:
    """Called by equiv.prove_equiv on every solver.check(). The honest record of real SMT work."""
    global _Z3_CHECKS
    _Z3_CHECKS += 1


def reset_z3_checks() -> None:
    global _Z3_CHECKS
    _Z3_CHECKS = 0


def z3_check_count() -> int:
    return _Z3_CHECKS


# region size below which CHEAP_CERT will still attempt a (small) Z3 proof
CHEAP_REGION_LIMIT = 6


def tier_allows_certificate(tier: VerifierTier, region_size: int = 1) -> bool:
    """FULL_CERT always; CHEAP_CERT only for a small region; MICRO never (fast never blocks on Z3)."""
    if tier >= VerifierTier.FULL_CERT:
        return True
    if tier == VerifierTier.CHEAP_CERT:
        return region_size <= CHEAP_REGION_LIMIT
    return False


def attempt_certificate(tier: VerifierTier, prove_fn: Optional[Callable[[], "Tuple[bool, Optional[str]]"]],
                        *, region_size: int = 1) -> "Tuple[bool, bool, Optional[str]]":
    """The ONLY gate through which the engine reaches Z3. Returns (attempted, proven, counterexample_or_reason).
    If the tier forbids a certificate (MICRO, or CHEAP_CERT on a too-large region), Z3 is NOT invoked — the
    counter stays put — and we report (attempted=False) so the caller falls back to a differential grade."""
    if prove_fn is None:
        return (False, False, "no proof available")
    if not tier_allows_certificate(tier, region_size):
        return (False, False, f"tier {tier.name} below certificate (region={region_size}) — differential only")
    proven, cex = prove_fn()                       # prove_fn (equiv.prove_equiv) increments the Z3 counter
    return (True, bool(proven), cex)
