//! NATIVE-CORE §1 — dependency-0 Rust core (std only, ctypes ABI; no PyO3/maturin/cffi/flint/faer).
//! ============================================================================================
//! Delivers the pieces the v34 Rust stage explicitly deferred ("multimodular CRT / arena-DOD / explicit SIMD
//! noted as future"):
//!   • a flat **arena AST** (index-based, children-before-parents) evaluated in a single deterministic pass;
//!   • a **deterministic fixed-precision multimodular (CRT) ring** — evaluate the arena modulo a FIXED ordered
//!     prime basis, then Garner-combine the residues into the EXACT integer (native big-uint, base 2^32 limbs),
//!     replacing Python bignum for the arithmetic. EXACT while |result| < M/2 (M = ∏ basis primes); that bound
//!     is the "fixed precision". Beyond it the caller must widen the basis or DECLINE.
//!   • **rational reconstruction** (bounded extended Euclid) — recover p/q from its residue mod m;
//!   • a **deterministic, fixed-reduction-order** batched modular dot product (the "SIMD" demonstrator): pure
//!     integer arithmetic summed left-to-right ⇒ bit-identical regardless of vectorization or thread count.
//! Every result is DETERMINISTIC (no FP, fixed order) and differential-tested bit-exact against the Python
//! reference (see rust_core.py) — no fabricated number. If rustc is unavailable the Python path stands alone.

// ── fixed ordered prime basis (each < 2^31; ∏ ≈ 2^124, so M/2 ≈ 2^123 is the exact-integer bound) ──────────
const PRIMES: [u64; 4] = [2_147_483_647, 2_147_483_629, 2_147_483_587, 2_147_483_563];

#[inline]
fn mulmod(a: u64, b: u64, p: u64) -> u64 {
    ((a as u128 * b as u128) % p as u128) as u64
}

#[inline]
fn submod(a: u64, b: u64, p: u64) -> u64 {
    (a % p + p - b % p) % p
}

fn powmod(mut b: u64, mut e: u64, p: u64) -> u64 {
    let mut r: u64 = 1 % p;
    b %= p;
    while e > 0 {
        if e & 1 == 1 {
            r = mulmod(r, b, p);
        }
        b = mulmod(b, b, p);
        e >>= 1;
    }
    r
}

#[inline]
fn invmod(a: u64, p: u64) -> u64 {
    powmod(a % p, p - 2, p) // p prime ⇒ Fermat inverse
}

// ── tiny native big-uint (little-endian base 2^32 limbs) — the bignum we no longer borrow from Python ───────
fn bu_trim(v: &mut Vec<u32>) {
    while v.len() > 1 && *v.last().unwrap() == 0 {
        v.pop();
    }
}

fn bu_mul_small(a: &[u32], s: u64) -> Vec<u32> {
    let mut out = Vec::with_capacity(a.len() + 2);
    let mut carry: u128 = 0;
    for &limb in a {
        let cur = limb as u128 * s as u128 + carry;
        out.push((cur & 0xffff_ffff) as u32);
        carry = cur >> 32;
    }
    while carry > 0 {
        out.push((carry & 0xffff_ffff) as u32);
        carry >>= 32;
    }
    if out.is_empty() {
        out.push(0);
    }
    bu_trim(&mut out);
    out
}

fn bu_add(a: &[u32], b: &[u32]) -> Vec<u32> {
    let n = a.len().max(b.len());
    let mut out = Vec::with_capacity(n + 1);
    let mut carry: u64 = 0;
    for i in 0..n {
        let x = *a.get(i).unwrap_or(&0) as u64;
        let y = *b.get(i).unwrap_or(&0) as u64;
        let cur = x + y + carry;
        out.push((cur & 0xffff_ffff) as u32);
        carry = cur >> 32;
    }
    if carry > 0 {
        out.push(carry as u32);
    }
    bu_trim(&mut out);
    out
}

// a - b assuming a >= b
fn bu_sub(a: &[u32], b: &[u32]) -> Vec<u32> {
    let mut out = Vec::with_capacity(a.len());
    let mut borrow: i64 = 0;
    for i in 0..a.len() {
        let x = a[i] as i64;
        let y = *b.get(i).unwrap_or(&0) as i64;
        let mut cur = x - y - borrow;
        if cur < 0 {
            cur += 1 << 32;
            borrow = 1;
        } else {
            borrow = 0;
        }
        out.push((cur & 0xffff_ffff) as u32);
    }
    bu_trim(&mut out);
    out
}

