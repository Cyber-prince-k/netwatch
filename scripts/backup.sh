#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${1:-./backups}"
stamp=$(date +%Y%m%d-%H%M%S)
docker compose exec -T db pg_dump -U netwatch -d netwatch > "${1:-./backups}/netwatch-${stamp}.sql"
