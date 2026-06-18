"""
Mr. Jeffrey — authentication + persistence (SQLite).  ★ The LLM API key is NEVER touched here. ★
=================================================================================================
This module owns users, sessions, and saved WORK. It does NOT import claude_agent and never sees the LLM
key — that key is LEVEL-1 (entered per request, used once, dropped; see claude_agent.py). What we persist:
  • users      — email + a salted-KDF password HASH (bcrypt, or stdlib scrypt fallback). NEVER plaintext.
  • sessions   — sha256 of a random token (the raw token lives only in the cookie), + expiry + persistent.
  • work_history — the user's request / generated code / verification label / time. NO api_key column.

Security:
  • passwords: bcrypt if installed, else hashlib.scrypt (RFC 7914) — both salted, slow KDFs. Verify by hash.
  • sessions : a high-entropy random token, HMAC-signed with a secret from the ENV/.env (never hardcoded);
    only the token's sha256 is stored server-side. "remember me" → long-lived; else a short, session-style life.
  • password policy (server-side enforced): ≥8 chars with lower + upper + digit + special.
(auth.py may use `os`/`sqlite3` — the no-`os` rule is specifically claude_agent's, to fence the LLM key.)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_BASE = Path(__file__).parent
_SCHEMA = _BASE / "schema.sql"
DB_PATH = os.environ.get("MRJ_DB") or str(_BASE / "mrjeffrey.db")

PERSISTENT_DAYS = 30      # "remember me" lifetime
SESSION_HOURS = 12        # non-persistent (browser-session) server-side lifetime


def _load_env() -> None:
    """Load KEY=VALUE lines from .env into the environment (without overwriting). Never logs values."""
    env = _BASE / ".env"
    if not env.is_file():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _secret() -> bytes:
    """Session-signing secret from the env/.env (NOT hardcoded). Absent → a per-process random secret
    (dev only; sessions won't survive a restart — set MRJ_SECRET in .env for production)."""
    _load_env()
    s = os.environ.get("MRJ_SECRET")
    if not s:
        s = getattr(_secret, "_ephemeral", None) or secrets.token_urlsafe(48)
        _secret._ephemeral = s   # stable within the process
    return s.encode()


# ── DB ──────────────────────────────────────────────────────────────────────────────────────────────
def _conn(path: Optional[str] = None) -> sqlite3.Connection:
    c = sqlite3.connect(path or DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init_db(path: Optional[str] = None) -> None:
    with _conn(path) as c:
        c.executescript(_SCHEMA.read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── password hashing (bcrypt → scrypt fallback) + policy ─────────────────────────────────────────────
def _have_bcrypt() -> bool:
    try:
        import bcrypt  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def hash_password(pw: str) -> Tuple[str, str]:
    """Return (algo, stored_hash). NEVER returns or stores plaintext."""
    if _have_bcrypt():
        import bcrypt
        return ("bcrypt", bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return ("scrypt", f"{salt.hex()}${dk.hex()}")


def verify_password(pw: str, algo: str, stored: str) -> bool:
    try:
        if algo == "bcrypt":
            import bcrypt
            return bcrypt.checkpw(pw.encode(), stored.encode())
        if algo == "scrypt":
            salt_hex, dk_hex = stored.split("$", 1)
            dk = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt_hex), n=16384, r=8, p=1, dklen=32)
            return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:  # noqa: BLE001
        return False
    return False


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_password(pw: str) -> Tuple[bool, str]:
    """Server-side policy (authoritative): ≥8 chars, lower + upper + digit + special."""
    if len(pw or "") < 8:
        return (False, "비밀번호는 8자 이상이어야 합니다.")
    if not re.search(r"[a-z]", pw):
        return (False, "소문자를 포함해야 합니다.")
    if not re.search(r"[A-Z]", pw):
        return (False, "대문자를 포함해야 합니다.")
    if not re.search(r"[0-9]", pw):
        return (False, "숫자를 포함해야 합니다.")
    if not re.search(r"[^A-Za-z0-9]", pw):
        return (False, "특수문자를 포함해야 합니다.")
    return (True, "")


# ── signup / login / sessions ────────────────────────────────────────────────────────────────────────
def signup(email: str, password: str, nickname: str = "", path: Optional[str] = None) -> Dict:
    email = (email or "").strip().lower()
    if not _EMAIL.match(email):
        return {"ok": False, "message": "올바른 이메일을 입력해 주세요."}
    ok, why = validate_password(password)
    if not ok:
        return {"ok": False, "message": why}
    algo, h = hash_password(password)
    try:
        with _conn(path) as c:
            c.execute("INSERT INTO users(email, pw_hash, pw_algo, nickname, created_at) VALUES (?,?,?,?,?)",
                      (email, h, algo, (nickname or "").strip()[:40] or None, _now().isoformat()))
        return {"ok": True, "message": "created"}
    except sqlite3.IntegrityError:
        return {"ok": False, "message": "이미 가입된 이메일입니다."}


def _sign(token: str) -> str:
    return hmac.new(_secret(), token.encode(), hashlib.sha256).hexdigest()[:32]


def _new_session(user_id: int, remember: bool, path: Optional[str] = None) -> Dict:
    token = secrets.token_urlsafe(32)
    th = hashlib.sha256(token.encode()).hexdigest()
    life = timedelta(days=PERSISTENT_DAYS) if remember else timedelta(hours=SESSION_HOURS)
    expires = _now() + life
    with _conn(path) as c:
        c.execute("INSERT INTO sessions(token_hash, user_id, persistent, expires_at, created_at) "
                  "VALUES (?,?,?,?,?)", (th, user_id, 1 if remember else 0, expires.isoformat(), _now().isoformat()))
    return {"cookie": f"{token}.{_sign(token)}", "expires_at": expires, "persistent": remember}


def login(email: str, password: str, remember: bool = False, path: Optional[str] = None) -> Dict:
    email = (email or "").strip().lower()
    with _conn(path) as c:
        row = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not row or not verify_password(password, row["pw_algo"], row["pw_hash"]):
        return {"ok": False, "message": "이메일 또는 비밀번호가 올바르지 않습니다."}
    sess = _new_session(row["id"], remember, path)
    return {"ok": True, **sess}


def _parse_cookie(cookie_value: str) -> Optional[str]:
    """Verify the HMAC signature and return the raw token (constant-time); None if tampered/malformed."""
    if not cookie_value or "." not in cookie_value:
        return None
    token, sig = cookie_value.rsplit(".", 1)
    return token if hmac.compare_digest(_sign(token), sig) else None


def verify_session(cookie_value: str, path: Optional[str] = None) -> Optional[Dict]:
    token = _parse_cookie(cookie_value)
    if not token:
        return None
    th = hashlib.sha256(token.encode()).hexdigest()
    with _conn(path) as c:
        s = c.execute("SELECT * FROM sessions WHERE token_hash=?", (th,)).fetchone()
        if not s:
            return None
        if datetime.fromisoformat(s["expires_at"]) < _now():
            c.execute("DELETE FROM sessions WHERE token_hash=?", (th,))
            return None
        u = c.execute("SELECT id, email, nickname FROM users WHERE id=?", (s["user_id"],)).fetchone()
    if not u:
        return None
    return {"user_id": u["id"], "email": u["email"], "nickname": u["nickname"],
            "persistent": bool(s["persistent"]), "expires_at": s["expires_at"]}


def logout(cookie_value: str, path: Optional[str] = None) -> None:
    token = _parse_cookie(cookie_value)
    if not token:
        return
    th = hashlib.sha256(token.encode()).hexdigest()
    with _conn(path) as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (th,))


def whoami(cookie_value: str, path: Optional[str] = None) -> Dict:
    s = verify_session(cookie_value, path)
    return {"authenticated": False} if not s else {
        "authenticated": True, "email": s["email"], "nickname": s["nickname"]}


def update_profile(user_id: int, nickname: Optional[str] = None, password: Optional[str] = None,
                   path: Optional[str] = None) -> Dict:
    with _conn(path) as c:
        if nickname is not None:
            c.execute("UPDATE users SET nickname=? WHERE id=?", ((nickname or "").strip()[:40] or None, user_id))
        if password:
            ok, why = validate_password(password)
            if not ok:
                return {"ok": False, "message": why}
            algo, h = hash_password(password)
            c.execute("UPDATE users SET pw_hash=?, pw_algo=? WHERE id=?", (h, algo, user_id))
    return {"ok": True, "message": "saved"}


# ── work history (NO api_key persisted — by design) ─────────────────────────────────────────────────
def add_work(user_id: int, request: str, code: str = "", status: str = "", proof_tier: str = "",
             path: Optional[str] = None) -> None:
    with _conn(path) as c:
        c.execute("INSERT INTO work_history(user_id, request, code, status, proof_tier, created_at) "
                  "VALUES (?,?,?,?,?,?)", (user_id, (request or "")[:4000], (code or "")[:20000],
                                          status, proof_tier, _now().isoformat()))


def list_work(user_id: int, limit: int = 50, path: Optional[str] = None) -> List[Dict]:
    with _conn(path) as c:
        rows = c.execute("SELECT request, code, status, proof_tier, created_at FROM work_history "
                         "WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    return [dict(r) for r in rows]
