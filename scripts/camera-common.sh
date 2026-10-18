#!/usr/bin/env bash
# Shared constants and checks for the optional MacBook8,1 camera scripts.
# Source this file; it performs no installation or service changes.

CAM_MODULE=facetimehd
CAM_DRIVER_RELEASE=0.7.2
CAM_DRIVER_COMMIT=54fb8f25fcf76d4d5af682875f044dc0b6fa0b65
# Upstream release 0.7.2 still declares this version in dkms.conf.
CAM_DKMS_VERSION=0.7.0.1
CAM_FIRMWARE_COMMIT=60ee21228d9ca00a7bd84fdaefaff00a81f1db91
CAM_FIRMWARE_HASH=240ef2e991f1d089d8228ce11d92b66bfa4b3d7289ec4fee228b64a713024330
CAM_CALIBRATION_HASH=b7a38aef2755721bb28c92d84a15654b17e9fb3b0a0f088a384a981fc8fe16d6
CAM_KERNEL="$(uname -r)"
CAM_SRC_PARENT=/usr/src
CAM_SRC_DIR="$CAM_SRC_PARENT/$CAM_MODULE-$CAM_DKMS_VERSION"
CAM_DKMS_DIR=/var/lib/dkms/facetimehd
CAM_FW_DIR=/usr/lib/firmware/facetimehd
CAM_HEADERS_DIR="/usr/lib/modules/$CAM_KERNEL/build"
CAM_DMI_PATH=/sys/class/dmi/id/product_name
CAM_PCI_DIR=/sys/bus/pci/devices
CAM_VIDEO_DIR=/sys/class/video4linux
CAM_LOADED_MODULE=/sys/module/facetimehd
CAM_DEV_DIR=/dev
CAM_ARCH_RELEASE=/etc/arch-release
CAM_OWNER="macbook81-camera-v1 $CAM_DRIVER_COMMIT"

camera_fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

camera_require_commands() {
  local command
  for command in "$@"; do
    command -v "$command" >/dev/null 2>&1 || camera_fail "Missing command: $command. See docs/camera.md for prerequisites."
  done
}

camera_require_user() {
  (( EUID != 0 )) || camera_fail 'Run as your ordinary user: bash scripts/install-camera.sh (it uses sudo when needed).'
}

camera_require_root() {
  (( EUID == 0 )) || camera_fail 'Run with sudo: sudo bash scripts/uninstall-camera.sh'
}

