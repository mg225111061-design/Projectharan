"""
§AS §3.1/§3.2 — Z3 CONCURRENCY GUARD + BOUNDED SUBPROCESS (Tier-2 production robustness; precision UNTOUCHED).
================================================================================================================
Two REPRODUCED production hazards, fixed (measurement-first — §3.1 was confirmed by a 24-thread segfault, rc=139):

§3.1  z3's default Context and its ASTs are NOT thread-safe. Under a threadpool server (FastAPI sync handlers),
      concurrent solves on the shared context SEGFAULT the whole process. `z3_serialized()` / `@guarded` acquire a
      single global re-entrant lock so all z3 work is serialized across threads — correct, zero-dependency, and z3 is
      the bottleneck anyway so throughput cost is minimal (correctness > concurrency for a prover).

§3.2  A z3/Gröbner C-level OOM cannot be caught by Python try/except — only a PROCESS boundary contains it.
      `run_bounded(fn, mem_mb, timeout_s)` runs `fn` in a child process under `RLIMIT_AS` + a hard time cap; if the
      child OOMs / crashes / times out, the parent SURVIVES and gets a DECLINE sentinel (graceful degradation, never a
      hang/zombie). Pure stdlib (threading + multiprocessing + resource).

★ This changes NO verdict — it never turns a DECLINE into EXACT or vice-versa. It only keeps the prover process alive.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

# ── §3.1 — single global re-entrant lock serializing all z3 access across threads ───────────────────────────────
Z3_LOCK = threading.RLock()


class z3_serialized:
    """Context manager: hold the global z3 lock for the duration of a z3 interaction (solver build + check + model)."""
    def __enter__(self):
        Z3_LOCK.acquire()
        return self

    def __exit__(self, *exc):
        Z3_LOCK.release()
        return False


def guarded(fn: Callable) -> Callable:
    """Decorator: run `fn` under the global z3 lock (use on any function that builds/queries z3 in a server path)."""
    def wrapper(*a, **k):
        with z3_serialized():
            return fn(*a, **k)
    wrapper.__name__ = getattr(fn, "__name__", "guarded")
    wrapper.__doc__ = getattr(fn, "__doc__", None)
    return wrapper


# ── §3.2 — bounded subprocess for C-level OOM / runaway containment (graceful degradation) ──────────────────────
@dataclass
class BoundedResult:
    ok: bool                                 # the child returned a value within the bounds
    value: Any = None
    reason: str = ""                         # "ok" | "oom" | "timeout" | "crash" | "error"


def _bootstrap_runner(fn, args, kwargs, q, cap):
    """Module-level child entry (picklable for the 'spawn' start method). Applies the address-space cap, runs fn,
    and reports the outcome on the queue."""
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))                 # hard address-space cap (child only)
    except Exception:  # noqa: BLE001
        pass
    try:
        q.put(("ok", fn(*args, **kwargs)))
    except MemoryError:
        # at the RLIMIT_AS cap even q.put() can't start its feeder thread (no address space for a stack), so signal the
        # OOM via a sentinel EXIT CODE instead of the queue and _exit immediately — no thread, no leaked traceback.
        import os
        os._exit(137)                                                      # 128+9 (OOM convention); parent maps 137→oom
    except Exception as e:  # noqa: BLE001
        try:
            q.put(("error", f"{type(e).__name__}: {e}"))
        except Exception:  # noqa: BLE001 — queue itself unusable (e.g. cap hit) ⇒ fall back to a crash exit
            import os
            os._exit(139)


def run_bounded(fn: Callable, *args, mem_mb: int = 1024, timeout_s: float = 10.0, **kwargs) -> BoundedResult:
    """Run `fn(*args, **kwargs)` in a child process under RLIMIT_AS=mem_mb + a hard timeout. On OOM/crash/timeout the
    PARENT survives and returns a DECLINE-equivalent BoundedResult(ok=False) — never a hang/zombie. Heavy z3/groebner/
    kovacic calls should go through this in a server context (the C-level OOM the directive flags). `fn` must be a
    top-level (picklable) callable for the 'spawn' start method."""
    import multiprocessing as mp

    # ★ spawn (not fork): a FRESH child where RLIMIT_AS reliably applies. fork inherits the heavy parent VM (z3+numpy+
    # suite), so setrlimit below the current footprint can fail and a memory bomb would thrash the whole box (the 20-min
    # hang). spawn also avoids inheriting z3's internal threads/locks. The workers are top-level (picklable) so spawn is
    # safe; the small re-import cost is acceptable for a containment guard.
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    cap = mem_mb * 1024 * 1024
    p = ctx.Process(target=_bootstrap_runner, args=(fn, args, kwargs, q, cap))
    p.start()
    p.join(timeout_s)
    if p.is_alive():
        p.terminate()
        p.join(1.0)
        if p.is_alive():
            p.kill()
        return BoundedResult(False, None, "timeout")
    if p.exitcode is not None and p.exitcode < 0:                          # killed by a signal (segfault / OOM-killer)
        return BoundedResult(False, None, "crash")
    if p.exitcode == 137:                                                  # our MemoryError sentinel (RLIMIT_AS cap hit)
        return BoundedResult(False, None, "oom")
    if p.exitcode == 139:                                                  # queue-unusable fallback ⇒ treat as crash
        return BoundedResult(False, None, "crash")
    try:
        status, val = q.get_nowait()
    except Exception:  # noqa: BLE001
        return BoundedResult(False, None, "crash")
    if status == "ok":
        return BoundedResult(True, val, "ok")
    return BoundedResult(False, None, status)


# ── top-level workers for the regression (must be picklable for the 'spawn' start method) ───────────────────────
def _mem_bomb(_n: int = 0):
    """Allocate without bound — the child must hit the address-space cap and die while the PARENT survives."""
    blocks = []
    for _ in range(100000):
        blocks.append(bytearray(50 * 1024 * 1024))                        # 50 MB each ⇒ ~5 GB attempt ≫ any cap
    return len(blocks)


def _hang_worker(_n: int = 0):
    """Spin forever — the parent's hard TIMEOUT must reclaim it (no hang/zombie). The robust containment guarantee."""
    while True:
        pass


