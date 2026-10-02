import os, sqlite3
from pathlib import Path

from . import config  # noqa: F401  (loads .env before DB_PATH is read)


def conn():
    c = sqlite3.connect(os.environ.get("DB_PATH", "data.db"))
    c.row_factory = sqlite3.Row
    c.execute("pragma foreign_keys=on")
    return c


def migrate():
    """Apply migrations/*.sql in filename order, once each."""
    c = conn()
    c.execute("create table if not exists schema_migrations(name text primary key)")
    done = {r[0] for r in c.execute("select name from schema_migrations")}
    for f in sorted((Path(__file__).parent.parent / "migrations").glob("*.sql")):
        if f.name not in done:
            c.executescript(f.read_text())
            c.execute("insert into schema_migrations values(?)", (f.name,))
            c.commit()
    c.close()
