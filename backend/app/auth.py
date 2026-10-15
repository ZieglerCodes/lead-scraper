"""Verify Supabase's asymmetric access JWTs on every protected request.

No Supabase service-role credential or legacy shared JWT secret is needed.
The JWKS comes from the trusted SUPABASE_URL environment variable, never
from the token or the incoming HTTP request.
"""
import os
import uuid
from functools import lru_cache
from urllib.error import URLError
from urllib.parse import urlparse

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError, PyJWKClientConnectionError

bearer = HTTPBearer(auto_error=False)
ALGORITHMS = ["ES256", "RS256"]


def supabase_url() -> str:
    raw = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    parts = urlparse(raw)
    # Local dev auth still uses a real hosted Supabase project. Avoid
    # accepting a token-controlled JWKS endpoint or non-HTTPS remote URL.
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise RuntimeError("Set SUPABASE_URL to your project's HTTPS URL")
    return raw


@lru_cache(maxsize=8)
def jwks_client(project_url: str) -> PyJWKClient:
    return PyJWKClient(f"{project_url}/auth/v1/.well-known/jwks.json", cache_keys=True, lifespan=300, timeout=5)


def verify_access_token(token: str) -> dict:
    try:
        project_url = supabase_url()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Supabase auth not configured on server") from exc
    try:
        signing_key = jwks_client(project_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS,
            audience="authenticated",
            issuer=f"{project_url}/auth/v1",
            options={"require": ["sub", "iat", "exp", "iss", "aud"]},
            leeway=30,
        )
        # Distinguish a user's session from a service or anonymous API token.
        if claims.get("role") != "authenticated" or not claims.get("session_id"):
            raise InvalidTokenError("Not a user session")
        uuid.UUID(str(claims["sub"]))
        return claims
    except (PyJWKClientConnectionError, URLError, OSError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Unable to verify session with identity provider") from exc
    except (InvalidTokenError, PyJWKClientError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session", headers={"WWW-Authenticate": "Bearer"}) from exc


def current_user(credentials: HTTPAuthorizationCredentials | None = Security(bearer)) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    claims = verify_access_token(credentials.credentials)
    return str(uuid.UUID(str(claims["sub"])))
