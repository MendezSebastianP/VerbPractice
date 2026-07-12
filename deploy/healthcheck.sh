#!/bin/bash
# Watchdog for the running app (verbpractice-health.timer, every 2 minutes).
# Restart=always already revives a dead process; this catches the other
# failure mode — a process that is alive but no longer answering.
set -u

LOCK_FILE="/tmp/verbpractice-deploy.lock"

# A deploy is restarting the service right now — don't fight it.
exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

for _ in 1 2 3; do
    if curl -fsS --max-time 5 http://127.0.0.1:8000/healthz > /dev/null 2>&1; then
        exit 0
    fi
    sleep 5
done

echo "healthcheck: /healthz failed 3 times — restarting verbpractice" >&2
systemctl --user restart verbpractice
