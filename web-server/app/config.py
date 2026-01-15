"""web-server configuration.

The web-server is the "client-facing" service:
- It accepts a buy request over HTTP.
- It publishes a Kafka event.
- It proxies read requests to api-server.

Everything is controlled by environment variables so this service can run
anywhere (local, EC2, Docker) without code changes.
"""

from __future__ import annotations

import os

# Kafka
KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "172.31.0.202:9092")
KAFKA_TOPIC: str = os.getenv("KAFKA_TOPIC", "purchases.v1")

# api-server base URL (internal VPC IP or DNS)
API_SERVER_URL: str = os.getenv("API_SERVER_URL", "http://172.31.2.3:8000")
