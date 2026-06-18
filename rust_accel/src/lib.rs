//! v34 STAGE 3 — dependency-0 Rust acceleration (no flint/faer; std only, ctypes ABI).
//! NTT-based polynomial multiplication mod a NTT-friendly prime, with u128-intermediate modular
//! arithmetic (correct; Montgomery is an optimization left for later). Called from Python via ctypes.
//! The result is differential-tested against the Python reference (must be IDENTICAL) — no fake speedup.

const P: u64 = 998_244_353; // = 119 * 2^23 + 1, NTT-friendly; primitive root g = 3
const G: u64 = 3;

#[inline]
fn mulmod(a: u64, b: u64) -> u64 {
    ((a as u128 * b as u128) % P as u128) as u64
}

fn powmod(mut b: u64, mut e: u64) -> u64 {
    let mut r: u64 = 1;
    b %= P;
    while e > 0 {
        if e & 1 == 1 {
            r = mulmod(r, b);
        }
        b = mulmod(b, b);
        e >>= 1;
    }
    r
}

/// In-place iterative Cooley–Tukey NTT (forward if !invert, inverse if invert).
fn ntt(a: &mut [u64], invert: bool) {
    let n = a.len();
    // bit-reversal permutation
    let mut j = 0usize;
    for i in 1..n {
        let mut bit = n >> 1;
        while j & bit != 0 {
            j ^= bit;
            bit >>= 1;
        }
        j ^= bit;
        if i < j {
            a.swap(i, j);
        }
    }
    let mut len = 2usize;
    while len <= n {
        // primitive len-th root of unity (or its inverse)
        let root = powmod(G, (P - 1) / len as u64);
        let wlen = if invert { powmod(root, P - 2) } else { root };
        let mut i = 0usize;
        while i < n {
            let mut w: u64 = 1;
            for k in 0..len / 2 {
                let u = a[i + k];
                let v = mulmod(a[i + k + len / 2], w);
                a[i + k] = (u + v) % P;
                a[i + k + len / 2] = (u + P - v) % P;
                w = mulmod(w, wlen);
            }
            i += len;
        }
        len <<= 1;
    }
    if invert {
        let ninv = powmod(n as u64, P - 2);
        for x in a.iter_mut() {
            *x = mulmod(*x, ninv);
        }
    }
}

/// out[0..alen+blen-1] = (a * b) mod P, via NTT. Returns the result length. ABI: ctypes.
#[no_mangle]
pub extern "C" fn ntt_poly_mul(
    a: *const u64,
    alen: usize,
    b: *const u64,
    blen: usize,
    out: *mut u64,
) -> usize {
    if alen == 0 || blen == 0 {
        return 0;
    }
    let a = unsafe { std::slice::from_raw_parts(a, alen) };
    let b = unsafe { std::slice::from_raw_parts(b, blen) };
    let rlen = alen + blen - 1;
    let mut n = 1usize;
    while n < rlen {
        n <<= 1;
    }
    let mut fa = vec![0u64; n];
    let mut fb = vec![0u64; n];
    fa[..alen].copy_from_slice(a);
    fb[..blen].copy_from_slice(b);
    ntt(&mut fa, false);
    ntt(&mut fb, false);
    for i in 0..n {
        fa[i] = mulmod(fa[i], fb[i]);
    }
    ntt(&mut fa, true);
    let out = unsafe { std::slice::from_raw_parts_mut(out, rlen) };
    out.copy_from_slice(&fa[..rlen]);
    rlen
}

/// ABI/version probe.
#[no_mangle]
pub extern "C" fn fold_accel_modulus() -> u64 {
    P
}
