"""
NATIVE-CORE §1 — Rust core via ctypes (dependency-0: no PyO3/maturin/cffi/flint/faer).
=======================================================================================
Loads the std-only Rust cdylib (rust_core/target/release/libharan_core.so) through ctypes and exposes the
pieces the v34 Rust stage deferred:

  • a flat **arena AST** evaluated in one deterministic pass (children-before-parents);
  • a **deterministic fixed-precision multimodular (CRT) ring** — evaluate the arena under a FIXED ordered prime
    basis, then Garner-combine the residues into the EXACT integer (native big-uint). EXACT while |value| ≤
    (M−1)/2  (M = ∏ basis primes ≈ 2^124); that bound is the "fixed precision";
  • **rational reconstruction** (bounded extended Euclid);
  • a **deterministic fixed-reduction-order** batched modular dot product (the "SIMD" demonstrator).

Every Rust result is DIFFERENTIAL-TESTED bit-exact against the pure-Python reference here (CPython's arbitrary-
precision int is the ground truth). The native path NEVER changes a grade — it changes runtime only — and where
there is no measured speed crossover the speed claim is honestly UNVERIFIED (Python int is C-fast); CORRECTNESS
(exact, deterministic, bounded-exhaustively verified) is the verified deliverable. If the lib is absent every
entry point degrades to the Python reference / [BLOCKED] — no fabricated number.
"""
from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# fixed ordered basis — MUST match rust_core/src/lib.rs PRIMES (asserted against the lib at load).
PRIMES: List[int] = [2_147_483_647, 2_147_483_629, 2_147_483_587, 2_147_483_563]
M_TOTAL = 1
for _p in PRIMES:
    M_TOTAL *= _p
MAX_ABS = (M_TOTAL - 1) // 2          # the fixed-precision exact bound: |value| ≤ MAX_ABS ⇒ EXACT

_SO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rust_core", "target", "release", "libharan_core.so")
_LIB = None
_LOAD_ERR: Optional[str] = None


def _lib():
    global _LIB, _LOAD_ERR
    if _LIB is not None or _LOAD_ERR is not None:
        return _LIB
    try:
        lib = ctypes.CDLL(_SO)
        lib.rc_num_primes.restype = ctypes.c_uint64
        lib.rc_prime.argtypes = [ctypes.c_size_t]
        lib.rc_prime.restype = ctypes.c_uint64
        lib.rc_eval_residues.argtypes = [
            ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_int64), ctypes.c_size_t, ctypes.POINTER(ctypes.c_uint64)]
        lib.rc_eval_residues.restype = ctypes.c_int32
        lib.rc_crt_combine.argtypes = [ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint32),
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_uint8)]
        lib.rc_crt_combine.restype = ctypes.c_int32
        lib.rc_dot_modp.argtypes = [ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64),
                                    ctypes.c_size_t, ctypes.c_uint64]
        lib.rc_dot_modp.restype = ctypes.c_uint64
        lib.rc_rational_reconstruct.argtypes = [ctypes.c_uint64, ctypes.c_uint64,
                                                ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int64)]
        lib.rc_rational_reconstruct.restype = ctypes.c_int32
        # the lib's basis must match ours exactly (no silent drift)
        assert lib.rc_num_primes() == len(PRIMES), "basis size mismatch"
        for i, p in enumerate(PRIMES):
            assert lib.rc_prime(i) == p, f"basis[{i}] mismatch: lib {lib.rc_prime(i)} vs py {p}"
        _LIB = lib
    except Exception as e:  # noqa: BLE001
        _LOAD_ERR = f"[BLOCKED: {type(e).__name__}: {e}]"
    return _LIB


def available() -> bool:
    return _lib() is not None


# ── flat arena AST (op, arg, lhs, rhs); nodes topologically ordered, root last ──────────────────────────────
# opcodes: 0=CONST(arg=value) 1=VAR(arg=index) 2=NEG(lhs) 3=ADD(lhs,rhs) 4=SUB(lhs,rhs) 5=MUL(lhs,rhs)
class Expr:
    __slots__ = ("op", "arg", "a", "b")

    def __init__(self, op, arg=0, a=None, b=None):
        self.op, self.arg, self.a, self.b = op, arg, a, b