fn bu_mod_small(a: &[u32], m: u64) -> u64 {
    let mut r: u64 = 0;
    for &limb in a.iter().rev() {
        r = ((r << 32) | limb as u64) % m;
    }
    r
}

// compare: -1 if a<b, 0 if a==b, 1 if a>b
fn bu_cmp(a: &[u32], b: &[u32]) -> i32 {
    let la = a.iter().rposition(|&x| x != 0).map_or(0, |i| i + 1);
    let lb = b.iter().rposition(|&x| x != 0).map_or(0, |i| i + 1);
    if la != lb {
        return if la < lb { -1 } else { 1 };
    }
    for i in (0..la).rev() {
        if a[i] != b[i] {
            return if a[i] < b[i] { -1 } else { 1 };
        }
    }
    0
}

// halve a big-uint (floor)
fn bu_halve(a: &[u32]) -> Vec<u32> {
    let mut out = vec![0u32; a.len()];
    let mut carry: u64 = 0;
    for i in (0..a.len()).rev() {
        let cur = (carry << 32) | a[i] as u64;
        out[i] = (cur >> 1) as u32;
        carry = cur & 1;
    }
    bu_trim(&mut out);
    out
}

fn modulus_product() -> Vec<u32> {
    let mut m = vec![1u32];
    for &p in PRIMES.iter() {
        m = bu_mul_small(&m, p);
    }
    m
}

/// Garner's algorithm over the FIXED basis: residues[i] = x mod PRIMES[i] ⇒ exact x in [0, M). Deterministic
/// (basis order fixed). Returns the big-uint in [0, M).
fn crt_garner(res: &[u64]) -> Vec<u32> {
    let mut x = vec![res[0] as u32, (res[0] >> 32) as u32];
    bu_trim(&mut x);
    let mut m_partial = vec![PRIMES[0] as u32, (PRIMES[0] >> 32) as u32];
    bu_trim(&mut m_partial);
    for i in 1..PRIMES.len() {
        let p = PRIMES[i];
        let x_mod = bu_mod_small(&x, p);
        let inv = invmod(bu_mod_small(&m_partial, p), p);
        let t = mulmod(submod(res[i], x_mod, p), inv, p); // in [0, p)
        x = bu_add(&x, &bu_mul_small(&m_partial, t));
        m_partial = bu_mul_small(&m_partial, p);
    }
    x
}

// ── ABI ─────────────────────────────────────────────────────────────────────────────────────────────────
#[no_mangle]
pub extern "C" fn rc_num_primes() -> u64 {
    PRIMES.len() as u64
}

#[no_mangle]
pub extern "C" fn rc_prime(i: usize) -> u64 {
    if i < PRIMES.len() {
        PRIMES[i]
    } else {
        0
    }
}

// opcodes: 0=CONST(value=arg), 1=VAR(index=arg), 2=NEG(lhs), 3=ADD(lhs,rhs), 4=SUB(lhs,rhs), 5=MUL(lhs,rhs)
fn eval_arena_modp(
    ops: &[u8],
    args: &[i64],
    lhs: &[u32],
    rhs: &[u32],
    vars: &[i64],
    p: u64,
) -> Option<u64> {
    let n = ops.len();
    let mut val = vec![0u64; n];
    for i in 0..n {
        val[i] = match ops[i] {
            0 => {
                let a = args[i];
                if a >= 0 {
                    (a as u64) % p
                } else {
                    submod(0, ((-a) as u64) % p, p)
                }
            }
            1 => {
                let vi = args[i] as usize;
                if vi >= vars.len() {
                    return None;
                }
                let v = vars[vi];
                if v >= 0 {
                    (v as u64) % p
                } else {
                    submod(0, ((-v) as u64) % p, p)
                }
            }
            2 => submod(0, val[lhs[i] as usize], p),
            3 => (val[lhs[i] as usize] + val[rhs[i] as usize]) % p,
            4 => submod(val[lhs[i] as usize], val[rhs[i] as usize], p),
            5 => mulmod(val[lhs[i] as usize], val[rhs[i] as usize], p),
            _ => return None,
        };
    }
    Some(val[n - 1])
}

