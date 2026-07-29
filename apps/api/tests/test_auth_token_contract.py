"""Auth token contract tests.

These lock the exact contract the frontend session boundary depends on:

* what `/auth/login` puts in `TokenResponse` (field names + a string user id),
* that an access token is accepted by `/auth/me` while a refresh token is not,
* that `/auth/refresh` mints a usable access token,
* that expired / malformed / wrong-type tokens yield 401.

No database is required: `get_session` is overridden with a fake session that
returns a stub user, so these run anywhere `pytest` runs.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from ice_api.auth_utils import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    get_access_token_expire_minutes,
    get_refresh_token_expire_days,
)
from ice_api.main import app
from ice_shared.db import get_session

USER_ID = uuid.UUID("0f8f7a2e-1c3d-4b5a-9e6f-2a1b3c4d5e6f")
TENANT_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


class StubUser:
    """Minimal stand-in for the `User` ORM row touched by the auth paths."""

    id = USER_ID
    tenant_id = TENANT_ID
    email = "learner@example.com"
    name = "Learner"
    avatar_url = None
    xp = 0
    streak_count = 0
    streak_color = None
    token_version = 1
    is_active = True
    is_verified = True


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    """Async session stub: every lookup resolves to `user` (or None)."""

    def __init__(self, user):
        self.user = user
        # `get_current_user` inspects the dialect to decide on `SET LOCAL`.
        self.bind = type("Bind", (), {"dialect": type("D", (), {"name": "sqlite"})()})()

    async def execute(self, *_args, **_kwargs):
        return _Result(self.user)


@pytest.fixture
def client_for():
    """Build a TestClient whose DB session yields the given user."""
    created = []

    def _build(user=StubUser()):
        async def _override():
            yield FakeSession(user)

        app.dependency_overrides[get_session] = _override
        c = TestClient(app)
        created.append(c)
        return c

    yield _build
    app.dependency_overrides.pop(get_session, None)
    for c in created:
        c.close()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def access_token(**overrides) -> str:
    data = {"sub": str(USER_ID), "tv": 1}
    data.update(overrides)
    return create_access_token(data)


# --- Token shape ------------------------------------------------------------


def test_access_token_claims_match_frontend_expectations():
    claims = jose_jwt.decode(access_token(), SECRET_KEY, algorithms=[ALGORITHM])

    assert claims["sub"] == str(USER_ID)
    assert claims["type"] == "access"
    # The session route reads `exp` to size the cookie; it must be present.
    assert isinstance(claims["exp"], int)


def test_refresh_token_is_typed_distinctly_from_access():
    claims = jose_jwt.decode(
        create_refresh_token({"sub": str(USER_ID), "tv": 1}),
        SECRET_KEY,
        algorithms=[ALGORITHM],
    )

    assert claims["type"] == "refresh"


def test_token_lifetimes_match_the_cookie_policy():
    # apps/web/src/app/auth/session/route.ts uses these as cookie fallbacks.
    assert get_access_token_expire_minutes() == 60
    assert get_refresh_token_expire_days() == 7


def test_sub_is_a_uuid_string_not_an_integer():
    claims = jose_jwt.decode(access_token(), SECRET_KEY, algorithms=[ALGORITHM])

    assert isinstance(claims["sub"], str)
    # AuthUser.id is typed `string` on the frontend precisely because of this.
    uuid.UUID(claims["sub"])


# --- /auth/me ---------------------------------------------------------------


def test_me_accepts_a_freshly_minted_access_token(client_for):
    resp = client_for().get("/api/v1/auth/me", headers=auth(access_token()))

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == StubUser.email
    assert str(body["id"]) == str(USER_ID)


def test_me_returns_the_fields_the_frontend_renders(client_for):
    body = client_for().get("/api/v1/auth/me", headers=auth(access_token())).json()

    # AuthUser in apps/web/src/lib/auth.ts
    for field in ("id", "name", "email", "avatar_url", "xp", "streak_count"):
        assert field in body, f"missing {field}"


def test_me_rejects_a_refresh_token_used_as_an_access_token(client_for):
    token = create_refresh_token({"sub": str(USER_ID), "tv": 1})

    resp = client_for().get("/api/v1/auth/me", headers=auth(token))

    assert resp.status_code == 401


def test_me_rejects_an_expired_access_token(client_for):
    token = create_access_token(
        {"sub": str(USER_ID), "tv": 1}, expires_delta=timedelta(minutes=-5)
    )

    resp = client_for().get("/api/v1/auth/me", headers=auth(token))

    assert resp.status_code == 401


def test_me_rejects_a_malformed_token(client_for):
    resp = client_for().get("/api/v1/auth/me", headers=auth("not-a-jwt"))

    assert resp.status_code == 401


def test_me_rejects_a_token_signed_with_the_wrong_key(client_for):
    forged = jose_jwt.encode(
        {"sub": str(USER_ID), "tv": 1, "type": "access", "exp": 9999999999},
        "attacker-key",
        algorithm=ALGORITHM,
    )

    resp = client_for().get("/api/v1/auth/me", headers=auth(forged))

    assert resp.status_code == 401


def test_me_requires_a_token_at_all(client_for):
    assert client_for().get("/api/v1/auth/me").status_code == 401


def test_me_rejects_a_stale_token_version(client_for):
    # Password change bumps token_version; old tokens must stop working.
    resp = client_for().get("/api/v1/auth/me", headers=auth(access_token(tv=0)))

    assert resp.status_code == 401


def test_me_rejects_a_token_for_an_unknown_user(client_for):
    resp = client_for(None).get("/api/v1/auth/me", headers=auth(access_token()))

    assert resp.status_code == 401


# --- /auth/refresh ----------------------------------------------------------


def test_refresh_returns_an_access_token_that_me_accepts(client_for):
    client = client_for()
    refresh = create_refresh_token({"sub": str(USER_ID), "tv": 1})

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})

    assert resp.status_code == 200
    new_access = resp.json()["access_token"]
    # The frontend stores this verbatim, so it must authenticate on its own.
    assert client.get("/api/v1/auth/me", headers=auth(new_access)).status_code == 200


def test_refresh_rejects_an_access_token(client_for):
    resp = client_for().post(
        "/api/v1/auth/refresh", json={"refresh_token": access_token()}
    )

    assert resp.status_code == 401


def test_refresh_rejects_an_expired_refresh_token(client_for):
    expired = jose_jwt.encode(
        {"sub": str(USER_ID), "tv": 1, "type": "refresh", "exp": 1},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    resp = client_for().post("/api/v1/auth/refresh", json={"refresh_token": expired})

    assert resp.status_code == 401


def test_refresh_rejects_a_malformed_refresh_token(client_for):
    resp = client_for().post(
        "/api/v1/auth/refresh", json={"refresh_token": "garbage"}
    )

    assert resp.status_code == 401


def test_refresh_rejects_a_revoked_session(client_for):
    revoked = create_refresh_token({"sub": str(USER_ID), "tv": 0})

    resp = client_for().post("/api/v1/auth/refresh", json={"refresh_token": revoked})

    assert resp.status_code == 401
