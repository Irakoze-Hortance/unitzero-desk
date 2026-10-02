#!/bin/sh
set -e
# Migrations + seed users only (idempotent). Episodes are imported through the UI or POST /import.
if [ -f seed/users.json ]; then
  python -m app.seed seed
else
  echo "seed/users.json missing: running migrations only"
  python -c "from app.db import migrate; migrate()"
fi
exec "$@"