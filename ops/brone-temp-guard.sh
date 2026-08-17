#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-notifier_brone_auth}"
PROFILE_ROOT="${PROFILE_ROOT:-/tmp/brone-puppeteer}"
RUNTIME_ROOT="${RUNTIME_ROOT:-/tmp/brone-runtime}"
STALE_MINUTES="${STALE_MINUTES:-30}"
WARN_DISK_PERCENT="${WARN_DISK_PERCENT:-75}"
CRITICAL_DISK_PERCENT="${CRITICAL_DISK_PERCENT:-85}"

exec 9>/run/lock/brone-temp-guard.lock
flock -n 9 || exit 0

usage_percent() {
  df -P / | awk 'NR == 2 { gsub("%", "", $5); print $5 }'
}

log() {
  echo "[brone-temp-guard] $*"
}

if ! docker inspect --type container "${CONTAINER_NAME}" >/dev/null 2>&1; then
  log "container=${CONTAINER_NAME} is absent; nothing to clean."
  exit 0
fi

if [[ "$(docker inspect --format '{{.State.Running}}' "${CONTAINER_NAME}")" != "true" ]]; then
  log "container=${CONTAINER_NAME} is not running; skipping cleanup."
  exit 0
fi

usage="$(usage_percent)"
if (( usage >= CRITICAL_DISK_PERCENT )); then
  log "severity=critical disk_usage=${usage}% threshold=${CRITICAL_DISK_PERCENT}%"
elif (( usage >= WARN_DISK_PERCENT )); then
  log "severity=warning disk_usage=${usage}% threshold=${WARN_DISK_PERCENT}%"
else
  log "severity=ok disk_usage=${usage}%"
fi

# Only profiles created by browser-session.js are eligible. Generic Puppeteer
# directories are intentionally excluded because they can belong to an active job.
mapfile -t stale_profiles < <(
  docker exec "${CONTAINER_NAME}" sh -c '
    root="$1"
    stale_minutes="$2"
    [ -d "$root" ] || exit 0
    find "$root" -mindepth 1 -maxdepth 1 -type d -name "profile-*" -mmin "+$stale_minutes" -print
  ' sh "${PROFILE_ROOT}" "${STALE_MINUTES}"
)

processes="$(docker top "${CONTAINER_NAME}" -eo args 2>/dev/null || true)"
cleaned=0
skipped=0
for profile in "${stale_profiles[@]}"; do
  case "${profile}" in
    "${PROFILE_ROOT}"/profile-*) ;;
    *)
      log "refusing unexpected path=${profile}"
      skipped=$((skipped + 1))
      continue
      ;;
  esac

  if grep -Fq -- "--user-data-dir=${profile}" <<<"${processes}"; then
    log "skipping active profile=${profile}"
    skipped=$((skipped + 1))
    continue
  fi

  size="$(docker exec "${CONTAINER_NAME}" du -sh "${profile}" 2>/dev/null | awk '{print $1}' || true)"
  docker exec "${CONTAINER_NAME}" rm -rf -- "${profile}"
  log "removed stale profile=${profile} size=${size:-unknown}"
  cleaned=$((cleaned + 1))
done

# Chrome creates ProcessSingleton sockets under TMPDIR. This directory is owned
# by brone-auth, and is cleaned only when no Chrome process is active.
if ! grep -Eq '(^|[[:space:]])[^[:space:]]*chrome([^[:space:]]*)?([[:space:]]|$)' <<<"${processes}"; then
  mapfile -t stale_runtime_artifacts < <(
    docker exec "${CONTAINER_NAME}" sh -c '
      root="$1"
      stale_minutes="$2"
      [ -d "$root" ] || exit 0
      find "$root" -mindepth 1 -maxdepth 1 -name "com.google.Chrome.*" -mmin "+$stale_minutes" -print
    ' sh "${RUNTIME_ROOT}" "${STALE_MINUTES}"
  )
  for artifact in "${stale_runtime_artifacts[@]}"; do
    case "${artifact}" in
      "${RUNTIME_ROOT}"/com.google.Chrome.*) ;;
      *) continue ;;
    esac
    size="$(docker exec "${CONTAINER_NAME}" du -sh "${artifact}" 2>/dev/null | awk '{print $1}' || true)"
    docker exec "${CONTAINER_NAME}" rm -rf -- "${artifact}"
    log "removed stale runtime artifact=${artifact} size=${size:-unknown}"
    cleaned=$((cleaned + 1))
  done
else
  log "active Chrome detected; runtime artifacts are retained."
fi

log "completed cleaned=${cleaned} skipped=${skipped} stale_minutes=${STALE_MINUTES}"
