#!/bin/bash
# Auto-deploy VerbPractice on the mini PC (runs via verbpractice-deploy.timer).
#
# Phase 1 (no args): fetch origin/main and exit quietly when the last
# *successful* deploy (.deployed-rev marker) already matches it; otherwise
# hard-reset to it and re-exec the *updated* copy of this script so phase 2
# always runs the code that came with the new commit.
# Phase 2 (--post-pull <prev-rev>): rebuild what changed since the last
# successful deploy, migrate, restart the service, and record the marker only
# after the health check passes — so a failed deploy retries on the next tick
# instead of silently sticking.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/VerbPractice}"
LOCK_FILE="/tmp/verbpractice-deploy.lock"
MARKER_FILE="$REPO_DIR/.deployed-rev"

cd "$REPO_DIR"

if [ "${1:-}" != "--post-pull" ]; then
    exec 9>"$LOCK_FILE"
    flock -n 9 || exit 0
    git fetch --quiet origin main
    REMOTE=$(git rev-parse origin/main)
    DEPLOYED=$(cat "$MARKER_FILE" 2>/dev/null || echo "")
    [ "$REMOTE" = "$DEPLOYED" ] && exit 0
    echo "Deploying ${DEPLOYED:0:7} -> ${REMOTE:0:7}"
    git reset --hard origin/main
    exec /bin/bash "$REPO_DIR/deploy/autodeploy.sh" --post-pull "$DEPLOYED"
fi

# --- phase 2: $2 is the last successfully deployed rev (may be empty) ---
PREV="${2:-}"

changed() {
    # Unknown previous rev (first run / marker lost): rebuild everything.
    [ -z "$PREV" ] && return 0
    git rev-parse --verify --quiet "$PREV^{commit}" >/dev/null || return 0
    git diff --name-only "$PREV" HEAD | grep -qE "$1"
}

if changed '^pyproject\.toml'; then
    echo "Python deps changed — reinstalling..."
    make install
    make ocr-models
fi

if changed '^frontend/(src|package|index\.html|vite)'; then
    echo "Frontend changed — rebuilding SPA..."
    make spa-build
fi

make migrate

systemctl --user restart verbpractice

echo "Waiting for health..."
for _ in $(seq 1 20); do
    if curl -fsS --max-time 3 http://127.0.0.1:8000/healthz > /dev/null 2>&1; then
        git rev-parse HEAD > "$MARKER_FILE"
        echo "Deploy complete at $(date): $(git rev-parse --short HEAD)"
        exit 0
    fi
    sleep 2
done

echo "WARNING: service did not become healthy after deploy — will retry on the next timer tick" >&2
exit 1
