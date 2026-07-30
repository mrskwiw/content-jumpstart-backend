"""Integration tests for the content atomization endpoint (POST /api/posts/atomize)."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import User
from backend.utils.auth import get_password_hash


@pytest.fixture
def client(db_session):
    return TestClient(app)


@pytest.fixture
def auth_headers(db_session):
    user = User(
        id="user-atomize",
        email="atomize@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Atomizer",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    resp = client_login(db_session)
    return {"Authorization": f"Bearer {resp}"}


def client_login(db_session):
    c = TestClient(app)
    r = c.post(
        "/api/auth/login",
        json={
            "email": "atomize@example.com",
            "password": "testpass123",  # pragma: allowlist secret
        },
    )
    return r.json()["access_token"]


_LONG = (
    "Answer-engine visibility is the new SEO battleground. "
    "Buyers now ask ChatGPT and Perplexity before they ever touch Google. "
    "The brands that get cited inside those answers win the consideration set. "
    "Getting cited means structured content, clear claims, and self-contained answers. "
    "Most teams still optimize only for blue links and miss this entirely. "
    "Start by marking up your best article with schema and a crisp summary. "
    "Then measure which answer engines send you traffic and double down there."
)


def test_atomize_requires_auth(client):
    r = client.post("/api/posts/atomize", json={"text": _LONG})
    assert r.status_code == 401


def test_atomize_returns_thread_and_quotes(client, auth_headers):
    r = client.post("/api/posts/atomize", json={"text": _LONG}, headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["thread_count"] == len(body["thread"])
    assert body["thread_count"] >= 2  # long text splits into multiple posts
    # multi-post threads are numbered
    assert body["thread"][0].endswith(f"(1/{body['thread_count']})")
    assert isinstance(body["pull_quotes"], list)


def test_atomize_respects_max_chars(client, auth_headers):
    r = client.post(
        "/api/posts/atomize", json={"text": _LONG, "max_chars": 120}, headers=auth_headers
    )
    assert r.status_code == 200
    for post in r.json()["thread"]:
        assert len(post) <= 120


def test_atomize_respects_max_quotes(client, auth_headers):
    r = client.post(
        "/api/posts/atomize", json={"text": _LONG, "max_quotes": 2}, headers=auth_headers
    )
    assert r.status_code == 200
    assert len(r.json()["pull_quotes"]) <= 2


def test_atomize_blank_text_is_400(client, auth_headers):
    r = client.post("/api/posts/atomize", json={"text": "   "}, headers=auth_headers)
    assert r.status_code == 400


def test_atomize_empty_text_is_422(client, auth_headers):
    # min_length=1 -> schema validation rejects an empty string before the handler.
    r = client.post("/api/posts/atomize", json={"text": ""}, headers=auth_headers)
    assert r.status_code == 422


def test_atomize_oversized_text_is_rejected(client, auth_headers):
    # max_length caps the input so the endpoint can't be a DoS primitive.
    r = client.post("/api/posts/atomize", json={"text": "x " * 30000}, headers=auth_headers)
    assert r.status_code == 422
