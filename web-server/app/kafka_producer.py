"""Kafka producer helper for web-server.

Key points to understand:

1) Producer is created once and reused
Creating a producer is relatively heavy; we do it once at app startup.

2) Delivery acknowledgement
Kafka producers are asynchronous: `produce()` queues the message locally.
Delivery to the broker is confirmed later via a callback.

3) Why do we call `flush()`?
For a learning project, calling `flush()` after each message makes the behavior
obvious: the HTTP request returns only after Kafka confirms delivery (or times out).

In higher-throughput systems, you'd avoid flushing per message and let the producer
batch automatically.

4) Why do we set a message key (userId)?
Kafka uses the key to decide which partition receives the message.
Same key => same partition => preserves ordering for that key.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from confluent_kafka import Producer

from .config import KAFKA_BOOTSTRAP_SERVERS


def create_producer() -> Producer:
    """Create and configure a Confluent Kafka Producer."""
    conf: dict[str, Any] = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,

        # This makes the producer more resilient and safer against duplicates
        # when retries happen. It's a good default for most real systems.
        "enable.idempotence": True,
    }
    return Producer(conf)


def _delivery_report(err, msg) -> None:
    """Delivery callback.

    Confluent Kafka calls this when the broker acknowledges the message
    or when delivery fails.
    """
    if err is not None:
        print(f"[Producer] Delivery failed: {err}")
    else:
        print(f"[Producer] Delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")


def send_purchase_created(producer: Producer, topic: str, event: dict[str, Any]) -> None:
    """Serialize and send the PurchaseCreated event to Kafka."""
    # Convert dict -> JSON bytes (Kafka message value is bytes).
    payload: bytes = json.dumps(event).encode("utf-8")

    # Message key is also bytes. We use userId to preserve ordering per user.
    key: bytes = event["userId"].encode("utf-8")

    # `produce()` is asynchronous: it queues the message locally.
    producer.produce(
        topic=topic,
        key=key,
        value=payload,
        callback=_delivery_report,
    )

    # `flush(timeout)` blocks until all queued messages are delivered or timeout happens.
    # This is simple and good for learning (one request -> one Kafka publish -> flush).
    producer.flush(5)