def Const(v: int) -> Expr: return Expr(0, v)
def Var(i: int) -> Expr: return Expr(1, i)
def Neg(a: Expr) -> Expr: return Expr(2, 0, a)
def Add(a: Expr, b: Expr) -> Expr: return Expr(3, 0, a, b)
def Sub(a: Expr, b: Expr) -> Expr: return Expr(4, 0, a, b)
def Mul(a: Expr, b: Expr) -> Expr: return Expr(5, 0, a, b)


def to_arena(root: Expr) -> Tuple[List[int], List[int], List[int], List[int]]:
    """Flatten the tree to parallel arrays in a children-before-parents order (a single forward eval pass)."""
    ops: List[int] = []
    args: List[int] = []
    lhs: List[int] = []
    rhs: List[int] = []
    memo = {}

    def emit(e: Expr) -> int:
        if id(e) in memo:
            return memo[id(e)]
        li = ri = 0
        if e.a is not None:
            li = emit(e.a)
        if e.b is not None:
            ri = emit(e.b)
        idx = len(ops)
        ops.append(e.op); args.append(e.arg); lhs.append(li); rhs.append(ri)
        memo[id(e)] = idx
        return idx

    emit(root)
    return ops, args, lhs, rhs


def eval_true(root: Expr, vars: List[int]) -> int:
    """Ground truth: exact arbitrary-precision integer value (CPython int)."""
    def ev(e: Expr) -> int:
        if e.op == 0: return e.arg
        if e.op == 1: return vars[e.arg]
        if e.op == 2: return -ev(e.a)
        if e.op == 3: return ev(e.a) + ev(e.b)
        if e.op == 4: return ev(e.a) - ev(e.b)
        if e.op == 5: return ev(e.a) * ev(e.b)
        raise ValueError(e.op)
    return ev(root)


# ── Python references (the differential ground truth) ───────────────────────────────────────────────────────
def py_residues(value: int) -> List[int]:
    return [value % p for p in PRIMES]


def py_crt(residues: List[int]) -> int:
    """CRT to [0, M) then map into the symmetric range (−(M−1)/2 … (M−1)/2] — matches the Rust convention."""
    x = 0
    for r, p in zip(residues, PRIMES):
        mi = M_TOTAL // p
        x += (r % p) * mi * pow(mi, -1, p)
    x %= M_TOTAL
    return x - M_TOTAL if x > MAX_ABS else x


def py_rational_reconstruct(r: int, m: int) -> Optional[Tuple[int, int]]:
    nbound = 0
    while (nbound + 1) * (nbound + 1) <= m // 2:
        nbound += 1
    r0, r1 = m, r % m
    s0, s1 = 0, 1
    while r1 > nbound and r1 != 0:
        q = r0 // r1
        r0, r1, s0, s1 = r1, r0 - q * r1, s1, s0 - q * s1
    num, den = r1, s1
    if den < 0:
        num, den = -num, -den
    if den == 0 or den > nbound or abs(num) > nbound:
        return None
    if num % m != (den * r) % m:
        return None
    return num, den


# ── Rust entry points (None / fall back when the lib is absent) ─────────────────────────────────────────────
def rust_residues(arena, vars: List[int]) -> Optional[List[int]]:
    lib = _lib()
    if lib is None:
        return None
    ops, args, lhs, rhs = arena
    n = len(ops)
    c_ops = (ctypes.c_uint8 * n)(*ops)
    c_args = (ctypes.c_int64 * n)(*args)
    c_lhs = (ctypes.c_uint32 * n)(*lhs)
    c_rhs = (ctypes.c_uint32 * n)(*rhs)
    c_vars = (ctypes.c_int64 * max(1, len(vars)))(*(vars or [0]))
    out = (ctypes.c_uint64 * len(PRIMES))()
    rc = lib.rc_eval_residues(c_ops, c_args, c_lhs, c_rhs, n, c_vars, len(vars), out)
    if rc != 0:
        return None
    return [out[i] for i in range(len(PRIMES))]


