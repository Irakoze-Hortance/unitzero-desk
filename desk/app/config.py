"""Settings come from the environment (a local .env is loaded if present; real env vars win)."""
import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "SECRET_KEY is missing or too short (need >= 32 chars). Generate one with:\n"
        "  python -c \"import secrets; print(secrets.token_urlsafe(48))\"")

ACCESS_TOKEN_MINUTES = int(os.environ.get("ACCESS_TOKEN_MINUTES", "480"))
