#!/usr/bin/env bash
# Restore the per-boot CPU frequency ceilings and remove our service/config.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo' >&2; exit 1; }
unit=/etc/systemd/system/macbook81-cpu-cap.service
helper=/usr/local/libexec/macbook81-cpu-cap
config=/etc/macbook81-cpu-cap.max-khz
if [[ ! -f "$unit" ]]; then
  echo 'Our CPU cap service is not installed.'
  exit 0
fi
if ! grep -q '^# Managed by macbook81-starter' "$unit"; then
  echo 'Refusing to remove an unrecognized service file' >&2
  exit 1
fi
systemctl disable --now macbook81-cpu-cap.service
rm -f -- "$unit" "$config"
if [[ -f "$helper" ]] && grep -q '^# macbook81-cpu-cap runtime helper\.' "$helper"; then
  rm -f -- "$helper"
fi
systemctl daemon-reload
printf 'CPU cap service removed; previous per-boot limits restored where possible.\n'
printf 'If another tool controls CPU frequency, check its own settings.\n'