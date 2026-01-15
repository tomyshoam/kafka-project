#!/bin/bash
set -euxo pipefail

REPO_URL="${repo_url}"
KAFKA_IP="${kafka_private_ip}"
MONGO_IP="${mongo_private_ip}"

# Basic packages
apt-get update -y
apt-get install -y ca-certificates curl git

# Docker (official convenience script is fine for demos)
curl -fsSL https://get.docker.com | sh

# docker compose plugin usually comes with docker, but ensure it's available
docker --version
docker compose version || true

# Clone repo
mkdir -p /opt/kafka-project
cd /opt/kafka-project
if [ ! -d repo ]; then
  git clone "${REPO_URL}" repo
fi
cd repo

# Create env file for the app compose
mkdir -p deploy/app
cat > deploy/app/.env <<EOF
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_IP}:9092
KAFKA_TOPIC=purchases.v1
KAFKA_GROUP_ID=purchase-consumer

MONGO_URI=mongodb://${MONGO_IP}:27017
MONGO_DB=purchases_db
MONGO_COLLECTION=purchases

API_SERVER_URL=http://api-server:8000
EOF

# Start app compose (api-server + web-server)
docker compose -f deploy/app/docker-compose.yml --env-file deploy/app/.env up -d
docker ps
