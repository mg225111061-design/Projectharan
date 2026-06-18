"""
v27 STAGE 16 (lever 1) — type-constrained decoding: prune ill-typed tokens AS THEY ARE GENERATED.
==================================================================================================
A grammar/type automaton masks the next-token set so that only choices keeping a WELL-TYPED parse alive
are allowed. The model still chooses *among* the legal tokens (we never override its ranking) — we only
remove tokens that would guarantee a compile/type error. Net effect (measured below): the well-typed rate
of generated programs goes to 100% by construction, vs a fraction for unconstrained sampling.

Demonstrated on a small typed expression language with an Int target:
  operands  = int literals / Int vars / '('         (a Bool var is PRUNED here — wrong type for an Int slot)
  operators = '+' '*' / ')' (if open) / END          ('<' and '&' are PRUNED — they would yield Bool ≠ Int)
The mask is a left-to-right OPERAND/OPERATOR state machine + paren depth; every accepted string parses and
type-checks to Int. We MEASURE the well-typed rate of constrained vs unconstrained generation on the same
mock token-proposer (no LLM/key needed — the LLM only supplies a ranking we filter).

★ HONEST (§1.9, §5.9) ★: this is a heuristic *accuracy lever*, not a guarantee — it removes TYPE errors,
NOT logic errors. The correctness guarantee remains the write→verify→fix verifier. A live-LLM accuracy
delta needs a key/egress ([BLOCKED] here); the measurable, key-free claim is the well-typed-rate lift.
"""
from __future__ import annotations

import ast
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

INT_VARS = {"x", "y"}
BOOL_VARS = {"b"}
INT_LITS = {"1", "2"}
ARITH = {"+", "*"}          # Int × Int → Int
CMP = {"<"}                 # Int × Int → Bool   (illegal in an Int slot)
BOOLOP = {"&"}              # Bool × Bool → Bool (illegal in an Int slot)
LP, RP, END = "(", ")", "<END>"
VOCAB: List[str] = sorted(INT_VARS | BOOL_VARS | INT_LITS | ARITH | CMP | BOOLOP | {LP, RP})


# ── the type checker (uses Python's parser for the grammar/balance, a type walk for typing) ─────────
def welltyped_int(tokens: List[str]) -> bool:
    """True iff `tokens` parse as a balanced expression AND type-check to Int."""
    if not tokens:
        return False
    expr = " ".join("and" if t == "&" else t for t in tokens)
    try:
        tree = ast.parse(expr, mode="eval").body
    except SyntaxError:
        return False

    def typ(n) -> Optional[str]:
        if isinstance(n, ast.Constant):
            return "Int" if isinstance(n.value, int) and not isinstance(n.value, bool) else None
        if isinstance(n, ast.Name):
            return "Int" if n.id in INT_VARS else ("Bool" if n.id in BOOL_VARS else None)
        if isinstance(n, ast.BinOp) and type(n.op).__name__ in ("Add", "Mult"):
            return "Int" if typ(n.left) == "Int" and typ(n.right) == "Int" else None
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.Lt):
            return "Bool" if typ(n.left) == "Int" and typ(n.comparators[0]) == "Int" else None
        if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.And):
            return "Bool" if all(typ(v) == "Bool" for v in n.values) else None
        return None
    return typ(tree) == "Int"


# ── the type-constrained next-token mask (left-to-right state machine) ───────────────────────────────
@dataclass
class _State:
    mode: str = "OPERAND"   # OPERAND (need an Int operand) | OPERATOR (need an op / close / end)
    depth: int = 0


def _step(st: _State, tok: str) -> Optional[_State]:
    if st.mode == "OPERAND":
        if tok in INT_VARS or tok in INT_LITS:
            return _State("OPERATOR", st.depth)
        if tok == LP:
            return _State("OPERAND", st.depth + 1)
        return None
    # OPERATOR
    if tok in ARITH:
        return _State("OPERAND", st.depth)
    if tok == RP and st.depth > 0:
        return _State("OPERATOR", st.depth - 1)
    if tok == END and st.depth == 0:
        return _State("OPERATOR", st.depth)
    return None


def valid_next_tokens(prefix: List[str]) -> Set[str]:
    """The type-valid next tokens after `prefix` for an Int-typed expression (ill-typed ones are pruned)."""
    st = _State()
    for t in prefix:
        nxt = _step(st, t)
        if nxt is None:
            return set()            # prefix already dead — nothing valid
        st = nxt
    return {t for t in VOCAB + [END] if _step(st, t) is not None}


# ── generation: constrained (mask) vs unconstrained (raw), and the measured well-typed rate ─────────
def constrained_generate(rng: random.Random, max_len: int = 12) -> List[str]:
    """Sample only from the type-valid mask, then FORCE-COMPLETE (supply a pending operand, close open
    parens) so the result is well-typed Int BY CONSTRUCTION."""
    out: List[str] = []
    st = _State()
    while len(out) < max_len:
        if st.mode == "OPERATOR" and st.depth == 0 and out and rng.random() < 0.35:
            return out                                   # legal stopping point (Int, balanced)
        choices = sorted(valid_next_tokens(out) - {END})
        if not choices:
            break
        tok = rng.choice(choices)
        out.append(tok)
        st = _step(st, tok)
    if st.mode == "OPERAND":                              # pending operand → supply one
        out.append(rng.choice(sorted(INT_VARS | INT_LITS)))
        st = _State("OPERATOR", st.depth)
    while st.depth > 0:                                  # close any open parens
        out.append(RP)
        st = _State("OPERATOR", st.depth - 1)
    return out


def unconstrained_generate(rng: random.Random, max_len: int = 12) -> List[str]:
    n = rng.randint(1, max_len)
    return [rng.choice(VOCAB) for _ in range(n)]


def measure_welltyped_rate(n: int = 2000, seed: int = 7) -> Dict[str, float]:
    """Measure the well-typed (compile-success) rate of constrained vs unconstrained generation."""
    rng = random.Random(seed)
    con = sum(1 for _ in range(n) if welltyped_int(constrained_generate(rng)))
    rng = random.Random(seed)
    unc = sum(1 for _ in range(n) if welltyped_int(unconstrained_generate(rng)))
    con_rate, unc_rate = con / n, unc / n
    err_before, err_after = 1 - unc_rate, 1 - con_rate
    reduction = (err_before - err_after) / err_before if err_before > 0 else 0.0
    return {"constrained_welltyped": con_rate, "unconstrained_welltyped": unc_rate,
            "compile_error_reduction": reduction, "n": n}
