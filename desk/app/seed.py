import json, sys
from pathlib import Path

from .db import conn, migrate
from .security import hash_pw

def main(seed_dir="seed"):
    """Create the tables and the users from users.json. Does NOT import any episodes:
    import them through the UI (operator/admin) or POST /import, so you can see the report."""
    migrate()
    c = conn()
    data = json.loads((Path(seed_dir) / "users.json").read_text())
    created = 0
    for u in data["users"] if isinstance(data, dict) else data:
        created += c.execute("insert or ignore into users(email,name,password_hash,role) values(?,?,?,?)",
                             (u["email"].strip().lower(), u["name"], hash_pw(u["password"]), u["role"])).rowcount
    c.commit()
    print(f"users created: {created} (episodes: none imported)")


if __name__ == "__main__":
    main(*sys.argv[1:])