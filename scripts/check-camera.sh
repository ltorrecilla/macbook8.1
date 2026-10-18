#!/usr/bin/env bash
# Read-only camera diagnostics. Does not load modules or restart services.
set -euo pipefail
CAM_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=camera-common.sh
source "$CAM_SCRIPT_DIR/camera-common.sh"

main() {
  if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
    printf 'Usage: bash scripts/check-camera.sh\nRead-only diagnostics; run as your normal desktop user.\n'
    return 0
  fi
  (( $# == 0 )) || camera_fail 'No positional arguments are supported; use --help.'
  local missing=0 name node path
  printf 'Model: %s\nKernel: %s\n' "$(cat "$CAM_DMI_PATH" 2>/dev/null || printf unknown)" "$CAM_KERNEL"
  printf '\nCamera PCI device and driver:\n'
  if command -v lspci >/dev/null 2>&1; then lspci -nnk -d 14e4:1570 || true; else printf 'lspci unavailable (pciutils).\n'; fi
  printf '\nInstalled package versions:\n'
  if command -v pacman >/dev/null 2>&1; then pacman -Q linux-cachyos linux-cachyos-headers dkms 2>/dev/null || true; fi
  printf '\nDriver module for the running kernel:\n'
  if command -v modinfo >/dev/null 2>&1 && modinfo "$CAM_MODULE"; then :; else missing=1; fi
  printf '\nDKMS registrations:\n'
  if command -v dkms >/dev/null 2>&1; then dkms status -m "$CAM_MODULE" || true; else printf 'dkms unavailable.\n'; fi
  printf '\nInstallation ownership:\n'
  if camera_owned_source; then
    printf 'Driver source has this repository installer\047s ownership marker.\n'
  else
    printf 'No matching installer ownership marker (manual/package installations are preserved).\n'
  fi
  printf '\nExpected firmware 5.60.0 and MacBook sensor calibration:\n'
  if command -v sha256sum >/dev/null 2>&1; then
    for name in firmware.bin 1675_01XX.dat; do
      local hash=$CAM_FIRMWARE_HASH
      [[ "$name" != 1675_01XX.dat ]] || hash=$CAM_CALIBRATION_HASH
      if camera_hash_matches "$CAM_FW_DIR/$name" "$hash"; then
        printf 'OK: %s\n' "$CAM_FW_DIR/$name"
      else
        printf 'MISSING, DIFFERENT, OR UNREADABLE: %s\n' "$CAM_FW_DIR/$name"
        missing=1
      fi
    done
  else
    printf 'sha256sum unavailable; firmware not verified.\n'
    missing=1
  fi
  printf '\nV4L2 devices:\n'
  if command -v v4l2-ctl >/dev/null 2>&1; then v4l2-ctl --list-devices || true; else printf 'Install v4l-utils for v4l2-ctl.\n'; fi
  local found=0
  for node in "$CAM_VIDEO_DIR"/video*; do
    [[ -e "$node" ]] || continue
    path="$CAM_DEV_DIR/${node##*/}"
    printf '\n%s: %s\n' "$path" "$(cat "$node/name" 2>/dev/null || printf unknown)"
    ls -l -- "$path" 2>/dev/null || true
    if [[ "$(readlink -f "$node/device/driver/module" 2>/dev/null || true)" == */facetimehd ]]; then
      found=1
      printf 'facetimehd node. Manual capture test: mpv av://v4l2:%s\n' "$path"
    fi
    if command -v fuser >/dev/null 2>&1; then fuser -v "$path" 2>&1 || true; fi
  done
  (( found != 0 )) || { printf 'No video node linked to facetimehd was found.\n'; missing=1; }
  printf '\nPipeWire/WirePlumber view (optional; no service changes):\n'
  if command -v wpctl >/dev/null 2>&1; then wpctl status || true; else printf 'wpctl unavailable.\n'; fi
  printf '\nClose mpv fully before testing another camera app.\n'
  printf 'If that app has no camera, record its name and installation type, plus this output.\n'
  printf 'A module/video node does not prove live capture or application compatibility. See docs/camera.md.\n'
  return "$missing"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
