"""api-server configuration.

This module is intentionally "boring": it only reads environment variables.

Keeping configuration in one place makes it easier to:
- run locally, on EC2, or later inside Docker
- change IPs/ports without touching application logic
- see, at a glance, what the service depends on

All defaults are reasonable for development. In EC2 you should override them with
environment variables.
"""

from __future__ import annotations

import os

# --- Kafka -------------------------------------------------------------------
# Kafka bootstrap servers (broker addresses). Example: "172.31.0.202:9092"
KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "172.31.0.202:9092")

# Kafka topic for purchase events
KAFKA_TOPIC: str = os.getenv("KAFKA_TOPIC", "purchases.v1")

# Consumer group id:
# - Offsets in Kafka are tracked per consumer group.
# - If you change this value to something new, the consumer will behave like
#   "a brand new group" and (depending on auto.offset.reset) may re-read old events.
KAFKA_GROUP_ID: str = os.getenv("KAFKA_GROUP_ID", "purchase-consumer")

# --- MongoDB -----------------------------------------------------------------
# Mongo connection string. Example: "mongodb://172.31.2.197:27017"
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://172.31.2.197:27017")

# Database name
MONGO_DB: str = os.getenv("MONGO_DB", "purchases_db")

# Collection name
MONGO_COLLECTION: str = os.getenv("MONGO_COLLECTION", "purchases")
