"""
§AQ §5.OFFSET — buffer/page offsets, serialization sizes, TCP sequence numbers = linear / telescoping / modular, z3.
================================================================================================================
`offset = i·CHUNK` (linear, z3 LIA); fixed-record serialization size `n·recordSize` and `Σ fieldᵢ_size` (telescoping);
TCP `seq = (seq + len) mod 2³²` (modular linear, z3 BV). ★REDUCE to the existing linear / telescoping / modular
mechanisms (S-1). All are pure arithmetic FRAMED OFF the surrounding I/O (§5 frame rule).
"""
from __future__ import annotations


def prove_offset_linear(CHUNK: int = 4096, N: int = 5, correct: bool = True) -> bool:
    """z3 LIA: the running offset (offset += CHUNK, N times) == N·CHUNK. WRONG: (N+1)·CHUNK ⇒ SAT."""
    import z3
    off = z3.IntVal(0)
    for _ in range(N):
        off = off + CHUNK
    closed = (N if correct else N + 1) * CHUNK
    sol = z3.Solver(); sol.add(off != closed)
    return sol.check() == z3.unsat


def prove_serialize_telescoping(n: int = 4, correct: bool = True) -> bool:
    """z3 LIA: total size Σ fieldᵢ over n fields == the telescoping sum. WRONG drops the last field ⇒ SAT."""
    import z3
    fs = [z3.Int(f"s{i}") for i in range(n)]
    total = z3.IntVal(0)
    for s in fs:
        total = total + s
    closed = z3.Sum(fs if correct else fs[:-1])
    sol = z3.Solver(); sol.add(total != closed)
    return sol.check() == z3.unsat


def prove_tcp_seq_modular(width: int = 32, steps: int = 3, correct: bool = True) -> bool:
    """z3 BV: seq = (seq + len) mod 2ʷ over `steps` segments == (seq₀ + Σ lenᵢ) mod 2ʷ. WRONG uses a + that ignores one
    len ⇒ SAT."""
    import z3
    lens = [z3.BitVec(f"l{i}", width) for i in range(steps)]
    seq0 = z3.BitVec("seq0", width)
    seq = seq0
    for l in lens:
        seq = seq + l                                            # BV add wraps mod 2^w
    closed = seq0 + z3.Sum(lens if correct else lens[:-1])
    sol = z3.Solver(); sol.add(seq != closed)
    return sol.check() == z3.unsat


def adversarial_battery() -> dict:
    """★ buffer offset (linear), serialization size (telescoping), TCP seq (modular BV) z3-proven ≡ their closed forms
    (⇒ existing mechanisms); ★★ a wrong variant of each is z3-REFUTED."""
    cases = {
        "offset_linear": prove_offset_linear(4096, 5, True),
        "serialize_telescoping": prove_serialize_telescoping(4, True),
        "tcp_seq_modular": prove_tcp_seq_modular(32, 3, True),
        "offset_wrong_refuted": not prove_offset_linear(4096, 5, False),       # ★★
        "serialize_wrong_refuted": not prove_serialize_telescoping(4, False),  # ★★
        "tcp_wrong_refuted": not prove_tcp_seq_modular(32, 3, False),          # ★★
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
