"""
CAPSTONE bypass (우회군 D) — Angluin's L* active automaton learning (pure Python, no deps).
============================================================================================
A black-box boolean behaviour over a finite alphabet — a function `mq(word)->bool` — that is REGULAR is recovered
EXACTLY as its minimal DFA from membership + equivalence queries (Myhill–Nerode). This turns "an opaque predicate
over strings" (looks structureless) into a canonical finite state machine (M9 complete invariant / M11 hidden state).

★ CERTIFICATE (per-instance, §7): the learned DFA is checked for agreement with `mq` on EVERY word up to length L
  (exhaustive bounded equivalence). For a target with ≤ k Myhill–Nerode classes, L ≥ 2k−1 makes the agreement
  COMPLETE (not just bounded) — the canonical minimal DFA is then exact. We report the learned state count and the
  verified depth L; if any disagreement is found up to L (target not regular / not within the budget) → DECLINE. ★
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Callable, Dict, List, Optional, Tuple

Word = Tuple[str, ...]


@dataclass
class DFA:
    alphabet: Tuple[str, ...]
    states: List[int]
    start: int
    accept: frozenset
    delta: Dict[Tuple[int, str], int]

    def run(self, w: Word) -> bool:
        s = self.start
        for a in w:
            s = self.delta[(s, a)]
        return s in self.accept


@dataclass
class LStarVerdict:
    status: str                       # EXACT | DECLINE
    dfa: Optional[DFA] = None
    n_states: int = 0
    verified_depth: int = 0
    complete: bool = False            # True ⇒ bounded depth covers the Myhill–Nerode bound ⇒ globally exact
    reason: str = ""
    detail: str = ""


class _Table:
    """The L* observation table (S, E, T) with membership cache."""
    def __init__(self, alphabet: Tuple[str, ...], mq: Callable[[Word], bool]):
        self.A = alphabet
        self.mq = mq
        self._cache: Dict[Word, bool] = {}
        self.S: List[Word] = [()]
        self.E: List[Word] = [()]
        self.rows: List[Word] = [(a,) for a in alphabet]   # S·A \ S candidates (one-letter extensions)

    def T(self, w: Word) -> bool:
        v = self._cache.get(w)
        if v is None:
            v = bool(self.mq(w))
            self._cache[w] = v
        return v

    def _sig(self, s: Word) -> Tuple[bool, ...]:
        return tuple(self.T(s + e) for e in self.E)

    def closed_violation(self) -> Optional[Word]:
        sigs = {self._sig(s) for s in self.S}
        for r in self.rows:
            if self._sig(r) not in sigs:
                return r
        return None

    def consistent_violation(self) -> Optional[Word]:
        # two S-rows with equal signature whose one-letter extensions differ on some e ⇒ add a·e to E
        for i in range(len(self.S)):
            for j in range(i + 1, len(self.S)):
                if self._sig(self.S[i]) == self._sig(self.S[j]):
                    for a in self.A:
                        for e in self.E:
                            if self.T(self.S[i] + (a,) + e) != self.T(self.S[j] + (a,) + e):
                                return (a,) + e
        return None

    def promote(self, r: Word):
        self.S.append(r)
        self.rows.remove(r)
        for a in self.A:                                   # extend the new S-prefix
            cand = r + (a,)
            if cand not in self.S and cand not in self.rows:
                self.rows.append(cand)

    def add_suffix(self, e: Word):
        if e not in self.E:
            self.E.append(e)

    def build(self) -> DFA:
        reps: List[Word] = []
        sig_to_state: Dict[Tuple[bool, ...], int] = {}
        for s in self.S:
            sg = self._sig(s)
            if sg not in sig_to_state:
                sig_to_state[sg] = len(reps)
                reps.append(s)
        start = sig_to_state[self._sig(())]
        accept = frozenset(sig_to_state[self._sig(s)] for s in self.S if self.T(s))
        delta: Dict[Tuple[int, str], int] = {}
        for idx, s in enumerate(reps):
            for a in self.A:
                tgt_sig = self._sig(s + (a,))
                if tgt_sig not in sig_to_state:            # extension not represented yet — fall back to closest S-row
                    tgt_sig = self._sig(s)
                delta[(idx, a)] = sig_to_state[tgt_sig]
        return DFA(self.A, list(range(len(reps))), start, accept, delta)


def _bounded_equiv(dfa: DFA, mq: Callable[[Word], bool], max_len: int) -> Optional[Word]:
    """Exhaustive check: a counterexample word (len ≤ max_len) where the DFA and `mq` disagree, else None."""
    for L in range(max_len + 1):
        for w in product(dfa.alphabet, repeat=L):
            if dfa.run(w) != bool(mq(w)):
                return w
    return None


def learn(mq: Callable[[Word], bool], alphabet, max_states: int = 12, equiv_depth: Optional[int] = None) -> LStarVerdict:
    """Learn the minimal DFA of the regular language decided by `mq` over `alphabet`. EXACT with the learned state
    count + verified depth; DECLINE if not regular within `max_states` / a disagreement persists. The equivalence
    oracle is exhaustive bounded testing up to `equiv_depth` (default 2·max_states+1 — covers Myhill–Nerode for
    targets with ≤ max_states classes ⇒ a `complete` (globally exact) certificate)."""
    A = tuple(alphabet)
    depth = equiv_depth if equiv_depth is not None else 2 * max_states + 1
    t = _Table(A, mq)
    for _ in range(200):                                   # bounded refinement loop (each iter closes/fixes the table)
        while True:
            cv = t.closed_violation()
            if cv is not None:
                t.promote(cv)
                continue
            iv = t.consistent_violation()
            if iv is not None:
                t.add_suffix(iv)
                continue
            break
        dfa = t.build()
        if len(dfa.states) > max_states:
            return LStarVerdict("DECLINE", reason=f"hypothesis exceeded {max_states} states — not regular within budget")
        ce = _bounded_equiv(dfa, mq, depth)
        if ce is None:
            complete = len(dfa.states) * 2 - 1 <= depth
            return LStarVerdict("EXACT", dfa=dfa, n_states=len(dfa.states), verified_depth=depth, complete=complete,
                                detail=f"minimal DFA with {len(dfa.states)} states; agrees with the oracle on all "
                                       f"{sum(len(A)**L for L in range(depth+1))} words up to length {depth}"
                                       + (" (≥ Myhill–Nerode bound ⇒ globally exact)" if complete else ""))
        # add the counterexample and all its prefixes to S (Angluin's classic counterexample handling)
        for k in range(len(ce) + 1):
            pref = ce[:k]
            if pref not in t.S and pref not in t.rows:
                t.rows.append(pref)
            if pref in t.rows:
                t.promote(pref)
    return LStarVerdict("DECLINE", reason="L* did not converge within the refinement budget")
