"""Kafka consumer loop for api-server.

High-level flow:
    poll -> decode JSON -> validate schema -> write to Mongo -> commit offset

Important Kafka concepts used here:

1) Consumer groups and offsets
- Kafka tracks the "current position" (offset) per partition per consumer group.
- Offsets are stored in Kafka itself (in an internal topic).
- Multiple consumers with the same group.id will share work (partition assignment).

2) Manual offset commit
- We set `enable.auto.commit=False`.
- We commit offsets only after successful processing.
- This gives "at-least-once" delivery: duplicates are possible, so we use
  idempotent writes in Mongo (`_id = eventId`).

3) poll(timeout)
- `consumer.poll(1.0)` means: wait up to 1 second for a message.
- In a `while True` loop, this effectively means: check for messages continuously,
  but don't block forever so we can react to shutdown signals.
"""

from __future__ import annotations

import json
from typing import Any

from confluent_kafka import Consumer
from pydantic import ValidationError

from .config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_GROUP_ID, KAFKA_TOPIC
from .models import PurchaseCreatedEvent
from .mongo import insert_purchase


def create_consumer() -> Consumer:
    """Create and configure a Confluent Kafka Consumer.

    Non-obvious settings explained:

    - auto.offset.reset:
        If this consumer group has NO committed offsets yet, where should we start?
        `earliest` means start at the beginning of the topic.
        Alternative: `latest` means only consume new events going forward.

    - enable.auto.commit:
        If True, the client commits offsets automatically in the background.
        We turn it off so we can commit only after Mongo write succeeds.
    """
    conf: dict[str, Any] = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": KAFKA_GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }
    return Consumer(conf)


def run_consumer(collection, stop_event) -> None:
    """Run the consumer loop until `stop_event.is_set()` becomes True.

    Args:
        collection: MongoDB collection handle.
        stop_event: A threading.Event (or compatible object) used to stop the loop.

    Poison-pill handling (very important):
        If a message is malformed (bad JSON / wrong schema), we COMMIT its offset
        after logging it. Otherwise we'd be stuck re-reading the same bad message
        forever.
    """
    print("[Consumer] Starting Kafka consumer")

    consumer = create_consumer()

    # Subscribe to our topic. Kafka will assign partitions to this consumer.
    consumer.subscribe([KAFKA_TOPIC])

    try:
        while not stop_event.is_set():
            # Wait up to 1 second for a message. Returns None if no message arrives.
            msg = consumer.poll(1.0)

            if msg is None:
                continue

            # `msg.error()` indicates a Kafka-level error (not an application payload error).
            if msg.error():
                print(f"[Consumer] Kafka error: {msg.error()}")
                continue

            # --- Decode JSON payload ---------------------------------------------------
            try:
                raw = msg.value().decode("utf-8")
                data = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                print(
                    f"[Consumer] Bad payload (decode/json): {e}. "
                    f"Skipping. partition={msg.partition()} offset={msg.offset()}"
                )
                # Commit to skip this poison message so the consumer can keep running.
                consumer.commit(msg)
                continue

            # --- Validate event schema ------------------------------------------------
            try:
                event = PurchaseCreatedEvent.model_validate(data)
            except ValidationError as e:
                print(f"[Consumer] Bad event schema: {e}. data={data}")
                # Same poison-pill strategy: log and commit so we move forward.
                consumer.commit(msg)
                continue

            print(
                f"[Consumer] Received event: {event.model_dump()} "
                f"(p={msg.partition()} o={msg.offset()})"
            )

            # --- Transform to Mongo document -----------------------------------------
            # Store `eventId` as `_id` for idempotency.
            purchase_doc = {
                "_id": event.eventId,
                "eventVersion": event.eventVersion,
                "eventType": event.eventType,
                "timestamp": event.timestamp,
                "userId": event.userId,
                "itemId": event.itemId,
                "quantity": event.quantity,
            }

            # --- Write to Mongo --------------------------------------------------------
            ok = insert_purchase(collection, purchase_doc)

            # --- Commit offset after successful processing -----------------------------
            if ok:
                # Committing the message tells Kafka: "this group processed this offset".
                # On restart, consumption resumes from the next offset.
                consumer.commit(msg)

    finally:
        consumer.close()
        print("[Consumer] Closed")
