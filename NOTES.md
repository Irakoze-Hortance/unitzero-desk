# NOTES

Stack: FastAPI + SQLite (plain SQL, hand-rolled migration runner), vanilla JS frontend served by the API, Docker Compose. No stretch item chosen; I preferred a small, tested core.

## 1. Design

**Data model** (all state lives in the database; the JWT is stateless, the browser keeps only the token in `sessionStorage`):

```
users(id, email UNIQUE, name, password_hash, role, active)
episodes(episode_id PK, robot_id, task_name, recorded_at, duration_seconds, operator_name, quality)
requests(id, client_id -> users, task_name, episodes_requested, deadline, notes, status, created_at)
status_history(id, request_id -> requests, from_status, to_status, user_id -> users, at)
assignments(episode_id PK -> episodes, request_id -> requests)
```

Code layout: `controllers/` (HTTP only), `services/` (rules + SQL), `models/` (schemas, transition table), `deps.py` (auth). Services raise `DomainError`; `main.py` maps it to a response.

**Hardest decisions**

1. *Where to enforce "an episode is on at most one request".* I made `episode_id` the primary key of `assignments`, so the database refuses a second assignment even under concurrent requests. A check-then-insert in Python would race. Batches are all-or-nothing (one commit at the end).
2. *Import policy for messy data.* I normalise what is unambiguous (case, whitespace, ISO / day-first dates, timezone to UTC) and skip what is not (unknown robot, bad quality, bad duration, missing required field, malformed row), with a reason and line number for every skip. Existing episodes are never overwritten (first write wins), which is what makes re-imports idempotent. Cost: a corrected row in a later file will not update an old one.
3. *Status changes.* A transition table maps `(from, to)` to the role that owns the step. The update is `... WHERE id=? AND status=?` (compare-and-swap), so two simultaneous changes cannot both succeed. History is written in the same transaction.

**Ambiguities I decided** (brief was silent): only clients create requests (admins do not); admin = operator for workflow steps; episodes can be assigned while a request is submitted / in progress / rejected but not once delivered or accepted; over-assigning beyond `episodes_requested` is allowed; "time to delivered" uses the first delivery; analytics filter requests by `created_at`; task names are lower-cased and whitespace-collapsed on both sides so request and episode names match; `dd/mm/yyyy` is read day-first; timestamps are naive UTC.

## 2. Left out / next

Left out: unassigning episodes, request edit/cancel, pagination on `/requests`, rate limiting, token revocation, a UI for history / analytics / user admin (the API supports them), import size limits, an import-run audit table. (CI is a minimal GitHub Actions workflow that only runs the tests.)

With two more days: Postgres + Alembic; unassign + audit trail of imports; SSE for live status updates (stretch); browser tests for the frontend; login rate limiting.



## 3. Security

- Passwords: scrypt with a per-user random salt, constant-time compare, a dummy hash for unknown emails so response time does not reveal which accounts exist. Seed passwords are hashed, never stored plain.
- Tokens: HS256 JWT, 8h expiry (configurable), `exp` and `sub` required. `SECRET_KEY` comes from the environment and the app refuses to start if it is missing or under 32 characters. The user row is re-read on every request, so deactivation and role changes take effect immediately.
- Validation: Pydantic on every body (positive counts, real dates, role/status enums), whitelist of quality and robot values on import, parameterised SQL everywhere (the only f-strings insert fixed column fragments, never user input). A client asking for another client's request gets 404, not 403. The frontend writes server data with `textContent`, never `innerHTML`.

**Two things I would worry about most:**
1. *Credential attacks and token theft.* There is no rate limiting on `/login`, and the token sits in `sessionStorage`, so any XSS would hand over an account. JWTs cannot be revoked before expiry. Fix: rate limit / lockout, short-lived tokens with refresh, httpOnly cookies with CSRF protection.
2. *Unbounded input and authorization drift.* `/import` has no size limit (memory and time DoS), and per-object checks live in service code, so a new endpoint that forgets `get_request` leaks data. Fix: body size limits and streaming import; a central authorization layer with tests that enumerate every route against every role.

## 4. Scale

- **Analytics at 5 million episodes:** all aggregation runs in the database. `(recorded_at, robot_id)` serves the per-day/per-robot query as an index scan, so cost grows with the rows in the date range, not the table. Top-5-good-tasks has no good index for a date range, so a wide range scans a lot. Fix: partial index on `quality='good'` or a nightly rollup table (day, robot, task, quality, count); on Postgres use `percentile_cont` for the median and partition `episodes` by month.
- **10× users:** SQLite has a single writer, so the first break is concurrent writes. Move to Postgres with a pool and several workers; scrypt makes logins CPU-heavy, so cap login rate.
- **100× episodes:** the import breaks first (row-by-row inserts in Python). Use `COPY` into a staging table, then `INSERT ... ON CONFLICT DO NOTHING`, with a background job and progress reporting. The episode list uses `LIMIT/OFFSET`, which degrades at depth; switch to keyset pagination.
- **If production used Postgres:** swap `date(:b,'+1 day')`, `julianday` and `substr` for native date types and operators, use `ON CONFLICT`, and replace the hand-rolled migration runner with Alembic.

## 5. AI tooling

I used Claude (Anthropic) as a coding assistant for scaffolding the API,  tests,  the frontend, and drafting these notes. I reviewed and ran the code myself and can explain and modify every part of it.
