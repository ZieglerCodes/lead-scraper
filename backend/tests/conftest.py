"""Offline integration tests with genuine signed JWTs (no Supabase calls)."""
from datetime import datetime, timedelta, timezone
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import auth
from app.main import app

PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
USER_A = str(uuid.uuid4())
USER_B = str(uuid.uuid4())
ISSUER = "https://testproject.supabase.co/auth/v1"


class Key:
    key = PRIVATE.public_key()


class FakeJwks:
    def get_signing_key_from_jwt(self, token: str) -> Key:
        return Key()


def make_token(user_id: str = USER_A, *, expires: int = 3600, audience: str = "authenticated", issuer: str = ISSUER, role: str = "authenticated", session: bool = True, key=None):
    now = datetime.now(timezone.utc)
    claims = {"sub": user_id, "iss": issuer, "aud": audience, "role": role, "iat": now, "exp": now + timedelta(seconds=expires)}
    if session:
        claims["session_id"] = str(uuid.uuid4())
    return jwt.encode(claims, key or PRIVATE, algorithm="RS256", headers={"kid": "testkey"})


@pytest.fixture
def token():
    return make_token


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_SCRAPER_DATABASE_PATH", str(tmp_path / "phase3-test.sqlite3"))
    monkeypatch.setenv("SUPABASE_URL", "https://testproject.supabase.co")
    monkeypatch.setattr(auth, "jwks_client", lambda url: FakeJwks())
    with TestClient(app) as client:
        yield client


@pytest.fixture
def headers():
    def _headers(user_id=USER_A, **kwargs):
        return {"Authorization": f"Bearer {make_token(user_id, **kwargs)}"}
    return _headers
