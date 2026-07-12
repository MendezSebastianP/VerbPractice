#!/bin/bash
# Auto-deploy VerbPractice on the mini PC (runs via verbpractice-deploy.timer).
#
# Phase 1 (no args): fetch origin/main and exit quietly when already current;
# otherwise hard-reset to it and re-exec the *updated* copy of this script so
# phase 2 always runs the code that came with the new commit.
# Phase 2 (--post-pull): rebuild what changed, migrate, restart the service.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/VerbPractice}"
LOCK_FILE="/tmp/verbpractice-deploy.lock"

cd "$REPO_DIR"

if [ "${1:-}" != "--post-pull" ]; then
    exec 9>"$LOCK_FILE"
    flock -n 9 || exit 0
    git fetch --quiet origin main
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main)
    [ "$LOCAL" = "$REMOTE" ] && exit 0
    echo "Deploying ${LOCAL:0:7} -> ${REMOTE:0:7}"
    git reset --hard origin/main
    exec /bin/bash "$REPO_DIR/deploy/autodeploy.sh" --post-pull
fi

# --- phase 2: HEAD@{1} is the commit we were on before the reset above ---
PREV=$(git rev-parse 'HEAD@{1}' 2>/dev/null || echo "")

changed() {
    [ -z "$PREV" ] && return 0
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
        echo "Deploy complete at $(date): $(git rev-parse --short HEAD)"
        exit 0
    fi
    sleep 2
done

echo "WARNING: service did not become healthy after deploy" >&2
exit 1
