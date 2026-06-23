"""
PHASE 1 — robust MATH input parser: the notations people actually type → the internal problem dict.
====================================================================================================
Forgiving of `^` vs `**`, unicode math (Σ ∏ ∫ √ π ² ³ −), LaTeX (\sum_{k=1}^{N}, \frac, \cdot), whitespace, casing.
Recognizes: a^b mod m / pow(a,b,m) / towers a^(b^c) mod m; fibonacci/lucas/catalan(n) [mod m]; Lucas–Lehmer /
isprime(2^p−1); collatz(n); Σ/sum(f,k,lo,hi) (Faulhaber for k^p, else summand fold); n! / factorial; C(n,k) /
binomial; gcd/lcm/isprime/factor/eulerphi; ∫/integrate; d/dx/diff; det/eigenvalues/inverse of [[..]]; solve(...).

Returns a problem dict for the solver, or {"_parse_error": "<precise hint>"} so MATH gives a SPECIFIC
parse-failure message (not a blunt "no structure"). SYMBOLIC parsing needs NO key. NL (prose) is handled
upstream by the optional LLM pipeline (echoed, UNVERIFIED); this module is pure, deterministic, key-free.
"""
from __future__ import annotations

import json
import re
from typing import Optional

import sympy as sp

_SUPERSCRIPT = str.maketrans({"²": "**2", "³": "**3", "⁴": "**4", "⁵": "**5", "⁶": "**6", "⁰": "**0", "¹": "**1"})


def _norm(s: str) -> str:
    """Normalize unicode/LaTeX/`^` to a plain ASCII-ish math string."""
    s = s.strip()
    s = (s.replace("−", "-").replace("×", "*").replace("·", "*").replace("π", "pi")
         .replace("∞", "oo").replace("√", "sqrt"))
    s = s.translate(_SUPERSCRIPT)
    # LaTeX
    s = s.replace(r"\left", "").replace(r"\right", "").replace(r"\,", " ").replace(r"\cdot", "*").replace(r"\times", "*")
    s = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"((\1)/(\2))", s)
    s = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"sqrt(\1)", s)
    s = s.replace(r"\sum", "Σ").replace(r"\prod", "∏").replace(r"\int", "∫")
    s = s.replace("^", "**")
    return s


def _to_int(expr: str) -> Optional[int]:
    """Safely evaluate an integer arithmetic expression (digits, ** * + - ( ), e-notation like 1e9, 10**12)."""
    try:
        e = sp.sympify(expr.replace("**", "^").replace("^", "**"), rational=True)
        if e.free_symbols:
            return None
        v = sp.nsimplify(e)
        return int(v) if v == int(v) else None
    except Exception:  # noqa: BLE001
        return None


def _modulus(tail: str) -> Optional[int]:
    """Extract a modulus from a trailing 'mod m' / '% m'."""
    m = re.search(r"(?:mod|%)\s*(.+)$", tail, re.IGNORECASE)
    return _to_int(m.group(1)) if m else None


