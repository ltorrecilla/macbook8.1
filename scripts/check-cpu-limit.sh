#!/usr/bin/env bash
set -euo pipefail
printf 'Model: '; cat /sys/class/dmi/id/product_name 2>/dev/null || echo unknown
printf 'Kernel: '; uname -r
printf 'CPU cap service: '
if command -v systemctl >/dev/null 2>&1; then
  systemctl is-enabled macbook81-cpu-cap.service 2>/dev/null || true
  printf 'Service state: '; systemctl is-active macbook81-cpu-cap.service 2>/dev/null || true
else
  echo 'systemd unavailable'
fi
if [[ -r /etc/macbook81-cpu-cap.max-khz ]]; then
  printf 'Requested cap: %s MHz\n' "$(($(cat /etc/macbook81-cpu-cap.max-khz)/1000))"
fi
shopt -s nullglob
policies=(/sys/devices/system/cpu/cpufreq/policy[0-9]*)
shopt -u nullglob
if (( ${#policies[@]} == 0 )); then echo 'No cpufreq policies found'; exit 1; fi
for p in "${policies[@]}"; do
  name=${p##*/}
  printf '%s governor=%s min=%s MHz max=%s MHz hardware_max=%s MHz\n' \
    "$name" "$(cat "$p/scaling_governor")" \
    "$(($(cat "$p/scaling_min_freq")/1000))" \
    "$(($(cat "$p/scaling_max_freq")/1000))" \
    "$(($(cat "$p/cpuinfo_max_freq")/1000))"
done