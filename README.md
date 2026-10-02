# Dataset Request Desk

Internal platform for a robotics data collection company: clients submit dataset requests, operators fulfil them by assigning episodes, clients accept or reject the delivery.

Stack: Python / FastAPI, SQLite (migrations in `migrations/`), vanilla JS frontend served by the API, Docker Compose. Design decisions are in [NOTES.md](NOTES.md).

## Run it

### Option A: Docker (one command)

```bash
cp .env.example .env            # then set SECRET_KEY (see below)
docker compose up --build
```

Migrations and seed users run automatically on start. Open **http://localhost:8000/** (UI) or **http://localhost:8000/docs** (API docs).
Stop with `docker compose down`; add `-v` to also wipe the database.

### Option B: Python

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # then set SECRET_KEY
python -m app.seed seed              # creates tables + users from seed/users.json
uvicorn app.main:app --reload
```

Generate a secret (>= 32 characters; the app refuses to start without one):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `SECRET_KEY` | none, required | Signs login tokens |
| `DB_PATH` | `data.db` | SQLite file (Docker uses `/data/data.db` in a volume) |
| `ACCESS_TOKEN_MINUTES` | `480` | Token lifetime |
| `LOG_LEVEL` | `INFO` | Log level |

## Run the tests

```bash
pytest                     # 7 tests, temporary database, no setup needed
docker compose run --rm api pytest     # same, inside the container
```

Covered: authorization per role, status transitions and history, assignment rules, import idempotency and skip reporting, analytics, and that the UI is served. CI (`.github/workflows/ci.yml`) runs them on every push.

## Seed users

Created from `seed/users.json` (passwords are stored hashed). Seeding creates **users only**; no episodes are loaded.

| Email | Password | Role |
|---|---|---|
| `admin@example.com` | `admin123` | admin |
| `ops1@examplw.com` | `ops123` | operations |
| `client-a@example.com` | `client123` | client |

## Import episodes

Log in as an operator or admin, then use **Import episodes (CSV)** in the UI. A report appears with rows read, imported, and every skip reason with line numbers. Or via the API:

```bash
curl -X POST localhost:8000/import -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: text/csv" --data-binary @seed/episodes.csv
```

Importing the same file again creates no duplicates (existing episodes are reported as "already in database").
A large clean file for load testing: `python3 seed/generate_episodes.py 200000 > seed/episodes_large.csv`.

## API overview

| Endpoint | Who |
|---|---|
| `POST /login`, `GET /health` | anyone |
| `POST /requests`, accept/reject via `POST /requests/{id}/status` | client |
| `GET /requests`, `GET /requests/{id}` | client (own only), staff (all) |
| `POST /requests/{id}/status` (start, deliver, rework) | operator, admin |
| `GET /episodes`, `POST /requests/{id}/episodes`, `POST /import`, `GET /analytics?from=&to=` | operator, admin |
| `POST /users`, `PATCH /users/{id}` | admin |

Interactive docs at `/docs` (log in with `POST /login`, then **Authorize** and paste the token). Every request logs one JSON line to the terminal (method, path, status, duration, user id).

## Layout

```
app/main.py          app wiring, request logging, error handler, static UI
app/controllers/     HTTP routes
app/services/        business rules, SQL, CSV importer
app/models/          request schemas, statuses and transition table
app/deps.py          db connection, current user, role checks
app/security.py      password hashing, tokens
frontend/            index.html, styles.css, app.js
migrations/          SQL migrations, applied on startup
tests/               pytest suite
```
