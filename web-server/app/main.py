"""web-server FastAPI application.

Responsibilities:
- Accept buy requests and publish Kafka events.
- Provide a read endpoint that proxies to api-server.

Important note:
This service does NOT write to MongoDB directly.
Writes happen asynchronously by api-server's Kafka consumer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from .api_client import get_all_bought_items
from .config import KAFKA_TOPIC
from .kafka_producer import create_producer, send_purchase_created
from .models import BuyRequest, PurchaseCreatedEvent

from pathlib import Path
from fastapi.staticfiles import StaticFiles
# serve ./web-ui as static site
UI_DIR = Path("/app/web-ui")
app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="web-ui")

app = FastAPI(title="Client Web Server")

# Global producer instance created at startup.
producer = None


@app.on_event("startup")
def on_startup() -> None:
    """Create the Kafka producer once when the app starts."""
    global producer
    producer = create_producer()


@app.get("/health")
def health() -> dict[str, str]:
    """Basic liveness endpoint."""
    return {"status": "ok"}


@app.post("/buy")
def buy(req: BuyRequest):
    """Create a PurchaseCreated event and publish it to Kafka.

    This endpoint returns immediately after the message is confirmed delivered to Kafka
    (because we flush after produce).
    The actual MongoDB write is asynchronous and done by api-server.
    """
    event = PurchaseCreatedEvent(
        eventId=str(uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        userId=req.userId,
        itemId=req.itemId,
        quantity=req.quantity,
    ).model_dump()

    try:
        send_purchase_created(producer, KAFKA_TOPIC, event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to produce event: {e}")

    # "accepted" here means: the event was accepted into Kafka,
    # not that it has already been written to Mongo.
    return {"status": "accepted", "eventId": event["eventId"]}


@app.get("/getAllBoughtItems")
def get_all(userId: str):
    """Return all purchases for a user (proxied through api-server)."""
    if not userId:
        raise HTTPException(status_code=400, detail="userId is required")

    try:
        return get_all_bought_items(userId)
    except Exception as e:
        # 502 means our upstream dependency (api-server) failed.
        raise HTTPException(status_code=502, detail=f"API server error: {e}")
