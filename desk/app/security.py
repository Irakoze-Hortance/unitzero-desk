import hashlib, hmac, os
from datetime import datetime, timedelta, timezone

import jwt

from . import config

ALGO = "HS256"


def _scrypt(pw: str, salt: bytes) -> str:
    return hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1).hex()


def hash_pw(pw: str) -> str:
    salt = os.urandom(16)
    return salt.hex() + ":" + _scrypt(pw, salt)


def check_pw(pw: str, stored: str) -> bool:
    salt, digest = stored.split(":")
    return hmac.compare_digest(_scrypt(pw, bytes.fromhex(salt)), digest)


# Checked when the email is unknown, so "no such user" and "wrong password" take the same time.
DUMMY_HASH = hash_pw(os.urandom(8).hex())


def make_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=config.ACCESS_TOKEN_MINUTES)}
    return jwt.encode(claims, config.SECRET_KEY, ALGO)


def read_token(token: str) -> int:
    claims = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGO], options={"require": ["exp", "sub"]})
    return int(claims["sub"])
