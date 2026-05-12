#!/usr/bin/env bash
set -euo pipefail

TARGET_MOUNT="${TARGET_MOUNT:-/}"
DISK_THRESHOLD_PERCENT="${DISK_THRESHOLD_PERCENT:-85}"
CONTAINER_PRUNE_UNTIL="${CONTAINER_PRUNE_UNTIL:-168h}"
IMAGE_PRUNE_UNTIL="${IMAGE_PRUNE_UNTIL:-240h}"
BUILDER_PRUNE_UNTIL="${BUILDER_PRUNE_UNTIL:-240h}"
JOURNAL_RETENTION="${JOURNAL_RETENTION:-7d}"
ENABLE_VOLUME_PRUNE="${ENABLE_VOLUME_PRUNE:-false}"

current_usage() {
  df -P "${TARGET_MOUNT}" | awk 'NR==2 {gsub("%","",$5); print $5}'
}

print_status() {
  echo "[storage-guard] Disk usage for ${TARGET_MOUNT}:"
  df -h "${TARGET_MOUNT}"
}

print_status
usage="$(current_usage)"

if (( usage < DISK_THRESHOLD_PERCENT )); then
  echo "[storage-guard] Usage ${usage}% is below threshold ${DISK_THRESHOLD_PERCENT}%. No cleanup needed."
  exit 0
fi

echo "[storage-guard] Usage ${usage}% is above threshold ${DISK_THRESHOLD_PERCENT}%. Starting safe cleanup..."

docker container prune -f --filter "until=${CONTAINER_PRUNE_UNTIL}"
docker image prune -a -f --filter "until=${IMAGE_PRUNE_UNTIL}"
docker builder prune -a -f --filter "until=${BUILDER_PRUNE_UNTIL}"

if [[ "${ENABLE_VOLUME_PRUNE}" == "true" ]]; then
  echo "[storage-guard] ENABLE_VOLUME_PRUNE=true -> pruning dangling volumes."
  docker volume prune -f
fi

if command -v journalctl >/dev/null 2>&1; then
  journalctl --vacuum-time="${JOURNAL_RETENTION}" >/dev/null || true
fi

echo "[storage-guard] Cleanup finished."
print_status
