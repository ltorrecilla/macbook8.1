#!/usr/bin/env bash
# Prototype fresh-install rollback helper. NOT wired into production installer.
# Only deletes paths with exact expected checksums; refuses changed files.
cpu_fresh_rollback() {
  local manifest=$1 path expected actual
  [[ -f "$manifest" && ! -L "$manifest" ]] || return 2
  local errors=0
  while IFS=$'\t' read -r expected path; do
    [[ "$expected" =~ ^[a-f0-9]{64}$ && -n "$path" ]] || { errors=1; continue; }
    # Caller supplies explicit allowlist root (fixture in tests).
    [[ -n "${CPU_ROLLBACK_ROOT:-}" && "$path" == "$CPU_ROLLBACK_ROOT/"* ]] ||
      { errors=1; continue; }
    [[ -e "$path" && -f "$path" && ! -L "$path" ]] || { errors=1; continue; }
    actual=$(sha256sum -- "$path") || { errors=1; continue; }
    if [[ "${actual%% *}" == "$expected" ]]; then
      rm -- "$path" || errors=1
    else
      printf 'Preserving changed file: %s\n' "$path" >&2
      errors=1
    fi
  done < "$manifest"
  return "$errors"
}