def _ok_worker(n: int):
    return n * n


_AB_CACHE: Optional[dict] = None


def adversarial_battery() -> dict:
    """★ §3.1: 24 concurrent z3 solves under the guard do NOT crash and all agree (the reproduced segfault is gone);
    ★ §3.2: a HANGING worker is reclaimed by the hard timeout (parent survives) and a MEMORY BOMB is contained, while a
    normal worker returns its value under a generous cap (graceful degradation, never a hang/zombie).
    ★ idempotent (no state) ⇒ computed ONCE per process (memoized): the suite calls it from test_as2, as_report.report,
    and as_report.adversarial_battery — without the cache the subprocess-spawning containment ran 3× (the 20-min hang)."""
    global _AB_CACHE
    if _AB_CACHE is not None:
        return _AB_CACHE
    # §3.1 — concurrent guarded z3 (the reproduced segfault path, now serialized)
    from catalog import equiv_check as EC
    results, errs = [], []

    def work():
        try:
            with z3_serialized():
                r = EC.prove_equiv_z3(lambda e: (e["a"] + e["b"]) ** 2,
                                      lambda e: e["a"] ** 2 + 2 * e["a"] * e["b"] + e["b"] ** 2, ["a", "b"], sort="Int")
            results.append(r.proved)
        except Exception as ex:  # noqa: BLE001
            errs.append(repr(ex))
    ts = [threading.Thread(target=work) for _ in range(24)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    concurrency_safe = len(results) == 24 and all(results) and not errs

    # §3.2 — bounded subprocess containment (spawn ⇒ RLIMIT_AS reliably applies in a fresh child; both cap AND timeout
    # keep the parent alive). Tight bounds: a fresh spawned python is ~0.5 GB virtual, so a 1 GB cap leaves room to
    # import then OOMs the bomb fast (no thrash); 6 s timeout is the backstop (the bomb OOMs in well under 1 s).
    hang = run_bounded(_hang_worker, mem_mb=2048, timeout_s=2.0)            # infinite loop ⇒ reclaimed by timeout
    bomb = run_bounded(_mem_bomb, mem_mb=1024, timeout_s=6.0)               # ~5 GB attempt ⇒ contained (oom/crash) fast
    ok = run_bounded(_ok_worker, 7, mem_mb=2048, timeout_s=10.0)           # generous cap ⇒ normal worker returns

    cases = {
        "z3_concurrency_no_crash": concurrency_safe,           # ★ §3.1 — the reproduced segfault is fixed
        "all_concurrent_proofs_agree": len(results) == 24 and all(results),
        "hang_reclaimed_by_timeout": (not hang.ok) and hang.reason == "timeout",   # ★ §3.2 — no hang/zombie
        "membomb_contained": (not bomb.ok) and bomb.reason in ("oom", "crash", "timeout"),  # ★ §3.2 — parent survives
        "normal_worker_ok": ok.ok and ok.value == 49,          # ★ graceful degradation (normal path unaffected)
    }
    _AB_CACHE = {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
    return _AB_CACHE
