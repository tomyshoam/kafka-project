# pmk-project — Kafka + MongoDB + Python (FastAPI)

A small **event-driven** project that records purchases.

This repo is intentionally kept simple and readable:
- No vendored dependencies
- No virtual environments committed
- Lots of comments explaining the non-obvious parts (Kafka offsets, idempotency, producer delivery, and HTTP proxying)

## Services

### web-server (FastAPI, port 9000)
- `POST /buy` publishes a `PurchaseCreated` event into Kafka.
- `GET /getAllBoughtItems?userId=<id>` calls api-server and returns purchases.

### api-server (FastAPI, port 8000)
- Runs a Kafka consumer in a **background thread**.
- Validates events with **Pydantic** to avoid runtime crashes on bad payloads.
- Writes purchases into MongoDB.
- Exposes a read endpoint: `GET /purchases?userId=<id>`.

## Data flow

1. Client calls `POST /buy` on **web-server**
2. web-server produces a JSON message into Kafka topic `purchases.v1`
3. **api-server** consumes that message, validates it, and writes it to MongoDB
4. Client calls `GET /getAllBoughtItems` on web-server
5. web-server proxies the request to api-server `/purchases`
6. api-server reads from MongoDB and returns the stored purchases

## Event contract (important)

The `PurchaseCreated` event schema uses **quantity** (not `qty`):

```json
{
  "eventId": "uuid",
  "eventType": "PurchaseCreated",
  "eventVersion": 1,
  "timestamp": "2026-01-15T10:34:14.300477+00:00",
  "userId": "u1",
  "itemId": "i99",
  "quantity": 2
}
```

## Configuration

Both services use environment variables (no hardcoded IPs required in code).

Create `.env` files from the included examples:
- `api-server/.env.example`
- `web-server/.env.example`

## Running (virtualenv)

Run both services on the same machine (as you did on your app EC2) or on separate machines as long as they can reach Kafka and Mongo.

### api-server

```bash
cd api-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# config
export KAFKA_BOOTSTRAP_SERVERS="172.31.0.202:9092"
export KAFKA_TOPIC="purchases.v1"
export KAFKA_GROUP_ID="purchase-consumer"

export MONGO_URI="mongodb://172.31.2.197:27017"
export MONGO_DB="purchases_db"
export MONGO_COLLECTION="purchases"

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### web-server

```bash
cd web-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# config
export KAFKA_BOOTSTRAP_SERVERS="172.31.0.202:9092"
export KAFKA_TOPIC="purchases.v1"
export API_SERVER_URL="http://172.31.2.3:8000"

python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
```

## Quick tests

Health:
```bash
curl http://<WEB_HOST>:9000/health
curl http://<API_HOST>:8000/health
```

Buy:
```bash
curl -X POST http://<WEB_HOST>:9000/buy \
  -H 'Content-Type: application/json' \
  -d '{"userId":"u1","itemId":"i99","quantity":2}'
```

Get all purchases (through web-server):
```bash
curl "http://<WEB_HOST>:9000/getAllBoughtItems?userId=u1"
```

Direct read (api-server):
```bash
curl "http://<API_HOST>:8000/purchases?userId=u1"
```

## Troubleshooting

### web-server returns 502 (connection refused)
The api-server is not running or not reachable from the web-server host.

Confirm from the web-server host:
```bash
curl http://172.31.2.3:8000/health
```

### Consumer logs “Bad event schema”
Kafka contains an old/bad message (for example it used `qty` instead of `quantity`).
We log it and commit its offset so it does not block the consumer forever.
