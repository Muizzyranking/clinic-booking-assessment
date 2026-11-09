from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import API_KEY, make_slots


def book(client: TestClient, slot_id="s1", email="ada@example.com", **kwargs):
    body = {"slot_id": slot_id, "name": "Ada Obi", "email": email}
    headers = kwargs.pop("headers", None)
    body.update(kwargs)
    return client.post("/bookings", json=body, headers=headers)


# level 1
def test_list_slots_and_filter(client):
    slots = [
        *make_slots(2),
        {**make_slots(1)[0], "id": "b1", "provider": "Dr Musa Bello"},
    ]
    assert client.post("/reset", json={"slots": slots}).status_code == 200
    all_slots = client.get("/slots").json()["slots"]
    assert [s["id"] for s in all_slots] == ["s1", "s2", "b1"]
    assert all(s["available"] for s in all_slots)
    musa = client.get("/slots", params={"provider": "Dr Musa Bello"}).json()["slots"]
    assert [s["id"] for s in musa] == ["b1"]
    assert (
        client.get("/slots", params={"provider": "dr musa bello"}).json()["slots"] == []
    )


def test_book_and_lookup(client):
    response = book(client)
    assert response.status_code == 201
    booking = response.json()
    assert booking["status"] == "confirmed"
    assert booking["slot_id"] == "s1"
    fetched = client.get(f"/bookings/{booking['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == booking
    slots = {s["id"]: s for s in client.get("/slots").json()["slots"]}
    assert slots["s1"]["available"] is False
    assert slots["s2"]["available"] is True


def test_lookup_missing_booking(client):
    response = client.get("/bookings/nope")
    assert response.status_code == 404
    assert "error" in response.json()


# level 2
def test_api_key_required(client):
    anonymous = TestClient(app)
    assert anonymous.get("/slots").status_code == 401
    assert anonymous.get("/slots", headers={"X-API-Key": "wrong"}).status_code == 401
    assert anonymous.post("/reset", json={"slots": []}).status_code == 401
    response = anonymous.post("/bookings", json={})
    assert response.status_code == 401
    assert set(response.json()) == {"error"}
    assert anonymous.get("/slots", headers={"X-API-Key": API_KEY}).status_code == 200


def test_validation_errors(client):
    # Each body uses its own email so the rate limiter (5/min/email) stays out of it.
    for body in [
        {},
        {"slot_id": "s1", "name": "Ada"},
        {"slot_id": "s1", "email": "a1@b.co"},
        {"name": "Ada", "email": "a2@b.co"},
        {"slot_id": "", "name": "Ada", "email": "a3@b.co"},
        {"slot_id": "s1", "name": "   ", "email": "a4@b.co"},
        {"slot_id": "s1", "name": "Ada", "email": ""},
        {"slot_id": "s1", "name": "Ada", "email": "not-an-email"},
        {"slot_id": 1, "name": "Ada", "email": "a5@b.co"},
        {"slot_id": "s1", "name": ["Ada"], "email": "a6@b.co"},
    ]:
        response = client.post("/bookings", json=body)
        assert response.status_code == 400, body
        assert set(response.json()) == {"error"}


def test_malformed_json_and_non_object(client):
    response = client.post(
        "/bookings", content="{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert set(response.json()) == {"error"}
    assert client.post("/bookings", json=["x"]).status_code == 400


def test_unknown_slot_is_404(client):
    response = book(client, slot_id="missing")
    assert response.status_code == 404
    assert response.json() == {"error": "slot not found"}


def test_started_slot_rejected(client):
    client.post(
        "/reset",
        json={
            "slots": [
                {
                    "id": "old",
                    "provider": "Dr Chioma Okafor",
                    "start": "2020-01-01T09:00:00Z",
                    "end": "2020-01-01T09:30:00Z",
                }
            ]
        },
    )
    assert book(client, slot_id="old").status_code == 400


def test_trim_and_lowercase(client):
    response = book(client, name="  Ada Obi  ", email="  Ada@Example.COM ")
    assert response.status_code == 201
    assert response.json()["name"] == "Ada Obi"
    assert response.json()["email"] == "ada@example.com"


# level 3
def test_double_booking_is_409(client):
    assert book(client).status_code == 201
    second = book(client, email="other@example.com")
    assert second.status_code == 409
    assert set(second.json()) == {"error"}


def test_cancel_frees_slot(client):
    booking = book(client).json()
    cancelled = client.delete(f"/bookings/{booking['id']}")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.get(f"/bookings/{booking['id']}").json()["status"] == "cancelled"
    assert book(client, email="other@example.com").status_code == 201


def test_cancel_errors(client):
    assert client.delete("/bookings/nope").status_code == 404
    booking = book(client).json()
    assert client.delete(f"/bookings/{booking['id']}").status_code == 200
    assert client.delete(f"/bookings/{booking['id']}").status_code == 409


#  level 4
def test_idempotent_retry_returns_same_booking(client):
    headers = {"Idempotency-Key": "key-1"}
    first = book(client, headers=headers)
    second = book(client, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    listing = client.get("/bookings", params={"email": "ada@example.com"}).json()
    assert len(listing["bookings"]) == 1


def test_idempotency_key_with_different_body_is_422(client):
    headers = {"Idempotency-Key": "key-2"}
    assert book(client, headers=headers).status_code == 201
    assert book(client, slot_id="s2", headers=headers).status_code == 422


def test_idempotent_replay_of_conflict(client):
    book(client)
    headers = {"Idempotency-Key": "key-3"}
    first = book(client, email="b@example.com", headers=headers)
    second = book(client, email="b@example.com", headers=headers)
    assert first.status_code == second.status_code == 409


def test_pagination(client):
    client.post("/reset", json={"slots": make_slots(5)})
    ids = []
    for i in range(1, 6):
        ids.append(book(client, slot_id=f"s{i}", email="Page@Example.com").json()["id"])
    book(client, slot_id="s1", email="x@example.com")  # 409, other person
    seen, cursor, pages = [], None, 0
    while True:
        params = {"email": "PAGE@example.com", "limit": 2}
        if cursor:
            params["cursor"] = cursor
        data = client.get("/bookings", params=params).json()
        seen += [b["id"] for b in data["bookings"]]
        pages += 1
        cursor = data["next_cursor"]
        if cursor is None:
            break
    assert seen == ids
    assert pages == 3


def test_pagination_exact_multiple_has_null_cursor(client):
    client.post("/reset", json={"slots": make_slots(2)})
    book(client, slot_id="s1")
    book(client, slot_id="s2")
    data = client.get(
        "/bookings", params={"email": "ada@example.com", "limit": 2}
    ).json()
    assert len(data["bookings"]) == 2
    assert data["next_cursor"] is None


def test_list_param_errors(client):
    for params in [
        {"email": "a@b.co", "limit": 0},
        {"email": "a@b.co", "limit": "abc"},
        {"email": "a@b.co", "limit": 1000},
        {"email": "a@b.co", "cursor": "!!!"},
        {},
        {"email": "  "},
    ]:
        response = client.get("/bookings", params=params)
        assert response.status_code == 400, params
        assert set(response.json()) == {"error"}


# level 5
def test_rate_limit(client):
    for _ in range(5):
        assert (
            book(client, slot_id="missing", email="spam@example.com").status_code == 404
        )
    sixth = book(client, slot_id="s1", email="SPAM@example.com")
    assert sixth.status_code == 429
    retry_after = sixth.headers["Retry-After"]
    assert retry_after.isdigit()
    assert 1 <= int(retry_after) <= 60
    assert book(client, slot_id="s1", email="fine@example.com").status_code == 201


def test_rate_limit_counts_invalid_attempts(client):
    for _ in range(5):
        assert book(client, name="").status_code == 400
    assert book(client, name="").status_code == 429


def test_idempotent_replays_do_not_burn_attempts(client):
    headers = {"Idempotency-Key": "replay"}
    for _ in range(8):
        assert book(client, headers=headers).status_code == 201


# persistence
def test_bookings_survive_a_new_app_instance(client):
    booking = book(client).json()
    with TestClient(app, headers={"X-API-Key": API_KEY}) as fresh:
        assert fresh.get(f"/bookings/{booking['id']}").json() == booking
