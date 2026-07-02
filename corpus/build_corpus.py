"""
§AK §1 — 2000-CODE CORPUS with FIXED PROVENANCE (the root of honest measurement).
================================================================================================================
★ M-1 (measurement is the easiest thing to fake): fill the corpus with signal code and you get a 90% fold rate. A
single number is a lie. So this corpus is (a) split into FIVE DOMAIN BUCKETS measured separately, (b) skewed to the
GENERAL BACKEND (the real-world majority — where there IS no structure, so a LOW fold rate is correct, not failure),
and (c) tagged by PROVENANCE — `synthetic` (patterns we planted, foldable-by-design ⇒ a RECALL CEILING: "does the
engine catch what it knows?") vs `realworld_style` (real code shapes ⇒ the REAL number: "how much actually folds?").
Mixing the two is self-deception, so they are aggregated separately downstream.

★ Anti-manipulation guard: every bucket contains deliberately NON-foldable code (the general bucket is mostly that).
A corpus where everything folds is self-deception — failures must exist for the measurement to be honest.

★ Reproducible: generation is fully DETERMINISTIC (fixed seed, template-based — NO LLM, which would be non-reproducible
and unverifiable). Same seed ⇒ identical 2000 codes ⇒ identical numbers. The `planted` tag is the corpus's own
self-knowledge for sanity/anti-manipulation; it is NOT used to compute the fold rate (that comes only from the engine).

Repo-first: the realworld_style general/crypto shapes mirror `catalog.fold_coverage_production`'s corpus and the
`corpus/*.py` sample apps; numeric/signal/stats synthetics mirror the patterns the §AI conjecturers are built to recall.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, List, Tuple

SEED = 20260628
# domain → target count (general_backend is the majority — M-4: the real world is mostly structureless backend code)
DOMAIN_COUNTS = {"general_backend": 600, "numeric": 400, "signal": 350, "statistical": 350, "crypto_preprocessing": 300}
TOTAL = sum(DOMAIN_COUNTS.values())   # 2000


@dataclass
class CorpusItem:
    cid: str
    domain: str
    provenance: str          # "synthetic" | "realworld_style"
    src: str                 # the code (a self-contained function `f`)
    entry: str               # entry function name
    unary_oracle: bool       # callable as f(n)->number (the §AI black-box path can probe it)
    planted: str             # what we planted (corpus self-knowledge — NOT used in the fold rate)


# ── numeric (synthetic foldables = recall ceiling; realworld matrix/data loops = the real number) ───────────────
def _numeric(rng: random.Random, i: int) -> CorpusItem:
    fam = i % 9
    if fam == 0:                                            # Σ(a·k+b) — lift AND black-box foldable
        a, b = rng.randint(1, 9), rng.randint(0, 9)
        src = f"def f(n):\n    s = 0\n    for k in range(n + 1):\n        s += {a}*k + {b}\n    return s\n"
        return CorpusItem("", "numeric", "synthetic", src, "f", True, "linear_sum")
    if fam == 1:                                            # Σk² polynomial
        src = "def f(n):\n    s = 0\n    for k in range(n + 1):\n        s += k*k\n    return s\n"
        return CorpusItem("", "numeric", "synthetic", src, "f", True, "power_sum")
    if fam == 2:                                            # geometric a^n — black-box (constant ratio)
        a = rng.randint(2, 5)
        src = f"def f(n):\n    return {a} ** n\n"
        return CorpusItem("", "numeric", "synthetic", src, "f", True, "geometric")
    if fam == 3:                                            # disguised Fibonacci-class (linear recurrence)
        p, q = rng.randint(1, 3), rng.randint(1, 3)
        src = (f"def f(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, {p}*b + {q}*a\n    return a\n")
        return CorpusItem("", "numeric", "synthetic", src, "f", True, "linear_recurrence")
    if fam == 4:                                            # realworld: matrix-vector (data arg, not a unary oracle)
        src = ("def f(matrix, vector):\n    out = []\n    for row in matrix:\n        acc = 0\n"
               "        for j in range(len(vector)):\n            acc += row[j] * vector[j]\n        out.append(acc)\n    return out\n")
        return CorpusItem("", "numeric", "realworld_style", src, "f", False, "matvec_dataloop")
    if fam == 5:                                            # realworld: in-place normalize (data-dependent)
        src = ("def f(xs):\n    total = sum(xs) or 1\n    return [x / total for x in xs]\n")
        return CorpusItem("", "numeric", "realworld_style", src, "f", False, "normalize_data")
    if fam == 6:                                            # ★ realworld FOLDABLE: a real savings/fee schedule loop
        base, step = rng.choice([50, 100, 200]), rng.choice([3, 5, 7])
        src = (f"def f(periods):\n    balance = 0\n    for p in range(periods):\n        balance += {base} + {step}*p\n    return balance\n")
        return CorpusItem("", "numeric", "realworld_style", src, "f", True, "realworld_foldable_schedule")
    if fam == 7:                                            # ★ a HIDDEN-R case: §AI portfolio DECLINEs popcount, but the
        src = "def f(n):\n    return bin(n).count('1')\n"   #   k-regular mechanism (M22) folds it (k=2) ⇒ near-miss R
        return CorpusItem("", "numeric", "realworld_style", src, "f", True, "kregular_popcount")
    # planted DEEP-miss unary (base-10 digit sum — 10-regular in theory, but the current M22 k-kernel doesn't close
    # for k=10 ⇒ stays a genuine DECLINE even under aggressive retry; honestly NOT counted as R)
    src = "def f(n):\n    return sum(int(d) for d in str(n))\n"
    return CorpusItem("", "numeric", "realworld_style", src, "f", True, "deepmiss_digitsum_base10")


# ── signal (synthetic periodic/modular = recall ceiling; realworld DSP on data = real number) ───────────────────
def _signal(rng: random.Random, i: int) -> CorpusItem:
    fam = i % 6
    if fam == 0:                                            # periodic table lookup — black-box period fold
        p = rng.randint(2, 6)
        vals = [rng.randint(0, 99) for _ in range(p)]
        src = f"def f(n):\n    table = {vals}\n    return table[n % {p}]\n"
        return CorpusItem("", "signal", "synthetic", src, "f", True, "periodic")
    if fam == 1:                                            # modular orbit pow(a,n,m) — periodic mod m
        a, m = rng.choice([2, 3, 5]), rng.choice([7, 11, 13])
        src = f"def f(n):\n    return pow({a}, n, {m})\n"
        return CorpusItem("", "signal", "synthetic", src, "f", True, "modular_orbit")
    if fam == 2:                                            # alternating carrier (period-2 sign) × linear — recurrence
        c = rng.randint(1, 9)
        src = f"def f(n):\n    return ((-1) ** n) * {c}\n"
        return CorpusItem("", "signal", "synthetic", src, "f", True, "alternating")
    if fam == 3:                                            # realworld: moving average over a window (data arg)
        w = rng.randint(2, 5)
        src = (f"def f(xs):\n    w = {w}\n    out = []\n    for i in range(len(xs) - w + 1):\n"
               "        out.append(sum(xs[i:i+w]) / w)\n    return out\n")
        return CorpusItem("", "signal", "realworld_style", src, "f", False, "moving_average")
    if fam == 4:                                            # realworld: naive DFT magnitude (data arg, transcendental)
        src = ("def f(xs):\n    import math\n    n = len(xs)\n    out = []\n    for k in range(n):\n"
               "        re = sum(xs[t] * math.cos(2*math.pi*k*t/n) for t in range(n))\n        out.append(re)\n    return out\n")
        return CorpusItem("", "signal", "realworld_style", src, "f", False, "naive_dft")
    # planted NON-foldable unary (genuinely chaotic logistic map iterated n times — no periodic index, no closed form)
    src = "def f(n):\n    x = 0.3\n    for _ in range(n + 1):\n        x = 3.9 * x * (1 - x)\n    return int(x * 1000)\n"
    return CorpusItem("", "signal", "realworld_style", src, "f", True, "nonfoldable_logistic")


# ── statistical (synthetic Faulhaber = recall ceiling; realworld estimators on data = real number) ──────────────
def _statistical(rng: random.Random, i: int) -> CorpusItem:
    fam = i % 7
    if fam == 0:                                            # Σk³ (Faulhaber degree 4)
        src = "def f(n):\n    s = 0\n    for k in range(n + 1):\n        s += k*k*k\n    return s\n"
        return CorpusItem("", "statistical", "synthetic", src, "f", True, "cube_sum")
    if fam == 1:                                            # count of multiples (linear closed form)
        d = rng.randint(2, 5)
        src = f"def f(n):\n    c = 0\n    for k in range(n + 1):\n        if k % {d} == 0:\n            c += 1\n    return c\n"
        return CorpusItem("", "statistical", "synthetic", src, "f", True, "count_multiples")
    if fam == 2:                                            # triangular running total
        src = "def f(n):\n    s = 0\n    for k in range(1, n + 1):\n        s += k\n    return s\n"
        return CorpusItem("", "statistical", "synthetic", src, "f", True, "triangular")
    if fam == 3:                                            # realworld: mean over data (non-unary)
        src = "def f(xs):\n    return sum(xs) / len(xs) if xs else 0.0\n"
        return CorpusItem("", "statistical", "realworld_style", src, "f", False, "mean")
    if fam == 4:                                            # realworld: variance (two-pass, data arg)
        src = ("def f(xs):\n    n = len(xs) or 1\n    m = sum(xs) / n\n    return sum((x - m) ** 2 for x in xs) / n\n")
        return CorpusItem("", "statistical", "realworld_style", src, "f", False, "variance")
    if fam == 5:                                            # ★ realworld FOLDABLE: cumulative event count over n slots
        w = rng.choice([2, 3, 4])
        src = (f"def f(n):\n    seen = 0\n    for t in range(n):\n        seen += {w}\n    return seen\n")
        return CorpusItem("", "statistical", "realworld_style", src, "f", True, "realworld_foldable_cumcount")
    # planted NON-foldable: histogram bucketing (data-dependent control flow)
    src = ("def f(xs):\n    buckets = {}\n    for x in xs:\n        key = x // 10\n        buckets[key] = buckets.get(key, 0) + 1\n    return buckets\n")
    return CorpusItem("", "statistical", "realworld_style", src, "f", False, "histogram")


# ── crypto_preprocessing (★ the CORE must DECLINE — folding a hash/CSPRNG would be a false EXACT) ───────────────
def _crypto(rng: random.Random, i: int) -> CorpusItem:
    fam = i % 5
    if fam == 0:
        src = "def f(data):\n    import hashlib\n    return hashlib.sha256(data).hexdigest()\n"
        return CorpusItem("", "crypto_preprocessing", "realworld_style", src, "f", False, "sha256")
    if fam == 1:
        src = "def f(data):\n    import hashlib\n    return hashlib.md5(data).hexdigest()\n"
        return CorpusItem("", "crypto_preprocessing", "realworld_style", src, "f", False, "md5")
    if fam == 2:
        src = "def f(b):\n    import base64\n    return base64.b64encode(b).decode()\n"
        return CorpusItem("", "crypto_preprocessing", "realworld_style", src, "f", False, "base64")
    if fam == 3:                                            # xor stream (key-dependent, data arg)
        k = rng.randint(1, 255)
        src = f"def f(data):\n    return bytes(b ^ {k} for b in data)\n"
        return CorpusItem("", "crypto_preprocessing", "realworld_style", src, "f", False, "xor_stream")
    # a DETERMINISTIC PRNG-style unary oracle (truncated hash) — MUST DECLINE (incompressible, class C)
    src = ("def f(n):\n    import hashlib\n    return int.from_bytes(hashlib.sha256(str(n).encode()).digest()[:6], 'big')\n")
    return CorpusItem("", "crypto_preprocessing", "synthetic", src, "f", True, "nonfoldable_hash_oracle")


# ── general_backend (★ the honest majority — mostly structureless ⇒ a LOW fold rate is CORRECT) ─────────────────
def _general(rng: random.Random, i: int) -> CorpusItem:
    fam = i % 10
    if fam == 0:                                            # CRUD-style dispatch (data-dependent control flow)
        src = ("def f(cmd, store):\n    if cmd['op'] == 'get':\n        return store.get(cmd['key'])\n"
               "    elif cmd['op'] == 'set':\n        store[cmd['key']] = cmd['val']\n        return True\n    return None\n")
        return CorpusItem("", "general_backend", "realworld_style", src, "f", False, "crud_dispatch")
    if fam == 1:                                            # JSON parse (I/O-shaped)
        src = "def f(blob):\n    import json\n    return json.loads(blob)\n"
        return CorpusItem("", "general_backend", "realworld_style", src, "f", False, "json_parse")
    if fam == 2:                                            # string pipeline
        src = "def f(s):\n    return [t.strip().lower() for t in s.split(',') if t.strip()]\n"
        return CorpusItem("", "general_backend", "realworld_style", src, "f", False, "string_pipeline")
    if fam == 3:                                            # validation (control flow)
        src = ("def f(rec):\n    if not rec.get('name'):\n        return 'missing name'\n"
               "    if rec.get('age', 0) < 0:\n        return 'bad age'\n    return 'ok'\n")
        return CorpusItem("", "general_backend", "realworld_style", src, "f", False, "validation")
    if fam == 4:                                            # request handler (I/O)
        src = ("def f(req):\n    headers = {k.lower(): v for k, v in req.get('headers', {}).items()}\n"
               "    return {'status': 200, 'ct': headers.get('content-type', 'text/plain')}\n")
        return CorpusItem("", "general_backend", "realworld_style", src, "f", False, "http_handler")
    if fam == 5:                                            # config merge (dict walk)
        src = ("def f(base, override):\n    out = dict(base)\n    for k, v in override.items():\n        out[k] = v\n    return out\n")
        return CorpusItem("", "general_backend", "realworld_style", src, "f", False, "config_merge")
    if fam == 6:                                            # retry/backoff control flow
        src = ("def f(attempts):\n    delay = 1\n    log = []\n    for a in range(attempts):\n"
               "        log.append(delay)\n        delay = delay * 2\n    return log\n")
        return CorpusItem("", "general_backend", "realworld_style", src, "f", False, "backoff_loop")
    if fam == 7:                                            # path routing (string match)
        src = ("def f(path):\n    if path.startswith('/api/'):\n        return 'api'\n"
               "    if path.startswith('/static/'):\n        return 'static'\n    return 'web'\n")
        return CorpusItem("", "general_backend", "realworld_style", src, "f", False, "router_match")
    if fam == 8:                                            # ★ a planted FOLDABLE hiding in the backend (id accumulator)
        a, b = rng.randint(1, 5), rng.randint(0, 5)
        src = f"def f(n):\n    total = 0\n    for k in range(n + 1):\n        total += {a}*k + {b}\n    return total\n"
        return CorpusItem("", "general_backend", "synthetic", src, "f", True, "planted_linear_sum")
    # data-dependent aggregation (genuinely non-foldable control flow)
    src = ("def f(events):\n    seen = set()\n    out = []\n    for e in events:\n        if e['id'] not in seen:\n"
           "            seen.add(e['id'])\n            out.append(e)\n    return out\n")
    return CorpusItem("", "general_backend", "realworld_style", src, "f", False, "dedup_stream")


_BUILDERS: dict = {"general_backend": _general, "numeric": _numeric, "signal": _signal,
                   "statistical": _statistical, "crypto_preprocessing": _crypto}


def build_corpus(n: int = TOTAL, seed: int = SEED) -> List[CorpusItem]:
    """Deterministically build `n` codes across the five domains (proportional to DOMAIN_COUNTS), provenance-tagged.
    Same (n, seed) ⇒ identical corpus (reproducible). The default n=2000 is the directive's measurement size."""
    rng = random.Random(seed)
    # proportional per-domain counts that sum to exactly n
    counts = {d: max(1, round(n * c / TOTAL)) for d, c in DOMAIN_COUNTS.items()}
    drift = n - sum(counts.values())
    counts["general_backend"] += drift                     # absorb rounding drift into the majority bucket
    items: List[CorpusItem] = []
    for domain, cnt in counts.items():
        build = _BUILDERS[domain]
        for i in range(cnt):
            it = build(rng, i)
            it.cid = f"{domain}:{i:04d}"
            items.append(it)
    return items


