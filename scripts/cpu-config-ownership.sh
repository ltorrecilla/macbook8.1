#!/usr/bin/env bash
# Ownership checks for the optional CPU cap configuration.
# Source this file. No system paths are changed merely by sourcing it.
CPU_CAP_OWNER_TAG=macbook81-cpu-cap-v1

cpu_cap_config_error() {
  printf 'CPU cap config: %s\n' "$*" >&2
  return 1
}

cpu_cap_config_preflight() {
  local config=$1 marker=$2 requested=$3 legacy_owned=$4
  local tag digest actual current
  [[ ! -L "$config" && ! -L "$marker" ]] ||
    { cpu_cap_config_error 'Refusing symbolic-link config or ownership marker'; return 1; }
  if [[ -e "$marker" ]]; then
    [[ -f "$marker" && -f "$config" ]] ||
      { cpu_cap_config_error 'Incomplete managed config/marker pair'; return 1; }
    read -r tag digest < "$marker" || true
    [[ "$tag" == "$CPU_CAP_OWNER_TAG" && "$digest" =~ ^[a-f0-9]{64}$ ]] ||
      { cpu_cap_config_error 'Unrecognized ownership marker'; return 1; }
    actual=$(sha256sum -- "$config") || return 1
    [[ "${actual%% *}" == "$digest" ]] ||
      { cpu_cap_config_error 'Config has been modified externally; preserving it'; return 1; }
    return 0
  fi
  if [[ -e "$config" ]]; then
    [[ -f "$config" && "$legacy_owned" == yes ]] ||
      { cpu_cap_config_error 'Unmanaged config exists; refusing to overwrite'; return 1; }
    current=$(cat -- "$config") || return 1
    [[ "$current" == "$requested" ]] ||
      { cpu_cap_config_error 'Legacy config differs from requested cap; preserving it'; return 1; }
  fi
}

cpu_cap_config_mark() {
  local config=$1 marker=$2 digest
  digest=$(sha256sum -- "$config") || return 1
  [[ ! -L "$marker" ]] || return 1
  printf '%s %s\n' "$CPU_CAP_OWNER_TAG" "${digest%% *}" > "$marker"
  chmod 0644 "$marker"
}

cpu_cap_config_removal_policy() {
  local config=$1 marker=$2
  if [[ -e "$marker" || -L "$marker" ]]; then
    cpu_cap_config_preflight "$config" "$marker" "" no || return 1
    printf 'managed\n'
  else
    [[ ! -L "$config" ]] || { cpu_cap_config_error 'Unmanaged symlink config'; return 1; }
    printf 'preserve\n'
  fi
}
