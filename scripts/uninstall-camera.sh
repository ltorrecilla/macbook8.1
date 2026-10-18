#!/usr/bin/env bash
# Remove only driver source/DKMS state owned by this repository's installer.
set -euo pipefail
CAM_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=camera-common.sh
source "$CAM_SCRIPT_DIR/camera-common.sh"

main() {
  if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
    printf 'Usage: sudo bash scripts/uninstall-camera.sh\nRemoves only this wrapper\047s driver/DKMS source; always preserves firmware and packages.\n'
    return 0
  fi
  (( $# == 0 )) || camera_fail 'No positional arguments are supported; use --help.'
  camera_require_root
  camera_require_commands dkms modprobe modinfo stat sha256sum readlink find sort xargs
  if [[ ! -e "$CAM_SRC_DIR" && ! -L "$CAM_SRC_DIR" && ! -e "$CAM_DKMS_DIR" ]]; then
    printf 'No driver owned by this installer is present. Nothing removed.\n'
    return 0
  fi
  camera_verify_owned_source
  camera_check_other_versions
  # A busy camera must be closed before removing the loaded driver. Do not force
  # unload it or terminate applications. Stop before deleting anything on error.
  if [[ -d "$CAM_LOADED_MODULE" ]]; then
    modprobe -r "$CAM_MODULE" || camera_fail 'Could not unload facetimehd. Close camera apps and retry; no files were removed.'
  fi
  if [[ -d "$CAM_DKMS_DIR/$CAM_DKMS_VERSION" ]]; then
    dkms remove -m "$CAM_MODULE" -v "$CAM_DKMS_VERSION" --all
  fi
  rm -rf -- "$CAM_SRC_DIR"
  printf 'Removed this installer\047s facetimehd driver and source.\n'
  printf 'Firmware in %s and all packages were preserved.\n' "$CAM_FW_DIR"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
