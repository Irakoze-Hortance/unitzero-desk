# Dataset Request Desk – backend

    pip install -r requirements.txt
    python -m app.seed seed            # migrate + create users from seed/users.json + import seed/episodes.csv
    cp .env.example .env   # then set SECRET_KEY
    uvicorn app.main:app
    pytest                             # tests

Import via API: `curl -X POST localhost:8000/import -H "Authorization: Bearer $T" -H "Content-Type: text/csv" --data-binary @seed/episodes.csv`
UI: http://localhost:8000/   (API docs: /docs)

## Layout
    app/main.py          app wiring: middleware/logging, error handler, routers
    app/controllers/     HTTP only: routes, params, auth dependencies
    app/services/        business rules + SQL (transitions, assignment, import, analytics)
    app/models/          pydantic schemas (schemas.py) and domain constants (domain.py)
    app/deps.py          db connection, current_user, role checks
    app/security.py      password hashing, JWT
    app/db.py            connection + migration runner

## Docker
    cp .env.example .env        # set SECRET_KEY
    docker compose up --build   # migrate + seed + API on http://localhost:8000
    docker compose run --rm api pytest
    docker compose down -v      # stop and wipe the database volume
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"