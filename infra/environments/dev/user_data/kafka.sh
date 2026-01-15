#!/bin/bash
set -euxo pipefail

REPO_URL="${repo_url}"

apt-get update -y
apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh

mkdir -p /opt/kafka-project
cd /opt/kafka-project

if [ ! -d repo ]; then
  git clone "${REPO_URL}" repo
fi

cd /opt/kafka-project/repo/deploy/kafka

# Start only the Kafka compose for this machine.
docker compose up -d

docker ps
