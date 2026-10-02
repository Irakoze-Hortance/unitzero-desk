from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import conn
from .errors import DomainError
from .security import read_token


bearer = HTTPBearer(auto_error=False)  # makes the Authorize button appear in /docs


def db():
    c = conn()
    try:
        yield c  # services commit explicitly; anything uncommitted is dropped on close
    finally:
        c.close()


def current_user(req: Request, cred: HTTPAuthorizationCredentials = Depends(bearer), c=Depends(db)):
    try:
        uid = read_token(cred.credentials)
    except Exception:
        raise DomainError(401, "invalid or missing token")
    u = c.execute("select id,email,role,active from users where id=?", (uid,)).fetchone()
    if not u or not u["active"]:  # re-read every request: deactivation / role change apply immediately
        raise DomainError(401, "invalid or missing token")
    req.state.uid = u["id"]
    return u


def role(*roles):
    def dep(u=Depends(current_user)):
        if u["role"] not in roles:
            raise DomainError(403, "forbidden")
        return u
    return dep
