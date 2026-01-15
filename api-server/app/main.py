"""api-server FastAPI application.

Responsibilities:
- Serve a read endpoint: `GET /purchases?userId=<id>`
- Start a background Kafka consumer that writes into MongoDB

Why run the consumer inside this process?
- The project requirement is a single api-server that both consumes and serves HTTP.
- The consumer loop blocks, so we run it in a background thread.
"""

from __future__ import annotations

from threading import Event, Thread

from fastapi import FastAPI, HTTPException

from .kafka_consumer import run_consumer
from .mongo import get_collection, get_purchases_by_user

app = FastAPI(title="API Server")

# Used to signal the consumer thread to stop on shutdown.
stop_event = Event()

# Stored so we keep a reference; the thread is daemonized.
consumer_thread: Thread | None = None

# Mongo collection handle; set on startup.
collection = None


@app.on_event("startup")
def on_startup() -> None:
    """Startup hook.

    - Connect to MongoDB.
    - Start the Kafka consumer thread.
    """
    global consumer_thread, collection

    collection = get_collection()

    consumer_thread = Thread(
        target=run_consumer,
        args=(collection, stop_event),
        daemon=True,  # Daemon threads won't block process exit.
    )
    consumer_thread.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    """Shutdown hook.

    Signal the consumer loop to stop (it checks stop_event.is_set()).
    """
    stop_event.set()


@app.get("/health")
def health() -> dict[str, str]:
    """Basic liveness endpoint."""
    return {"status": "ok"}


@app.get("/purchases")
def get_purchases(userId: str):
    """Return all purchases for a user.

    Query params:
        userId: required

    Returns:
        {
          "userId": "...",
          "purchases": [ ...documents from Mongo... ]
        }
    """
    if not userId:
        raise HTTPException(status_code=400, detail="userId is required")

    docs = get_purchases_by_user(collection, userId)
    return {"userId": userId, "purchases": docs}
