"""Mechanism 6 — RENORMALIZE to a FIXPOINT (RG fixed point + critical exponents, multigrid/AMG convergence,
abstract interpretation Kleene/Tarski fixpoint + widening). Output: fixpoint + convergence/critical bound.
Closely related to M13 (Kleene fixpoint) — M6 is the *scale/coarsening* specialization."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "fixpoint" in f.tags:
        s += 0.5
    if "physics" in f.tags and "renormaliz" in f.text:
        s += 0.4
    if "loop" in f.tags:
        s += 0.1
    return min(1.0, s)


def _apply(x, **kw):
    """M6 renormalize / coarse-grain to a fixpoint. WIRED (native, zero-dep): exact Markov lumping
    ({"markov":P,"partition":B} → strong-lumpability EXACT coarse-graining + lumped stationary) and multigrid/Jacobi
    linear solve ({"linsolve":A,"b":b} → residual-enclosure fixpoint). Non-lumpable / non-convergent ⇒ DECLINE;
    full RG of a critical field theory remains out of scope (honest defer for unstructured operators)."""
    if isinstance(x, dict) and (("markov" in x and "partition" in x) or ("linsolve" in x and "b" in x)):
        import renormalize
        return renormalize.m6_grade(x)
    return honest_defer("M6.renormalize_fixpoint",
                        "wired for {markov,partition} exact lumping and {linsolve,b} multigrid; general RG / "
                        "critical-exponent flow of an unstructured operator deferred")


MECHANISM = Mechanism(
    num=6, name="renormalize_fixpoint", probe=_probe, apply=_apply,
    cert_kinds=("fixpoint_inductive", "contraction_bound", "critical_exponent"),
    contract="requires a scale-invariant flow or a monotone lattice iteration; ensures a (post-)fixpoint with an "
            "inductiveness check or a contraction factor; grade EXACT (inductive) else PROBABILISTIC",
    composable_with=(13,),
)