def parse(text) -> dict:
    if isinstance(text, dict):
        return text
    raw = (text or "").strip()
    if not raw:
        return {"_parse_error": "empty input"}
    if raw[0] == "{":
        try:
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return {"_parse_error": "looks like JSON but did not parse"}
    s = _norm(raw)
    low = s.lower()

    # ── pow(a,b,m) / a**b mod m / towers a**(b**c) mod m ──
    mp = re.fullmatch(r"\s*pow\s*\(\s*(-?\d+)\s*,\s*(.+?)\s*,\s*(.+?)\s*\)\s*", s, re.IGNORECASE)
    if mp:
        a, b, m = int(mp[1]), _to_int(mp[2]), _to_int(mp[3])
        if b is not None and m is not None:
            return {"kernel": "modexp", "a": a, "b": b, "m": m}
    mexp = re.fullmatch(r"\s*(-?\d+)\s*\*\*\s*\(?\s*(.+?)\s*\)?\s*(?:mod|%)\s*(.+?)\s*", s, re.IGNORECASE)
    if mexp and "**" in _norm(mexp[2]) or (mexp and _to_int(mexp[2]) is not None):
        a, b, m = int(mexp[1]), _to_int(mexp[2]), _to_int(mexp[3])
        if b is not None and m is not None:
            return {"kernel": "modexp", "a": a, "b": b, "m": m}

    # ── Lucas–Lehmer / Mersenne primality isprime(2^p−1) ──
    mll = re.fullmatch(r"\s*(?:lucas[\s_-]*lehmer|ll)\s*\(?\s*(.+?)\s*\)?\s*", low)
    if mll and _to_int(mll[1]) is not None:
        return {"kernel": "lucas_lehmer", "p": _to_int(mll[1])}
    mmers = re.fullmatch(r"\s*is_?prime\s*\(\s*2\s*\*\*\s*(.+?)\s*-\s*1\s*\)\s*", low)
    if mmers and _to_int(mmers[1]) is not None:
        return {"kernel": "lucas_lehmer", "p": _to_int(mmers[1])}

    # ── collatz ──
    mc = re.fullmatch(r"\s*collatz(?:\s+(?:steps|stopping\s*time)\s*(?:of)?)?\s*\(?\s*(\d+)\s*\)?\s*", low)
    if mc:
        return {"kernel": "collatz", "n": int(mc[1])}

    # ── fibonacci / lucas / catalan (n) [mod m] ──
    mfib = re.fullmatch(r"\s*(?:fib(?:onacci)?|f)\s*\(?\s*(.+?)\s*\)?\s*((?:mod|%)\s*.+)?\s*", s, re.IGNORECASE)
    if mfib and re.match(r"^(?:fib|fibonacci|f)\b", low):
        n = _to_int(mfib[1])
        if n is not None:
            return {"kernel": "fib", "n": n, "m": _modulus(mfib[2] or "")}
    mluc = re.fullmatch(r"\s*(?:lucas|l)\s*\(\s*(.+?)\s*\)\s*((?:mod|%)\s*.+)?\s*", s, re.IGNORECASE)
    if mluc and re.match(r"^(?:lucas|l)\s*\(", low):
        n = _to_int(mluc[1])
        if n is not None:
            return {"kernel": "lucas", "n": n, "m": _modulus(mluc[2] or "")}
    mcat = re.fullmatch(r"\s*catalan\s*\(?\s*(\d+)\s*\)?\s*((?:mod|%)\s*.+)?\s*", low)
    if mcat:
        return {"kernel": "catalan", "n": int(mcat[1]), "m": _modulus(mcat[2] or "")}

    # ── summation: sum(f,k,lo,hi) / Σ_{k=lo}^{hi} f / sum f from lo to hi ──
    summ = _parse_sum(s)
    if summ is not None:
        return summ

    # ── factorial n! ──
    mfac = re.fullmatch(r"\s*(?:factorial\s*\(\s*(\d+)\s*\)|(\d+)\s*!)\s*", low)
    if mfac:
        return {"kernel": "factorial", "n": int(mfac[1] or mfac[2])}

    # ── binomial C(n,k) / binomial(n,k) / nCk ──
    mbin = re.fullmatch(r"\s*(?:c|binomial|choose)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*", low)
    if mbin:
        return {"domain": "combinatorics", "op": "binomial", "n": int(mbin[1]), "r": int(mbin[2])}

    # ── gcd / lcm ──
    mg = re.fullmatch(r"\s*(gcd|lcm)\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*", low)
    if mg:
        if mg[1] == "gcd":
            return {"domain": "number_theory", "op": "egcd", "a": int(mg[2]), "b": int(mg[3])}
        return {"kernel": "lcm", "a": int(mg[2]), "b": int(mg[3])}

    # ── matrices: det/eigenvalues/inverse of [[...]] ──
    mmat = re.fullmatch(r"\s*(det|determinant|eigenvalues?|eig|inverse|inv)\s*\(?\s*(\[\[.+\]\])\s*\)?\s*", s, re.IGNORECASE)
    if mmat:
        mat = _parse_matrix(mmat[2])
        if mat is not None:
            opmap = {"det": "det", "determinant": "det", "eigenvalue": "eigen", "eigenvalues": "eigen",
                     "eig": "eigen", "inverse": "inverse", "inv": "inverse"}
            return {"domain": "linear_algebra", "op": opmap[mmat[1].lower()], "A": mat}

    # ── delegate to the strict free-text router (isprime/factor/integrate/solve/nonneg/φ/ζ/Γ/…) ──
    nat = _free_text(s)
    if nat:
        return nat

    # ── bare summand mentioning k (indefinite sum) ──
    if "k" in low and re.fullmatch(r"[0-9k\s+\-*/().!]+|.*k\*\*\d+.*", s.replace("factorial", "")):
        return {"sum": s}

    return {"_parse_error": "couldn't parse — try e.g.  sum(k^2,k,1,100) · 2^50 mod 97 · fibonacci(100) mod 1e9+7 · "
                            "isprime(2^31-1) · collatz(27) · C(10,3) · det([[1,2],[3,4]]) · factor x^2-1 · integrate x^2"}


