"""Pydantic models for api-server.

Why do we validate Kafka events?
- Kafka is a log: it can contain old messages produced with an older schema.
- Validation prevents KeyError-style crashes on unexpected payloads.
- When a message is invalid, we can log it and decide how to handle it.

We validate with Pydantic to make the event contract explicit and self-documenting.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PurchaseCreatedEvent(BaseModel):
    """Kafka event schema for a new purchase.

    Fields:
        eventId: Globally unique identifier for this event (UUID string).
        eventType: Constant discriminator for the event kind.
        eventVersion: Schema version. Useful for future evolution.
        timestamp: ISO8601 timestamp string (UTC recommended).

        userId: Who made the purchase.
        itemId: What they purchased.
        quantity: How many items were purchased.

    Notes:
        - `quantity` is required and must be >= 1.
        - Using an explicit event schema is the easiest way to avoid "schema drift"
          (producer sending something different than the consumer expects).
    """

    eventId: str
    eventType: Literal["PurchaseCreated"] = "PurchaseCreated"
    eventVersion: int = 1
    timestamp: str

    userId: str
    itemId: str
    quantity: int = Field(ge=1)
