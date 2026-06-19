//! perf-build STAGE 1 — Rust graph core (zero-dep, std-only, ctypes ABI).
//! ===========================================================================================
//! Faithful Rust mirror of repo_partition.py's two hot loops, which cap the Python orchestrator at
//! MAX_PRACTICAL_N = 4000 (measured: 50.3 s at N=4000, BLOCKED-scale above):
//!   - `gc_fiedler`   : deflated power iteration on M = cI − L  → the Fiedler vector (O(iters·E)).
//!   - `gc_kl_refine` : Kernighan–Lin balanced swap refinement   → the cut (O(passes·N²)).
//!
//! Faithfulness (so the result is DIFFERENTIAL-TESTED against Python, never a fake speedup):
//!   * The initial random vector is generated in PYTHON (random.Random(seed)) and passed in, so both
//!     sides start from the identical vector — the power iteration then matches to within FP rounding.
//!   * The Laplacian sum uses the SAME neighbor order Python passes (no reordering), so the arithmetic
//!     matches; deflation (subtract mean, L2-normalize) and the drift convergence test mirror Python.
//!   * KL gains are integer counts (exact). Node gains are precomputed once per pass — semantically
//!     identical to Python (parts are not mutated mid-pass), it just removes Python's redundant recompute.
//!   * Tie-breaking matches: zeros/ones in ascending index order, first STRICTLY-greater gain wins.
//! Graph = CSR (offsets[n+1], targets[2E]); each undirected edge appears in both directions.

use std::slice;

unsafe fn csr<'a>(n: usize, off: *const usize, tgt: *const u32) -> (&'a [usize], &'a [u32]) {
    let off = slice::from_raw_parts(off, n + 1);
    let tgt = slice::from_raw_parts(tgt, off[n]);
    (off, tgt)
}

/// Subtract the mean, then L2-normalize (zero norm → 1.0). Mirrors repo_partition.fiedler_vector.deflate,
/// including summation order (index 0..n).
fn deflate(v: &mut [f64]) {
    let n = v.len() as f64;
    let mut s = 0.0;
    for &vi in v.iter() {
        s += vi;
    }
    let m = s / n;
    for vi in v.iter_mut() {
        *vi -= m;
    }
    let mut nrm = 0.0;
    for &vi in v.iter() {
        nrm += vi * vi;
    }
    nrm = nrm.sqrt();
    if nrm == 0.0 {
        nrm = 1.0;
    }
    for vi in v.iter_mut() {
        *vi /= nrm;
    }
}

/// Fiedler vector by deflated power iteration on M = cI − L (c = 2·d_max + 1 ≥ λ_max(L)).
/// `init` is the raw random vector (from Python). Writes the converged vector into `out`.
#[no_mangle]
pub extern "C" fn gc_fiedler(
    n: usize,
    off: *const usize,
    tgt: *const u32,
    init: *const f64,
    iters: usize,
    out: *mut f64,
) -> i32 {
    if n == 0 {
        return 0;
    }
    let (off, tgt) = unsafe { csr(n, off, tgt) };
    let out = unsafe { slice::from_raw_parts_mut(out, n) };
    if n == 1 {
        out[0] = 0.0;
        return 0;
    }
    let init = unsafe { slice::from_raw_parts(init, n) };
    let mut maxdeg = 0usize;
    for i in 0..n {
        let d = off[i + 1] - off[i];
        if d > maxdeg {
            maxdeg = d;
        }
    }
    let c = 2.0 * maxdeg as f64 + 1.0;
    let mut x: Vec<f64> = init.to_vec();
    deflate(&mut x);
    let mut mx = vec![0.0f64; n];
    let mut prev: Option<Vec<f64>> = None;
    for _ in 0..iters {
        for i in 0..n {
            let deg = (off[i + 1] - off[i]) as f64;
            let mut s = 0.0;
            for k in off[i]..off[i + 1] {
                s += x[tgt[k] as usize];
            }
            let lx = deg * x[i] - s; // (L x)_i = deg_i·x_i − Σ_{j~i} x_j
            mx[i] = c * x[i] - lx; // (M x)_i = c·x_i − (L x)_i
        }
        std::mem::swap(&mut x, &mut mx);
        deflate(&mut x);
        if let Some(ref p) = prev {
            let mut drift = 0.0;
            for i in 0..n {
                drift += (x[i] - p[i]).abs() + (x[i] + p[i]).abs(); // sign-invariant convergence (Python)
            }
            if drift < 1e-9 {
                break;
            }
        }
        prev = Some(x.clone());
    }
    out.copy_from_slice(&x);
    0
}

