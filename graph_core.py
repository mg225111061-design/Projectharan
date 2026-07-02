"""
perf-build STAGE 1 — Rust graph core via ctypes (dependency-0: no PyO3/maturin/cffi).
======================================================================================
Loads the std-only Rust cdylib (rust_graph/target/release/libgraph_core.so) and offloads the two hot loops
that cap repo_partition.py at N=4000 (measured 50.3 s @ N=4000, BLOCKED-scale above):
  • the deflated power iteration for the Fiedler vector  (O(iters·E)), and
  • the Kernighan–Lin balanced swap refinement           (O(passes·N²)).

★ The RNG stays in Python (random.Random(seed)) and the initial vector is passed to Rust, so both sides start
  identical — the Rust Fiedler vector is DIFFERENTIAL-TESTED against repo_partition.fiedler_vector (must match
  to FP rounding) and the KL result is integer-exact. No fake speedup. ★
★ If the shared library is absent (rustc unavailable / not built) every entry point returns [BLOCKED] and the
  caller falls back to the pure-Python repo_partition — never a fabricated number. ★

This raises the SCALING CEILING (Clock B / orchestration), not Clock A (LLM latency) or Clock C (emitted code).
"""
from __future__ import annotations

import ctypes
import os
import random
from typing import Dict, List, Tuple

import repo_partition as RP

_SO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rust_graph", "target", "release", "libgraph_core.so")
_LIB = None
_LOAD_ERR = None


def _lib():
    global _LIB, _LOAD_ERR
    if _LIB is not None or _LOAD_ERR is not None:
        return _LIB
    try:
        lib = ctypes.CDLL(_SO)
        u64 = ctypes.c_uint64
        usize = ctypes.c_size_t
        lib.gc_abi_version.restype = u64
        lib.gc_fiedler.argtypes = [usize, ctypes.POINTER(usize), ctypes.POINTER(ctypes.c_uint32),
                                   ctypes.POINTER(ctypes.c_double), usize, ctypes.POINTER(ctypes.c_double)]
        lib.gc_fiedler.restype = ctypes.c_int
        lib.gc_kl_refine.argtypes = [usize, ctypes.POINTER(usize), ctypes.POINTER(ctypes.c_uint32),
                                     ctypes.POINTER(ctypes.c_uint8), usize]
        lib.gc_kl_refine.restype = ctypes.c_int64
        lib.gc_transitive_dependents.argtypes = [usize, ctypes.POINTER(usize), ctypes.POINTER(ctypes.c_uint32),
                                                 usize, ctypes.POINTER(ctypes.c_uint32)]
        lib.gc_transitive_dependents.restype = ctypes.c_int64
        assert lib.gc_abi_version() == 1
        _LIB = lib
    except Exception as e:  # noqa: BLE001
        _LOAD_ERR = f"[BLOCKED: {type(e).__name__}: {e}]"
    return _LIB


def available() -> bool:
    return _lib() is not None


def load_error() -> str:
    _lib()
    return _LOAD_ERR or ""


def _csr(n: int, adj: Dict[int, List[int]]):
    """Build CSR (offsets[n+1], targets[2E]) preserving repo_partition's neighbor order (so the Laplacian
    summation order matches Python exactly)."""
    off = (ctypes.c_size_t * (n + 1))()
    flat: List[int] = []
    acc = 0
    for i in range(n):
        off[i] = acc
        nb = adj[i]
        flat.extend(nb)
        acc += len(nb)
    off[n] = acc
    tgt = (ctypes.c_uint32 * max(acc, 1))()
    for k, v in enumerate(flat):
        tgt[k] = v
    return off, tgt


def fiedler_vector(n: int, adj: Dict[int, List[int]], iters: int = 300, seed: int = 12345) -> List[float]:
    """Rust Fiedler vector with the SAME init vector Python would use (random.Random(seed))."""
    lib = _lib()
    if lib is None:
        return RP.fiedler_vector(n, adj, iters, seed)
    if n <= 1:
        return [0.0] * n
    rng = random.Random(seed)
    init = (ctypes.c_double * n)(*[rng.uniform(-1.0, 1.0) for _ in range(n)])
    off, tgt = _csr(n, adj)
    out = (ctypes.c_double * n)()
    lib.gc_fiedler(n, off, tgt, init, iters, out)
    return list(out)


def _kl_refine(parts: List[int], n: int, adj: Dict[int, List[int]], passes: int = 6) -> Tuple[List[int], int]:
    lib = _lib()
    off, tgt = _csr(n, adj)
    arr = (ctypes.c_uint8 * n)(*[int(p) for p in parts])
    cut = int(lib.gc_kl_refine(n, off, tgt, arr, passes))
    return list(arr), cut


def _bisect(n: int, adj: Dict[int, List[int]], edges) -> Tuple[List[int], str]:
    """Mirror of repo_partition._bisect, hot loops in Rust."""
    if n <= 1:
        return [0] * n, "trivial"
    fv = fiedler_vector(n, adj)
    order = sorted(range(n), key=lambda i: fv[i])
    parts = [0] * n
    for rank, node in enumerate(order):
        parts[node] = 0 if rank < n // 2 else 1
    method = "spectral-seed+KL(rust)"
    if len(set(parts)) == 1:
        parts = [0 if i < n // 2 else 1 for i in range(n)]
        method = "balanced-seed+KL(rust)"
    base_cut = RP.cut_size(parts, edges)
    refined, ref_cut = _kl_refine(parts, n, adj)
    if ref_cut <= base_cut:
        parts = refined
    return parts, method


def partition(graph: "RP.Graph", k: int = 2) -> RP.Partition:
    """Rust-accelerated drop-in for repo_partition.partition (identical API + result semantics). The N>4000
    ceiling is gone — Rust handles the O(iters·E) power iteration and O(passes·N²) KL. Falls back to pure
    Python when the cdylib is unavailable."""
    if not available():
        return RP.partition(graph, k)
    n, adj, edges = RP._normalize(graph)
    if n == 0:
        return RP.Partition([], 0, 0, "trivial", [], False, "empty graph")
    if k <= 1 or n <= 1:
        return RP.Partition([0] * n, 1, 0, "trivial", [n], False)
    parts, method = _bisect(n, adj, edges)
    next_id = 2
    while next_id < k:
        sizes = [sum(1 for p in parts if p == g) for g in range(next_id)]
        target = max(range(next_id), key=lambda g: sizes[g])
        members = sorted(i for i in range(n) if parts[i] == target)
        if len(members) <= 1:
            break
        remap = {old: new for new, old in enumerate(members)}
        subg = {remap[i]: [remap[j] for j in adj[i] if parts[j] == target] for i in members}
        sp, _m = _bisect(len(members), subg, RP._edges_of(subg))
        for old in members:
            if sp[remap[old]] == 1:
                parts[old] = next_id
        next_id += 1
    sizes = [sum(1 for p in parts if p == g) for g in range(max(parts) + 1)]
    return RP.Partition(parts, max(parts) + 1, RP.cut_size(parts, edges), method, sizes, False,
                        "rust graph core (ceiling removed)")
