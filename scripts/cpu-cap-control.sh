#!/usr/bin/env bash
# macbook81-cpu-cap runtime helper.
# A conservative cpufreq policy maximum, not a thermal fail-safe.
set -euo pipefail

SYSFS_ROOT="${MACBOOK81_CPU_SYSFS:-/sys/devices/system/cpu/cpufreq}"
RUN_ROOT="${MACBOOK81_CPU_RUN:-/run/macbook81-cpu-cap}"
CONFIG_FILE="${MACBOOK81_CPU_CONFIG:-/etc/macbook81-cpu-cap.max-khz}"

fail() { printf 'macbook81-cpu-cap: %s\n' "$*" >&2; exit 1; }
read_number() {
  local value
  [[ -r "$1" ]] || fail "Cannot read $1"
  IFS= read -r value < "$1" || [[ -n "$value" ]] || fail "Empty $1"
  [[ "$value" =~ ^[0-9]+$ ]] || fail "Non-numeric value in $1"
  printf '%s' "$value"
}
get_policies() {
  local -n policies_out="$1"
  shopt -s nullglob
  policies_out=("$SYSFS_ROOT"/policy[0-9]*)
  shopt -u nullglob
  (( ${#policies_out[@]} > 0 )) || fail "No CPU frequency policy in $SYSFS_ROOT"
}

apply() {
  local max_khz original new policy name min_limit hw_max
  max_khz="$(read_number "$CONFIG_FILE")"
  local -a policies=()
  get_policies policies
  # Validate ALL policies before changing ANY.
  for policy in "${policies[@]}"; do
    min_limit="$(read_number "$policy/scaling_min_freq")"
    hw_max="$(read_number "$policy/cpuinfo_max_freq")"
    (( max_khz >= min_limit && max_khz <= hw_max )) || fail "Configured ${max_khz} kHz not within $policy bounds (${min_limit}-${hw_max})"
    [[ -w "$policy/scaling_max_freq" ]] || fail "Not writable: $policy/scaling_max_freq (need root?)"
  done
  mkdir -p "$RUN_ROOT"
  chmod 0700 "$RUN_ROOT"
  for policy in "${policies[@]}"; do
    name="${policy##*/}"
    original="$(read_number "$policy/scaling_max_freq")"
    if (( original > max_khz )); then
      # One state file per policy, recording previous value and applied limit.
      # Preserve the ORIGINAL until a matching restore, even on repeated apply.
      if [[ ! -e "$RUN_ROOT/$name" ]]; then
        printf '%s %s\n' "$original" "$max_khz" > "$RUN_ROOT/$name"
      fi
      printf '%s\n' "$max_khz" > "$policy/scaling_max_freq"
    fi
    new="$(read_number "$policy/scaling_max_freq")"
    printf '%s: max %s MHz (requested %s MHz)\n' "$name" "$((new/1000))" "$((max_khz/1000))"
  done
}

restore() {
  local state name policy previous applied actual minimum hardware
  shopt -s nullglob
  local -a states=("$RUN_ROOT"/policy[0-9]*)
  shopt -u nullglob
  for state in "${states[@]}"; do
    name="${state##*/}"
    [[ "$name" =~ ^policy[0-9]+$ ]] || continue
    read -r previous applied < "$state" || true
    if [[ ! "${previous:-}" =~ ^[0-9]+$ || ! "${applied:-}" =~ ^[0-9]+$ ]]; then
      printf '%s: invalid saved state; leaving CPU setting unchanged\n' "$name" >&2
      continue
    fi
    policy="$SYSFS_ROOT/$name"
    if [[ -w "$policy/scaling_max_freq" ]]; then
      actual="$(read_number "$policy/scaling_max_freq")"
      minimum="$(read_number "$policy/scaling_min_freq")"
      hardware="$(read_number "$policy/cpuinfo_max_freq")"
      if (( actual == applied && previous >= minimum && previous <= hardware )); then
        printf '%s\n' "$previous" > "$policy/scaling_max_freq"
        printf '%s: restored previous max %s MHz\n' "$name" "$((previous/1000))"
      else
        printf '%s: limit was changed by another program or hardware; not overwriting\n' "$name" >&2
      fi
    fi
    rm -f -- "$state"
  done
  [[ ! -d "$RUN_ROOT" ]] || rmdir "$RUN_ROOT" 2>/dev/null || true
}

status() {
  local -a policies=()
  local policy name current min_limit hardware
  get_policies policies
  for policy in "${policies[@]}"; do
    name="${policy##*/}"
    current="$(read_number "$policy/scaling_max_freq")"
    min_limit="$(read_number "$policy/scaling_min_freq")"
    hardware="$(read_number "$policy/cpuinfo_max_freq")"
    printf '%s: min=%s MHz, configured-max=%s MHz, hardware-max=%s MHz\n' "$name" "$((min_limit/1000))" "$((current/1000))" "$((hardware/1000))"
  done
}

case "${1:-}" in
  apply) apply ;;
  restore) restore ;;
  status) status ;;
  *) printf 'Usage: %s {apply|restore|status}\n' "$0" >&2; exit 2 ;;
esac