def provenance_split(items: List[CorpusItem]) -> dict:
    syn = sum(1 for it in items if it.provenance == "synthetic")
    return {"total": len(items), "synthetic": syn, "realworld_style": len(items) - syn,
            "per_domain": {d: sum(1 for it in items if it.domain == d) for d in DOMAIN_COUNTS}}


def adversarial_battery() -> dict:
    """★ reproducibility (same seed ⇒ identical corpus); ★ M-4 honest sample (general_backend is the majority);
    ★ anti-manipulation (every bucket has a planted non-foldable, the general bucket is mostly realworld); ★ provenance
    is recorded on every item; codes parse."""
    import ast
    a, b = build_corpus(200, seed=1), build_corpus(200, seed=1)
    reproducible = [it.src for it in a] == [it.src for it in b]
    full = build_corpus()
    split = provenance_split(full)
    general_majority = split["per_domain"]["general_backend"] == max(split["per_domain"].values())
    has_synth = split["synthetic"] > 0 and split["realworld_style"] > 0
    # every domain has at least one realworld_style non-oracle (a structureless failure case) — anti-manipulation
    nonfold_each = all(any(it.domain == d and not it.unary_oracle for it in full) for d in DOMAIN_COUNTS)
    parses = all(_safe_parse(it.src) for it in build_corpus(120, seed=7))
    cases = {
        "reproducible_same_seed": reproducible,
        "total_is_2000": split["total"] == 2000,
        "general_backend_is_majority": general_majority,                 # ★ M-4 honest distribution
        "both_provenances_present": has_synth,                           # ★ synthetic vs realworld separable
        "every_bucket_has_nonfoldable": nonfold_each,                    # ★ anti-manipulation
        "all_codes_parse": parses,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


def _safe_parse(src: str) -> bool:
    import ast
    try:
        ast.parse(src)
        return True
    except SyntaxError:
        return False