def rust_crt_combine(residues: List[int]) -> Optional[int]:
    lib = _lib()
    if lib is None:
        return None
    cap = 8
    c_res = (ctypes.c_uint64 * len(PRIMES))(*[r % p for r, p in zip(residues, PRIMES)])
    out = (ctypes.c_uint32 * cap)()
    neg = ctypes.c_uint8(0)
    nl = lib.rc_crt_combine(c_res, out, cap, ctypes.byref(neg))
    if nl < 0:
        return None
    val = 0
    for i in range(nl):
        val |= out[i] << (32 * i)
    return -val if neg.value else val


def rust_dot_modp(a: List[int], b: List[int], p: int) -> Optional[int]:
    lib = _lib()
    if lib is None:
        return None
    n = len(a)
    ca = (ctypes.c_uint64 * n)(*[x % p for x in a])
    cb = (ctypes.c_uint64 * n)(*[x % p for x in b])
    return int(lib.rc_dot_modp(ca, cb, n, p))


def rust_rational_reconstruct(r: int, m: int) -> Optional[Tuple[int, int]]:
    lib = _lib()
    if lib is None:
        return None
    num = ctypes.c_int64(0)
    den = ctypes.c_int64(0)
    ok = lib.rc_rational_reconstruct(r % m, m, ctypes.byref(num), ctypes.byref(den))
    return (num.value, den.value) if ok else None


# ── verification: differential + bounded-exhaustive ─────────────────────────────────────────────────────────
def differential_test(trials: int = 200, seed: int = 7) -> bool:
    """Rust ≡ Python (bit-exact) on random arenas + var assignments, on CRT combine, on dot, on rational recon.
    Requires the lib (call available() first)."""
    import random
    if not available():
        return False
    rng = random.Random(seed)

    def rand_expr(depth: int) -> Expr:
        if depth == 0 or rng.random() < 0.3:
            return Const(rng.randint(-50, 50)) if rng.random() < 0.5 else Var(rng.randint(0, 2))
        op = rng.choice([2, 3, 4, 5])
        if op == 2:
            return Neg(rand_expr(depth - 1))
        return {3: Add, 4: Sub, 5: Mul}[op](rand_expr(depth - 1), rand_expr(depth - 1))

    for _ in range(trials):
        root = rand_expr(rng.randint(1, 4))
        vars = [rng.randint(-30, 30) for _ in range(3)]
        true_v = eval_true(root, vars)
        if abs(true_v) > MAX_ABS:      # stay inside the fixed-precision bound (random small exprs always do)
            continue
        arena = to_arena(root)
        rres = rust_residues(arena, vars)
        if rres != py_residues(true_v):
            return False
        if rust_crt_combine(rres) != true_v or py_crt(rres) != true_v:
            return False
    # dot product (fixed-order, mod a basis prime)
    for _ in range(20):
        n = rng.randint(1, 64)
        a = [rng.randrange(1 << 40) for _ in range(n)]
        b = [rng.randrange(1 << 40) for _ in range(n)]
        p = rng.choice(PRIMES)
        if rust_dot_modp(a, b, p) != sum((x % p) * (y % p) for x, y in zip(a, b)) % p:
            return False
    # rational reconstruction round-trip
    for _ in range(40):
        q = rng.randint(1, 40)
        num = rng.randint(-40, 40)
        from math import gcd
        if gcd(abs(num), q) != 1:
            continue
        m = PRIMES[0]
        r = (num * pow(q, -1, m)) % m
        if rust_rational_reconstruct(r, m) != py_rational_reconstruct(r, m):
            return False
    return True


def exhaustive_crt_roundtrip(window: int = 4096) -> dict:
    """EXACT-within-bound evidence: every integer v in [−window, window] round-trips residues→CRT→v EXACTLY,
    AND the symmetric wrap is exactly at ±MAX_ABS (boundary cases checked). Bounded-exhaustive ⇒ EXACT on the
    swept domain; the stated precision bound is |v| ≤ MAX_ABS. Uses Rust when available, else the Python ring."""
    use_rust = available()
    combine = rust_crt_combine if use_rust else py_crt
    bad = 0
    for v in range(-window, window + 1):
        if combine(py_residues(v)) != v:
            bad += 1
    # boundary: ±MAX_ABS representable; the symmetric fold is exact at the half-modulus
    boundary_ok = (combine(py_residues(MAX_ABS)) == MAX_ABS and
                   combine(py_residues(-MAX_ABS)) == -MAX_ABS)
    return {"window": window, "swept": 2 * window + 1, "mismatches": bad, "boundary_ok": boundary_ok,
            "backend": "rust" if use_rust else "python", "max_abs_bits": MAX_ABS.bit_length()}


