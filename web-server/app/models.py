"""Pydantic models for web-server.

We validate input at the HTTP boundary so that:
- bad requests fail fast with a clear error
- Kafka only receives valid events
- the event contract stays consistent across services
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BuyRequest(BaseModel):
    """Request body for `POST /buy`."""

    userId: str
    itemId: str
    quantity: int = Field(ge=1)


class PurchaseCreatedEvent(BaseModel):
    """Kafka event produced by web-server.

    This must match the schema expected by api-server.
    """

    eventId: str
    eventType: Literal["PurchaseCreated"] = "PurchaseCreated"
    eventVersion: int = 1
    timestamp: str

    userId: str
    itemId: str
    quantity: int = Field(ge=1)
