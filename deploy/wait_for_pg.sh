#!/bin/bash
# Start the postgres container and give it a moment to accept connections.
# Always exits 0: if postgres still isn't up, the app will fail to start and
# systemd (Restart=always) retries until it is — this wait just makes the
# common boot path clean instead of a crash-loop.
set -u

docker start verbpractice-pg >/dev/null 2>&1 || true

for _ in $(seq 1 30); do
    if docker exec verbpractice-pg pg_isready -U postgres >/dev/null 2>&1; then
        exit 0
    fi
    sleep 1
done

echo "wait_for_pg: postgres not ready after 30s — starting app anyway (systemd will retry)" >&2
exit 0