def exhaustive_arena_equiv() -> dict:
    """FORMAL / exhaustive-bounded equivalence to spec: enumerate EVERY arena over a tiny grammar (atoms =
    consts −3..3 and vars 0,1; plus Neg(atom) and every binary op(atom, atom)) and EVERY var assignment in
    [−3,3]², and assert the Rust multimodular eval + CRT combine equals the exact Python value on all of them.
    A finite, fully-swept domain ⇒ equivalence is EXACT on that domain (not sampled). Rust when available."""
    if not available():
        return {"backend": "python", "checks": 0, "mismatches": 0, "note": "lib absent"}
    atoms = [Const(c) for c in range(-3, 4)] + [Var(0), Var(1)]
    exprs: List[Expr] = list(atoms)
    exprs += [Neg(x) for x in atoms]
    for f in (Add, Sub, Mul):
        for x in atoms:
            for y in atoms:
                exprs.append(f(x, y))
    assigns = [[v0, v1] for v0 in range(-3, 4) for v1 in range(-3, 4)]
    checks = mism = 0
    for e in exprs:
        arena = to_arena(e)
        for vs in assigns:
            true_v = eval_true(e, vs)
            checks += 1
            if rust_crt_combine(rust_residues(arena, vs)) != true_v:
                mism += 1
    return {"backend": "rust", "expressions": len(exprs), "assignments": len(assigns),
            "checks": checks, "mismatches": mism}


@dataclass
class CoreMeasurement:
    status: str                       # OK | BLOCKED
    differential_ok: bool = False
    crt_exact_ok: bool = False
    rust_ms: float = 0.0
    python_ms: float = 0.0
    speedup: float = 0.0
    crossover: bool = False
    detail: str = ""
    note: str = ""


def measure(iters: int = 20000, seed: int = 1) -> CoreMeasurement:
    """[Clock B/C] multimodular eval+CRT: Rust vs the Python ring, with the differential + exhaustive checks.
    Honest: CPython int is C-fast and ctypes has call overhead, so at this granularity a speed WIN is not
    expected — if there is no crossover we say so (speed UNVERIFIED), CORRECTNESS is the deliverable. [BLOCKED]
    if the lib is unavailable — never a fabricated number."""
    import time
    if not available():
        return CoreMeasurement("BLOCKED", detail=_LOAD_ERR or "libharan_core.so not built",
                               note="Python ring is the verified fallback (exact, deterministic)")
    diff = differential_test()
    rt = exhaustive_crt_roundtrip(2048)
    crt_ok = rt["mismatches"] == 0 and rt["boundary_ok"]
    # a representative arena: ((a*b) - c)*(a + 7)  with 3 vars
    root = Mul(Sub(Mul(Var(0), Var(1)), Var(2)), Add(Var(0), Const(7)))
    arena = to_arena(root)
    vars = [123456, -98765, 4242]
    t = time.perf_counter()
    for _ in range(iters):
        rust_crt_combine(rust_residues(arena, vars))
    rust_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    for _ in range(iters):
        py_crt(py_residues(eval_true(root, vars)))
    python_ms = (time.perf_counter() - t) * 1000
    speedup = round(python_ms / rust_ms, 2) if rust_ms > 0 else 0.0
    crossover = speedup > 1.0
    note = ("Rust faster at this granularity" if crossover else
            "no crossover (ctypes overhead vs C-fast CPython int) — speed UNVERIFIED; correctness is the deliverable")
    return CoreMeasurement("OK", diff, crt_ok, round(rust_ms, 2), round(python_ms, 2), speedup, crossover,
                           detail=f"multimodular eval+CRT ×{iters} (4-prime basis, {MAX_ABS.bit_length()}-bit bound)",
                           note=note)
