"""MongoDB helper functions for api-server.

This module has one job: handle MongoDB interactions.

Key design choice (important):
- We store Kafka eventId as MongoDB `_id` (primary key).
- That makes writes idempotent:
    If the same Kafka message is processed twice, Mongo rejects the duplicate,
    and we treat it as "already processed".

This is the common approach when doing at-least-once Kafka processing.
"""

from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient, errors

from .config import MONGO_COLLECTION, MONGO_DB, MONGO_URI


def get_collection():
    """Connect to MongoDB and return the configured collection.

    We also create an index used by the read API:
    - query by userId
    - sort by timestamp (newest first)

    Creating the index here is convenient for a learning project.
    In larger systems you'd manage indexes via migrations or deployment scripts.
    """
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db[MONGO_COLLECTION]

    # This index supports queries like:
    #   find({userId}).sort(timestamp desc)
    collection.create_index([("userId", ASCENDING), ("timestamp", DESCENDING)])
    return collection


def insert_purchase(collection, purchase: dict[str, Any]) -> bool:
    """Insert a purchase document into MongoDB.

    Returns:
        True  -> insert succeeded OR duplicate was ignored
        False -> unexpected failure (caller may choose to not commit offset)

    Why return a boolean?
        The consumer decides whether to commit the Kafka offset. If Mongo insert
        failed for some transient reason, we can skip committing to retry later.

    DuplicateKeyError:
        This happens when `_id` already exists, meaning we already processed the
        event. That's fine; we treat it as success (idempotency).
    """
    try:
        collection.insert_one(purchase)
        print(f"[Mongo] Inserted purchase {purchase['_id']}")
        return True
    except errors.DuplicateKeyError:
        print(f"[Mongo] Duplicate event ignored: {purchase['_id']}")
        return True
    except Exception as e:
        print(f"[Mongo] Insert failed: {e} purchase_id={purchase.get('_id')}")
        return False


def get_purchases_by_user(collection, user_id: str) -> list[dict[str, Any]]:
    """Return purchases for a user, newest first."""
    return list(collection.find({"userId": user_id}).sort("timestamp", -1))