/// Kernighan–Lin balanced (size-preserving) swap refinement of a bisection. `parts` (0/1) is updated
/// in place; returns the final cut size. Mirrors repo_partition._kl_refine(keep_balance=True).
#[no_mangle]
pub extern "C" fn gc_kl_refine(
    n: usize,
    off: *const usize,
    tgt: *const u32,
    parts: *mut u8,
    passes: usize,
) -> i64 {
    if n == 0 {
        return 0;
    }
    let (off, tgt) = unsafe { csr(n, off, tgt) };
    let parts = unsafe { slice::from_raw_parts_mut(parts, n) };
    // sorted neighbor segments → O(log deg) edge-existence (used only by the −2 adjacency correction;
    // does NOT touch the Laplacian sum order, so gc_fiedler stays bit-faithful)
    let mut nbr: Vec<u32> = tgt.to_vec();
    for i in 0..n {
        nbr[off[i]..off[i + 1]].sort_unstable();
    }
    let has_edge = |a: usize, b: usize| -> bool { nbr[off[a]..off[a + 1]].binary_search(&(b as u32)).is_ok() };

    for _ in 0..passes {
        // node gains are constant within a pass (parts unchanged until the swap) → precompute once
        let mut ng = vec![0i64; n];
        for i in 0..n {
            let (mut same, mut other) = (0i64, 0i64);
            for k in off[i]..off[i + 1] {
                if parts[tgt[k] as usize] == parts[i] {
                    same += 1;
                } else {
                    other += 1;
                }
            }
            ng[i] = other - same;
        }
        let zeros: Vec<usize> = (0..n).filter(|&i| parts[i] == 0).collect();
        let ones: Vec<usize> = (0..n).filter(|&i| parts[i] == 1).collect();
        let mut best_gain = 0i64;
        let mut best: Option<(usize, usize)> = None;
        for &a in &zeros {
            for &b in &ones {
                let g = ng[a] + ng[b] - if has_edge(a, b) { 2 } else { 0 };
                if g > best_gain {
                    best_gain = g;
                    best = Some((a, b));
                }
            }
        }
        match best {
            None => break,
            Some((a, b)) => {
                parts[a] = 1;
                parts[b] = 0;
            }
        }
    }

    let mut cut = 0i64; // count each undirected edge once (i < j)
    for i in 0..n {
        for k in off[i]..off[i + 1] {
            let j = tgt[k] as usize;
            if i < j && parts[i] != parts[j] {
                cut += 1;
            }
        }
    }
    cut
}

/// Transitive dependents of a dirty node (proof-DAG incremental invalidation), BFS over the reverse
/// edges. CSR here is the DEPENDENTS graph. Writes the dirty set (including `start`) into `out` and
/// returns its length. Provided for completeness; proof_dag.py already does this in O(V+E) in Python.
#[no_mangle]
pub extern "C" fn gc_transitive_dependents(
    n: usize,
    off: *const usize,
    tgt: *const u32,
    start: usize,
    out: *mut u32,
) -> i64 {
    if n == 0 || start >= n {
        return 0;
    }
    let (off, tgt) = unsafe { csr(n, off, tgt) };
    let out = unsafe { slice::from_raw_parts_mut(out, n) };
    let mut seen = vec![false; n];
    let mut stack = vec![start as u32];
    seen[start] = true;
    let mut cnt = 0usize;
    while let Some(u) = stack.pop() {
        out[cnt] = u;
        cnt += 1;
        let u = u as usize;
        for k in off[u]..off[u + 1] {
            let v = tgt[k] as usize;
            if !seen[v] {
                seen[v] = true;
                stack.push(v as u32);
            }
        }
    }
    cnt as i64
}

/// sanity probe for the ctypes loader
#[no_mangle]
pub extern "C" fn gc_abi_version() -> u64 {
    1
}
