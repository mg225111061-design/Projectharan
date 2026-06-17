#!/usr/bin/env python3
"""
test_claude.py — verify the live Claude path. RUN THIS WITH YOUR OWN KEY.
=========================================================================
Two modes:

  # 1) REAL call (you supply the key):
  export HARAN_KEY=sk-ant-...            # your Anthropic API key
  python3 scripts/test_claude.py         # makes ONE real Claude call and reports live/usage/snippet

  # 2) KEY-FREE shape check (no real key needed):
  python3 scripts/test_claude.py --shape # sends a DUMMY key to the public API; 401 ⇒ shape accepted

Key security (LEVEL 1): this harness reads the key from $HARAN_KEY for exactly one call, hands it to
claude_generate, and drops it — it is never written to a file/log/cache. (claude_agent.py itself never
imports os; this *separate* script reads the env var you explicitly set for your own test.)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import claude_agent as CA   # noqa: E402

_PROMPT = ("Write a HARAN function `triangular(n: Nat) -> Nat` with `ensures result = n*(n+1)/2` "
           "using a single `fold k in 1..n { k }`. Return only the function.")


def shape_probe() -> int:
    """Key-free: confirm the request the app builds is accepted by the real API up to auth (401)."""
    import anthropic
    dummy = "sk-ant-api03-DUMMY-INVALID-DO-NOT-USE-shape-probe-0000000000"
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    client = anthropic.Anthropic(api_key=dummy, base_url=base, max_retries=0)
    kwargs = CA._build_kwargs(_PROMPT, None, CA.DEFAULT_MODEL, CA.DEFAULT_MAX_TOKENS, True)
    print(f"model={CA.DEFAULT_MODEL}  max_tokens={CA.DEFAULT_MAX_TOKENS}  thinking={{'type':'adaptive'}}")
    try:
        client.messages.create(**kwargs)
        print("UNEXPECTED: a dummy key should never succeed."); return 1
    except anthropic.AuthenticationError:
        print("SHAPE OK ✓ — the request reached the API and was rejected ONLY for the (dummy) key (401).")
        print("            With a real HARAN_KEY this exact request shape is accepted.")
        print("            (Body-param conformance is additionally enforced offline by")
        print("             claude_agent._assert_spec_conformant — no temperature/top_p/budget_tokens/prefill.)")
        return 0
    except anthropic.BadRequestError as e:
        print("SHAPE WRONG (400):", CA.redact_key(str(e))[:300]); return 1
    except Exception as e:   # noqa: BLE001
        print(f"probe error ({type(e).__name__}):", CA.redact_key(str(e))[:200]); return 1


def live_call() -> int:
    key = os.environ.get("HARAN_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("No HARAN_KEY in the environment. Either:")
        print("  export HARAN_KEY=sk-ant-...   &&  python3 scripts/test_claude.py     # real call")
        print("  python3 scripts/test_claude.py --shape                                # key-free shape check")
        return 2
    print(f"Making ONE real Claude call (model={CA.DEFAULT_MODEL}, max_tokens={CA.DEFAULT_MAX_TOKENS}) …")
    try:
        r = CA.claude_generate(_PROMPT, api_key=key)        # LEVEL-1: used once, dropped inside
    except Exception as e:   # noqa: BLE001
        print(f"CALL FAILED ({type(e).__name__}):", CA.redact_key(str(e))[:300])
        return 1
    finally:
        key = None
    if not r.live:
        print("Returned a MOCK result (source=%s) — no live call was made." % r.source); return 1
    print(f"LIVE OK ✓  source={r.source}  usage={r.usage}")
    print("  --- generated (first 240 chars) ---")
    print("  " + r.text[:240].replace("\n", "\n  "))
    return 0


if __name__ == "__main__":
    raise SystemExit(shape_probe() if "--shape" in sys.argv[1:] else live_call())
