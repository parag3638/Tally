"""End-to-end: auth flow + expense CRUD + cross-tenant isolation."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def _first_category_id(client, headers) -> int:
    r = client.get("/categories", headers=headers)
    assert r.status_code == 200
    return r.json()[0]["category_id"]


def _first_payment_method_id(client, headers) -> int:
    r = client.get("/payment_methods", headers=headers)
    assert r.status_code == 200
    return r.json()[0]["payment_method_id"]


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/expenses").status_code == 401
    assert client.get("/categories").status_code == 401


def test_full_expense_lifecycle(client, make_user):
    _, headers = make_user()
    cat = _first_category_id(client, headers)
    pm = _first_payment_method_id(client, headers)

    create = client.post(
        "/expenses",
        headers=headers,
        json={
            "date": "2026-06-01",
            "category_id": cat,
            "description": "Team lunch",
            "amount": "42.50",
            "vat": "3.50",
            "payment_method_id": pm,
            "business_personal": "business",
        },
    )
    assert create.status_code == 201, create.text
    tx_id = create.json()["transaction_id"]

    listed = client.get("/expenses", headers=headers)
    assert listed.status_code == 200
    assert any(e["transaction_id"] == tx_id for e in listed.json())

    got = client.get(f"/expenses/{tx_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["description"] == "Team lunch"

    deleted = client.delete(f"/expenses/{tx_id}", headers=headers)
    assert deleted.status_code == 200
    assert client.get(f"/expenses/{tx_id}", headers=headers).status_code == 404


def test_tenant_isolation(client, make_user):
    """User A must never see or delete user B's expenses."""
    _, headers_a = make_user()
    _, headers_b = make_user()

    cat = _first_category_id(client, headers_a)
    pm = _first_payment_method_id(client, headers_a)

    created = client.post(
        "/expenses",
        headers=headers_a,
        json={
            "date": "2026-06-02",
            "category_id": cat,
            "description": "A's private expense",
            "amount": "100.00",
            "vat": "0",
            "payment_method_id": pm,
            "business_personal": "personal",
        },
    )
    tx_id = created.json()["transaction_id"]

    # B cannot read A's expense by id...
    assert client.get(f"/expenses/{tx_id}", headers=headers_b).status_code == 404
    # ...nor delete it...
    assert client.delete(f"/expenses/{tx_id}", headers=headers_b).status_code == 404
    # ...nor see it in their list.
    b_list = client.get("/expenses", headers=headers_b).json()
    assert all(e["transaction_id"] != tx_id for e in b_list)

    # A still has it intact.
    assert client.get(f"/expenses/{tx_id}", headers=headers_a).status_code == 200


def test_duplicate_registration_conflicts(client):
    import uuid

    email = f"dupe_{uuid.uuid4().hex[:10]}@example.com"
    r1 = client.post("/auth/register", json={"email": email, "password": "supersecret123"})
    r2 = client.post("/auth/register", json={"email": email, "password": "supersecret123"})
    assert r1.status_code == 201
    assert r2.status_code == 409