/// Evaluate the arena under EVERY basis prime; write the residue vector (length rc_num_primes()). 0 ok / -1 bad.
#[no_mangle]
pub extern "C" fn rc_eval_residues(
    ops: *const u8,
    args: *const i64,
    lhs: *const u32,
    rhs: *const u32,
    n: usize,
    vars: *const i64,
    nvars: usize,
    out_res: *mut u64,
) -> i32 {
    if n == 0 {
        return -1;
    }
    let ops = unsafe { std::slice::from_raw_parts(ops, n) };
    let args = unsafe { std::slice::from_raw_parts(args, n) };
    let lhs = unsafe { std::slice::from_raw_parts(lhs, n) };
    let rhs = unsafe { std::slice::from_raw_parts(rhs, n) };
    let vars = if nvars == 0 {
        &[][..]
    } else {
        unsafe { std::slice::from_raw_parts(vars, nvars) }
    };
    let out = unsafe { std::slice::from_raw_parts_mut(out_res, PRIMES.len()) };
    for (k, &p) in PRIMES.iter().enumerate() {
        match eval_arena_modp(ops, args, lhs, rhs, vars, p) {
            Some(v) => out[k] = v,
            None => return -1,
        }
    }
    0
}

/// CRT-combine a residue vector into the EXACT signed integer, returned as base-2^32 little-endian limbs in
/// `out_limbs` (capacity `cap`); `*out_neg` = 1 if the (symmetric) result is negative. Returns #limbs or -1.
/// Symmetric range: result in (−M/2, M/2]. EXACT only while |true value| < M/2 (the fixed-precision bound).
#[no_mangle]
pub extern "C" fn rc_crt_combine(
    res: *const u64,
    out_limbs: *mut u32,
    cap: usize,
    out_neg: *mut u8,
) -> i32 {
    let res = unsafe { std::slice::from_raw_parts(res, PRIMES.len()) };
    let x = crt_garner(res);
    let m = modulus_product();
    let half = bu_halve(&m);
    let (mag, neg) = if bu_cmp(&x, &half) > 0 {
        (bu_sub(&m, &x), 1u8) // negative: value = x - M  ⇒ magnitude = M - x
    } else {
        (x, 0u8)
    };
    if mag.len() > cap {
        return -1;
    }
    let out = unsafe { std::slice::from_raw_parts_mut(out_limbs, cap) };
    for i in 0..cap {
        out[i] = *mag.get(i).unwrap_or(&0);
    }
    unsafe {
        *out_neg = neg;
    }
    mag.len() as i32
}

/// Deterministic, FIXED-reduction-order batched modular dot product: Σ a_i·b_i mod p, summed left-to-right.
/// Pure integer arithmetic ⇒ bit-identical regardless of autovectorization or thread count (no FP, fixed order).
#[no_mangle]
pub extern "C" fn rc_dot_modp(a: *const u64, b: *const u64, n: usize, p: u64) -> u64 {
    if n == 0 {
        return 0;
    }
    let a = unsafe { std::slice::from_raw_parts(a, n) };
    let b = unsafe { std::slice::from_raw_parts(b, n) };
    let mut acc: u64 = 0;
    for i in 0..n {
        acc = (acc + mulmod(a[i] % p, b[i] % p, p)) % p;
    }
    acc
}

/// Bounded rational reconstruction: recover p/q ≡ r (mod m) with |p|, q ≤ sqrt(m/2) via the extended-Euclid
/// remainder-sequence stop. Returns 1 and writes *out_num=p, *out_den=q on success; 0 if none in range.
#[no_mangle]
pub extern "C" fn rc_rational_reconstruct(
    r: u64,
    m: u64,
    out_num: *mut i64,
    out_den: *mut i64,
) -> i32 {
    // bound N = floor(sqrt(m/2))
    let mut nbound: u64 = 0;
    while (nbound + 1) * (nbound + 1) <= m / 2 {
        nbound += 1;
    }
    // extended Euclid on (m, r), tracking the v-coefficient; stop when remainder <= N
    let (mut r0, mut r1) = (m as i128, (r % m) as i128);
    let (mut s0, mut s1) = (0i128, 1i128); // v-coeff: r1 = s1 * r (mod m)
    while r1 as u64 > nbound && r1 != 0 {
        let q = r0 / r1;
        let r2 = r0 - q * r1;
        let s2 = s0 - q * s1;
        r0 = r1;
        r1 = r2;
        s0 = s1;
        s1 = s2;
    }
    let num = r1; // p
    let den = s1; // q
    let (num, den) = if den < 0 { (-num, -den) } else { (num, den) };
    if den == 0 || (den as u64) > nbound || num.unsigned_abs() as u64 > nbound {
        return 0;
    }
    // verify p ≡ q·r (mod m)
    let lhs = num.rem_euclid(m as i128);
    let rhs = (den * (r as i128)).rem_euclid(m as i128);
    if lhs != rhs {
        return 0;
    }
    unsafe {
        *out_num = num as i64;
        *out_den = den as i64;
    }
    1
}
