#!/usr/bin/env bash
# Optional CPU cpufreq maximum for the early 2015 MacBook8,1.
set -euo pipefail

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'USAGE'
Usage: sudo bash scripts/install-cpu-limit.sh [MAX_MHZ]

Default MAX_MHZ is 1600. Suggested starting profiles:
  1300  Cool
  1600  Balanced (default)
  2000  Performance

This caps the requested cpufreq ceiling. It is NOT a temperature guarantee.
Use scripts/uninstall-cpu-limit.sh to roll back.
USAGE
}
[[ "${1:-}" != '-h' && "${1:-}" != '--help' ]] || { usage; exit 0; }
[[ $EUID -eq 0 ]] || fail 'Run with sudo (e.g. sudo bash scripts/install-cpu-limit.sh 1600)'
[[ "${1:-1600}" =~ ^[0-9]+$ ]] || fail 'MAX_MHZ must be an integer in MHz'
(( $# <= 1 )) || fail 'Supply at most one frequency argument'
max_mhz="${1:-1600}"
max_khz=$((10#$max_mhz * 1000))
[[ "$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)" == 'MacBook8,1' ]] || fail 'Only MacBook8,1 is supported'
[[ -d /run/systemd/system ]] || fail 'systemd must be running'
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
helper_src="$source_dir/scripts/cpu-cap-control.sh"
service_src="$source_dir/systemd/macbook81-cpu-cap.service"
# shellcheck source=cpu-config-ownership.sh
source "$source_dir/scripts/cpu-config-ownership.sh"
[[ -r "$helper_src" && -r "$service_src" ]] || fail 'Missing kit files'
shopt -s nullglob
policies=(/sys/devices/system/cpu/cpufreq/policy[0-9]*)
shopt -u nullglob
(( ${#policies[@]} )) || fail 'No CPU frequency scaling policies found'
for p in "${policies[@]}"; do
  min="$(cat "$p/scaling_min_freq")"
  max="$(cat "$p/cpuinfo_max_freq")"
  (( max_khz >= min && max_khz <= max )) || fail "${max_mhz} MHz outside available ${min}-${max} kHz for ${p##*/}"
done
unit=/etc/systemd/system/macbook81-cpu-cap.service
helper=/usr/local/libexec/macbook81-cpu-cap
config=/etc/macbook81-cpu-cap.max-khz
marker=/etc/macbook81-cpu-cap.max-khz.owner
if [[ -e "$unit" ]] && ! grep -q '^# Managed by macbook81-starter' "$unit"; then
  fail "A different $unit exists; refusing to overwrite it"
fi
if [[ -e "$helper" ]] && ! grep -q '^# macbook81-cpu-cap runtime helper\.' "$helper"; then
  fail "A different $helper exists; refusing to overwrite it"
fi
legacy_owned=no
if [[ -f "$unit" && -f "$helper" ]] &&
   grep -q '^# Managed by macbook81-starter' "$unit" &&
   grep -q '^# macbook81-cpu-cap runtime helper\.' "$helper"; then
  legacy_owned=yes
fi
cpu_cap_config_preflight "$config" "$marker" "$max_khz" "$legacy_owned" || fail 'Refusing to alter CPU config'
for other in cpupower.service tuned.service auto-cpufreq.service; do
  if systemctl is-active --quiet "$other" 2>/dev/null; then
    printf 'WARNING: %s is active and may override frequency limits.\n' "$other" >&2
  fi
done
install -Dm755 "$helper_src" "$helper"
install -Dm644 "$service_src" "$unit"
printf '%s\n' "$max_khz" > "$config"
chmod 0644 "$config"
cpu_cap_config_mark "$config" "$marker" || fail 'Could not record CPU config ownership'
systemctl daemon-reload
systemctl enable macbook81-cpu-cap.service
systemctl restart macbook81-cpu-cap.service
printf '\nCPU cap installed and enabled at boot (%s MHz requested).\n' "$max_mhz"
"$helper" status
printf 'Check after reboot with: bash scripts/check-cpu-limit.sh\n'
printf 'Remove with: sudo bash scripts/uninstall-cpu-limit.sh\n'