camera_require_hardware() {
  [[ "$(cat "$CAM_DMI_PATH" 2>/dev/null || true)" == 'MacBook8,1' ]] || camera_fail 'Only MacBook8,1 is supported.'
  local device
  for device in "$CAM_PCI_DIR"/*; do
    [[ -r "$device/vendor" && -r "$device/device" ]] || continue
    if [[ "$(cat "$device/vendor")" == 0x14e4 && "$(cat "$device/device")" == 0x1570 ]]; then
      return 0
    fi
  done
  camera_fail 'The Broadcom FaceTime HD PCI device 14e4:1570 was not found.'
}

camera_hash_matches() {
  local path=$1 expected=$2 actual
  [[ -f "$path" && ! -L "$path" ]] || return 1
  actual="$(sha256sum -- "$path")" || return 1
  [[ "${actual%% *}" == "$expected" ]]
}

camera_firmware_matches() {
  [[ ! -L "$CAM_FW_DIR" ]] &&
    camera_hash_matches "$CAM_FW_DIR/firmware.bin" "$CAM_FIRMWARE_HASH" &&
    camera_hash_matches "$CAM_FW_DIR/1675_01XX.dat" "$CAM_CALIBRATION_HASH"
}

camera_check_firmware_conflicts() {
  [[ ! -L "$CAM_FW_DIR" ]] || camera_fail "Preserving symbolic link $CAM_FW_DIR; inspect it manually."
  local name hash suffix
  for name in firmware.bin 1675_01XX.dat; do
    hash=$CAM_FIRMWARE_HASH
    [[ "$name" != 1675_01XX.dat ]] || hash=$CAM_CALIBRATION_HASH
    if [[ -e "$CAM_FW_DIR/$name" || -L "$CAM_FW_DIR/$name" ]]; then
      camera_hash_matches "$CAM_FW_DIR/$name" "$hash" || camera_fail "Preserving different or unreadable firmware: $CAM_FW_DIR/$name"
    fi
    for suffix in xz zst; do
      [[ ! -e "$CAM_FW_DIR/$name.$suffix" && ! -L "$CAM_FW_DIR/$name.$suffix" ]] ||
        camera_fail "Preserving compressed firmware: $CAM_FW_DIR/$name.$suffix; inspect the existing installation first."
    done
  done
}

camera_owned_source() {
  local marker="$CAM_SRC_DIR/.macbook81-camera-owner"
  [[ -d "$CAM_SRC_DIR" && ! -L "$CAM_SRC_DIR" && -f "$marker" && ! -L "$marker" ]] &&
    [[ "$(stat -c %u -- "$CAM_SRC_DIR")" == 0 && "$(stat -c %u -- "$marker")" == 0 ]] &&
    [[ "$(cat "$marker")" == "$CAM_OWNER" ]]
}

camera_source_manifest() (
  cd "$1" || return 1
  find . -type f ! -path './.macbook81-camera-owner' ! -path './.macbook81-camera-sha256' -print0 |
    LC_ALL=C sort -z | xargs -0 sha256sum
)

camera_verify_owned_source() {
  camera_owned_source || camera_fail 'The driver source is not owned by this installer; leaving it unchanged.'
  local manifest="$CAM_SRC_DIR/.macbook81-camera-sha256"
  [[ -f "$manifest" && ! -L "$manifest" && "$(stat -c %u -- "$manifest")" == 0 ]] || camera_fail 'Missing or untrusted source manifest; leaving source unchanged.'
  # This pinned archive contains only regular files/directories. Check the whole
  # file list too, so uninstall cannot erase files or links added after setup.
  local special current
  special="$(find "$CAM_SRC_DIR" ! -type f ! -type d -print -quit)" || camera_fail 'Cannot inspect the driver source.'
  [[ -z "$special" ]] || camera_fail "Unexpected link or special file in driver source: $special; leaving it unchanged."
  current="$(camera_source_manifest "$CAM_SRC_DIR")" || camera_fail 'Cannot verify the driver source.'
  [[ "$current" == "$(cat "$manifest")" ]] ||
    camera_fail 'Installed driver source has changed; inspect it before retrying or uninstalling.'
  local registered="$CAM_DKMS_DIR/$CAM_DKMS_VERSION/source"
  if [[ -e "$registered" || -L "$registered" ]]; then
    [[ -L "$registered" && "$(readlink -f -- "$registered")" == "$CAM_SRC_DIR" ]] ||
      camera_fail 'DKMS points to a different source directory; leaving it unchanged.'
  fi
}

camera_has_existing_driver() {
  local path
  for path in "$CAM_SRC_PARENT"/facetimehd-* "$CAM_DKMS_DIR"; do
    [[ ! -e "$path" && ! -L "$path" ]] || return 0
  done
  modinfo "$CAM_MODULE" >/dev/null 2>&1
}

camera_check_other_versions() {
  local path
  for path in "$CAM_SRC_PARENT"/facetimehd-*; do
    [[ ! -e "$path" && ! -L "$path" ]] && continue
    [[ "$path" == "$CAM_SRC_DIR" ]] || camera_fail "Another driver source exists: $path; leaving it unchanged."
  done
  for path in "$CAM_DKMS_DIR"/*; do
    [[ ! -e "$path" && ! -L "$path" ]] && continue
    if [[ "$path" == "$CAM_DKMS_DIR/$CAM_DKMS_VERSION" && -d "$path" && ! -L "$path" ]]; then
      continue
    fi
    # DKMS keeps kernel-<release>-<arch> links alongside version directories.
    # Only links into our version are compatible with this installation.
    if [[ "$path" == "$CAM_DKMS_DIR"/kernel-* && -L "$path" &&
      "$(readlink -f -- "$path")" == "$CAM_DKMS_DIR/$CAM_DKMS_VERSION/"* ]]; then
      continue
    fi
    camera_fail "Another or unexpected DKMS entry exists: $path; inspect it first."
  done
}
