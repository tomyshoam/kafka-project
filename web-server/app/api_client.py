"""HTTP client for calling api-server.

Why is this its own module?
- Keeps the FastAPI route handlers small and readable.
- Makes it easy to add retries/backoff later in one place.
"""

from __future__ import annotations

import httpx

from .config import API_SERVER_URL


def get_all_bought_items(user_id: str) -> dict:
    """Call api-server and return its JSON response.

    Raises:
        httpx.HTTPError on connection failures, timeouts, or non-2xx status (after raise_for_status).
    """
    url = f"{API_SERVER_URL}/purchases"

    # httpx.Client is a "real" HTTP client (connection pooling, keep-alive).
    # We keep it simple by creating it per call; for high load you'd create one
    # at startup and reuse it.
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, params={"userId": user_id})
        resp.raise_for_status()
        return resp.json()
