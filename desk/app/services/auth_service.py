import sqlite3

from ..errors import DomainError
from ..security import DUMMY_HASH, check_pw, hash_pw, make_token


def login(c, email, password):
    u = c.execute("select * from users where email=?", (email.strip().lower(),)).fetchone()
    ok = check_pw(password, u["password_hash"] if u else DUMMY_HASH)
    if not u or not u["active"] or not ok:
        raise DomainError(401, "bad credentials")
    return {"token": make_token(u["id"]), "role": u["role"], "name": u["name"]}


def create_user(c, b):
    try:
        cur = c.execute("insert into users(email,name,password_hash,role) values(?,?,?,?)",
                        (b.email.strip().lower(), b.name, hash_pw(b.password), b.role))
    except sqlite3.IntegrityError:
        raise DomainError(409, "email already exists")
    c.commit()
    return {"id": cur.lastrowid}


def patch_user(c, me, uid, b):
    if uid == me["id"]:
        raise DomainError(409, "admins cannot change their own role/active flag")
    if not c.execute("select 1 from users where id=?", (uid,)).fetchone():
        raise DomainError(404, "no such user")
    if b.role:
        c.execute("update users set role=? where id=?", (b.role, uid))
    if b.active is not None:
        c.execute("update users set active=? where id=?", (int(b.active), uid))
    c.commit()
    return {"ok": True}
