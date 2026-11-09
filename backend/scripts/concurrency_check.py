"""
Fire many simultaneous bookings at a running server.

Usage: python scripts/concurrency_check.py http://localhost:8000 <api-key>
"""

import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
KEY = sys.argv[2] if len(sys.argv) > 2 else "change-me"
HEADERS = {"X-API-Key": KEY}
SLOT = {
    "id": "race",
    "provider": "Dr Chioma Okafor",
    "start": "2099-12-10T09:00:00Z",
    "end": "2099-12-10T09:30:00Z",
}
CLIENTS = 40


def attempt(i: int) -> int:
    response = httpx.post(
        f"{BASE}/bookings",
        headers=HEADERS,
        json={"slot_id": "race", "name": f"Person {i}", "email": f"p{i}@example.com"},
        timeout=30,
    )
    return response.status_code


def main() -> None:
    httpx.post(
        f"{BASE}/reset", headers=HEADERS, json={"slots": [SLOT]}
    ).raise_for_status()
    with ThreadPoolExecutor(max_workers=CLIENTS) as pool:
        codes = Counter(pool.map(attempt, range(CLIENTS)))
    print("status codes:", dict(codes))
    assert codes[201] == 1, "exactly one booking must succeed"
    assert codes[409] == CLIENTS - 1, "everyone else must get 409"

    # Same idempotency key sent concurrently -> one booking, identical responses.
    httpx.post(
        f"{BASE}/reset", headers=HEADERS, json={"slots": [SLOT]}
    ).raise_for_status()

    def same_key(_: int) -> tuple[int, str]:
        response = httpx.post(
            f"{BASE}/bookings",
            headers={**HEADERS, "Idempotency-Key": "k1"},
            json={"slot_id": "race", "name": "Ada", "email": "ada@example.com"},
            timeout=30,
        )
        return response.status_code, response.json().get("id", "")

    with ThreadPoolExecutor(max_workers=CLIENTS) as pool:
        results = set(pool.map(same_key, range(CLIENTS)))
    print("idempotent results:", results)
    assert len(results) == 1
    listing = httpx.get(
        f"{BASE}/bookings",
        headers=HEADERS,
        params={"email": "ada@example.com"},
    ).json()
    assert len(listing["bookings"]) == 1
    print("OK")


if __name__ == "__main__":
    main()
