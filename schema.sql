-- Mr. Jeffrey — SQLite schema / migration (idempotent: CREATE TABLE IF NOT EXISTS).
-- ★ SECURITY INVARIANT ★: we store the user's WORK (request / generated code / verification label / time)
-- but NEVER the LLM API key. There is deliberately NO api_key / token / secret column anywhere below — the
-- LLM key is LEVEL-1 (entered per request, used once, dropped; never persisted). See auth.py + claude_agent.py.
-- Passwords are stored ONLY as a salted KDF hash (bcrypt or scrypt) — never plaintext.

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT    NOT NULL UNIQUE,
    pw_hash     TEXT    NOT NULL,          -- "bcrypt$..." or "scrypt$salt$hash" — NEVER plaintext
    pw_algo     TEXT    NOT NULL,          -- which KDF produced pw_hash
    nickname    TEXT,
    created_at  TEXT    NOT NULL
    -- NOTE: no api_key column — by design. The LLM key is never stored.
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT    PRIMARY KEY,       -- sha256 of the random session token (raw token only in the cookie)
    user_id     INTEGER NOT NULL,
    persistent  INTEGER NOT NULL DEFAULT 0,-- 1 = "remember me" (long-lived), 0 = browser-session
    expires_at  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS work_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    request     TEXT    NOT NULL,          -- the user's instruction
    code        TEXT,                      -- the generated code
    status      TEXT,                      -- VERIFIED / UNRESOLVED / ...
    proof_tier  TEXT,                      -- PROVEN / TESTED / ... (verification label)
    created_at  TEXT    NOT NULL,
    -- NOTE: no api_key column — by design. We save the work, not the key.
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_work_user ON work_history(user_id);
