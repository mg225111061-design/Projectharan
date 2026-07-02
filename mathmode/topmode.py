"""
MATH-Ascent §1 — the two TOP-LEVEL modes: CODE and MATH (normal/extend preserved INSIDE each).
=====================================================================================================
CODE = today's engine: take code, emit faster verified code, grade EXACT/PROBABILISTIC/DECLINE. All of OMEGA.
MATH = solve hard mathematics/science/engineering: fold-first (math always has structure), the verified arsenal,
       certificate proving, honest DECLINE where there is no closed form.

The split is UNCONDITIONAL and enforced in code: each top mode routes to a different TOOLSET and a different
default first-move + verifier emphasis, and — critically — the OMEGA §B normal/extend sub-separation (2-tier —
a former third tier, `fast`, retired per §BT-0; its instant-win behaviour lives inside normal's own early-exit)
is preserved verbatim INSIDE each top mode (normal's early-exit never calls Z3; extend is EXACT-only; every tool
is mode-tagged). A per-commit invariant test asserts CODE and MATH route measurably differently AND that the
inner separation holds in both. Blurring fails the build.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List

from pillar3 import mode as M


class TopMode(enum.Enum):
    CODE = "code"
    MATH = "math"


@dataclass(frozen=True)
class TopRoute:
    top_mode: TopMode
    toolset: tuple              # the families of tools this mode dispatches to
    default_first_move: str     # CODE: profile→recognize; MATH: fold (structure-first)
    verifier_emphasis: str      # CODE: behavioural equivalence; MATH: closed-form / proof certificate
    fold_is_central: bool       # MATH uses fold as the default first move, always


# CODE — the optimization toolset (OMEGA lives here): recognizers, lifts, sound analyses, the ADT verifier.
_CODE_TOOLS = ("recognizers", "verified_lifting", "partial_eval", "sound_static_analyses",
               "native_compile", "sketches", "superopt", "z3_translation_validation")
# MATH — the mathematical toolset: fold (central) + the arsenal + the certificate prover.
_MATH_TOOLS = ("fold", "algebra_symbolic", "number_theory", "linear_algebra", "combinatorics_sums",
               "geometry", "logic_verification", "certified_numeric", "optimization_or", "science_engineering")


def route(top_mode: TopMode) -> TopRoute:
    """Route a top-level mode to its toolset + first-move + verifier emphasis. CODE and MATH are disjoint in
    their first move and central tool; their toolsets differ; both preserve the inner normal/extend §B."""
    if top_mode == TopMode.MATH:
        return TopRoute(TopMode.MATH, _MATH_TOOLS, default_first_move="fold",
                        verifier_emphasis="closed-form / certificate", fold_is_central=True)
    return TopRoute(TopMode.CODE, _CODE_TOOLS, default_first_move="profile→recognize",
                    verifier_emphasis="behavioural equivalence", fold_is_central=False)


def inner_modes(top_mode: TopMode) -> List["M.ModePolicy"]:
    """The OMEGA normal/extend sub-modes (2-tier — a former third tier, `fast`, retired), preserved verbatim
    INSIDE the chosen top mode. The §B contract is identical in CODE and MATH: normal=CHEAP_CERT, extend=
    EXACT-or-DECLINE."""
    return [M.ModePolicy.for_mode(m) for m in (M.Mode.NORMAL, M.Mode.EXTEND)]


def routes_differ() -> bool:
    """The CODE/MATH separation invariant (part 1): the two modes route measurably differently."""
    c, m = route(TopMode.CODE), route(TopMode.MATH)
    return (c.toolset != m.toolset and c.default_first_move != m.default_first_move
            and m.fold_is_central and not c.fold_is_central)