def _parse_sum(s: str) -> Optional[dict]:
    # sum(f, k, lo, hi)
    m = re.fullmatch(r"\s*(?:sum|Σ|∑)\s*\(\s*(.+?)\s*,\s*([a-zA-Z])\s*,\s*(.+?)\s*,\s*(.+?)\s*\)\s*", s, re.IGNORECASE)
    if not m:
        # Σ_{k=lo}^{hi} f   or  \sum_{k=lo}^{hi} f
        m2 = re.fullmatch(r"\s*(?:Σ|∑)\s*_\{?\s*([a-zA-Z])\s*=\s*(.+?)\s*\}?\s*\*\*\s*\{?\s*(.+?)\s*\}?\s+(.+?)\s*", s)
        if m2:
            m = type("M", (), {"__getitem__": lambda self, i: [None, m2[4], m2[1], m2[2], m2[3]][i]})()
        else:
            # sum f from lo to hi   (var defaults to k)
            m3 = re.fullmatch(r"\s*(?:sum|Σ|∑)\s+(.+?)\s+from\s+(.+?)\s+to\s+(.+?)\s*", s, re.IGNORECASE)
            if m3:
                var = "k" if "k" in m3[1] else (next((c for c in m3[1] if c.isalpha()), "k"))
                m = type("M", (), {"__getitem__": lambda self, i: [None, m3[1], var, m3[2], m3[3]][i]})()
            else:
                # bare "sum <expr>" / "Σ <expr>" (no bounds) ⇒ indefinite summand fold
                m4 = re.fullmatch(r"\s*(?:sum|Σ|∑)\s+(.+)", s, re.IGNORECASE)
                if m4 and not re.search(r"\bfrom\b", m4[1], re.IGNORECASE):
                    f = m4[1].strip()
                    var = "k" if "k" in f else next((c for c in f if c.isalpha()), "k")
                    return {"sum": f.replace(var, "k") if var != "k" else f}
                return None
    f, var, lo, hi = m[1].strip(), m[2].strip(), m[3].strip(), m[4].strip()
    lo_i, hi_i = _to_int(lo), _to_int(hi)
    # Faulhaber: summand is var^p (pure power)
    mp = re.fullmatch(rf"\s*{re.escape(var)}\s*\*\*\s*(\d+)\s*", f) or (re.fullmatch(rf"\s*{re.escape(var)}\s*", f) and None)
    if re.fullmatch(rf"\s*{re.escape(var)}\s*", f):
        p = 1
        mp = True
    elif mp:
        p = int(mp[1])
    else:
        mp = None
    if mp and lo_i is not None and hi_i is not None:
        return {"kernel": "faulhaber", "p": p, "N": hi_i, "lo": lo_i}
    # general definite/indefinite summand → fold/Gosper path (rename var to k for the engine)
    fk = f.replace(var, "k") if var != "k" else f
    return {"sum": fk, **({"_lo": lo_i, "_hi": hi_i} if (lo_i is not None and hi_i is not None) else {})}


def _parse_matrix(s: str):
    try:
        rows = json.loads(s)
        if isinstance(rows, list) and all(isinstance(r, list) for r in rows):
            return rows
    except Exception:  # noqa: BLE001
        pass
    return None


def _free_text(s: str) -> dict:
    t = s.strip().rstrip("?.").strip()
    low = t.lower()
    pats = (
        (r"(?:is\s+)?(\d+)\s+(?:a\s+)?prime", lambda m: {"domain": "number_theory", "op": "is_prime", "n": int(m[1])}),
        (r"is_?prime\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "number_theory", "op": "is_prime", "n": int(m[1])}),
        (r"factori[sz]e?\s+(\d+)", lambda m: {"domain": "number_theory", "op": "factorize", "n": int(m[1])}),
        (r"factor\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "number_theory", "op": "factorize", "n": int(m[1])}),
        (r"(?:euler\s*)?(?:phi|totient|φ)\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "number_theory", "op": "euler_phi", "n": int(m[1])}),
        (r"pell\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "number_theory", "op": "pell", "N": int(m[1])}),
        (r"(?:zeta|ζ)\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "special_functions", "op": "zeta_even", "s": int(m[1])}),
        (r"gamma\s*\(?\s*(\d+)\s*/\s*2\s*\)?", lambda m: {"domain": "special_functions", "op": "gamma", "two_z": int(m[1])}),
        (r"gamma\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "special_functions", "op": "gamma", "two_z": 2 * int(m[1])}),
    )
    for pat, build in pats:
        mm = re.fullmatch(pat, low)
        if mm:
            return build(mm)
    mf = re.fullmatch(r"factor\s+(.+)", t, re.IGNORECASE)
    if mf and not re.fullmatch(r"\d+", mf.group(1).strip()):
        return {"domain": "algebra", "op": "factor", "poly": mf.group(1).strip()}
    msv = re.fullmatch(r"(?:solve|roots?(?:\s+of)?)\s+(.+?)(?:\s*=\s*0)?", t, re.IGNORECASE)
    if msv and "x" in msv.group(1):
        return {"domain": "algebra", "op": "solve_poly", "poly": msv.group(1).strip()}
    mi = re.fullmatch(r"(?:integrate|∫)\s+(.+?)(?:\s*d\s*x)?", t, re.IGNORECASE)
    if mi and "x" in mi.group(1):
        return {"domain": "calculus", "op": "integrate", "f": mi.group(1).strip()}
    md = re.fullmatch(r"(?:d/dx|diff(?:erentiate)?|derivative\s+of)\s+(.+?)(?:\s*d?x?)?", t, re.IGNORECASE)
    if md and "x" in md.group(1):
        return {"domain": "calculus", "op": "differentiate", "f": md.group(1).strip()}
    mnn = re.fullmatch(r"(.+?)\s*(?:>=|≥)\s*0", t)
    if mnn and "x" in mnn.group(1):
        return {"domain": "inequalities", "op": "nonneg", "poly": mnn.group(1).strip()}
    return {}
