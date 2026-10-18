#!/usr/bin/env bash
# Optional facetimehd setup for MacBook8,1 on CachyOS/Arch.
set -euo pipefail
CAM_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=camera-common.sh
source "$CAM_SCRIPT_DIR/camera-common.sh"

usage() {
  cat <<'USAGE'
Usage: bash scripts/install-camera.sh

Run as an ordinary user. Downloads pinned upstream sources and extracts
firmware without root; uses sudo to install files, register/build with DKMS,
and load the camera module. Install prerequisites from docs/camera.md first.

Existing manual/package installations are preserved, never adopted.
Rollback for this wrapper's driver: sudo bash scripts/uninstall-camera.sh
Firmware is retained on rollback. --help prints this message.
USAGE
}

camera_fetch_source() {
  local url=$1 commit=$2 destination=$3
  git init --quiet "$destination"
  git -C "$destination" fetch --quiet --depth 1 "$url" "$commit"
  git -C "$destination" checkout --quiet --detach FETCH_HEAD
  [[ "$(git -C "$destination" rev-parse HEAD)" == "$commit" ]] || camera_fail 'Upstream commit verification failed.'
}

camera_install_cleanup() {
  local result=$?
  trap - EXIT
  if [[ -n "${camera_root_stage:-}" && "$camera_root_stage" == "$CAM_SRC_PARENT"/.macbook81-camera.* ]]; then
    sudo rm -rf -- "$camera_root_stage" || true
  fi
  [[ -z "${camera_work_dir:-}" ]] || rm -rf -- "$camera_work_dir"
  if (( result != 0 )) && camera_owned_source; then
    printf '\nSetup stopped. Owned source is retained for diagnosis/retry.\n' >&2
    printf 'DKMS build log: %s/%s/build/make.log\n' "$CAM_DKMS_DIR" "$CAM_DKMS_VERSION" >&2
    printf 'Rollback: sudo bash scripts/uninstall-camera.sh\n' >&2
  fi
  exit "$result"
}

main() {
  if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then usage; return 0; fi
  (( $# == 0 )) || camera_fail 'No positional arguments are supported; use --help.'
  camera_require_user
  # The private mktemp parent stays 0700; installed public source/metadata must
  # remain readable on later runs even if the user's usual umask is 077.
  umask 022
  camera_require_commands cat stat sha256sum modinfo readlink
  camera_require_hardware
  [[ -f "$CAM_ARCH_RELEASE" ]] || camera_fail 'This installer targets CachyOS/Arch Linux.'

  if ! camera_owned_source && camera_has_existing_driver; then
    if modinfo "$CAM_MODULE" >/dev/null 2>&1 && camera_firmware_matches; then
      printf 'Existing facetimehd module and expected firmware are present.\n'
      printf 'Keeping your installation unchanged; it is not adopted by this wrapper.\n'
      printf 'Check it with: bash scripts/check-camera.sh\n'
      return 0
    fi
    camera_fail 'An existing facetimehd installation needs inspection. Nothing changed. Run bash scripts/check-camera.sh and see docs/camera.md.'
  fi
  camera_check_other_versions
  camera_check_firmware_conflicts
  [[ -f "$CAM_HEADERS_DIR/Makefile" && -r "$CAM_HEADERS_DIR/include/config/kernel.release" ]] ||
    camera_fail "Install headers matching the running kernel $CAM_KERNEL; see docs/camera.md."
  [[ "$(cat "$CAM_HEADERS_DIR/include/config/kernel.release")" == "$CAM_KERNEL" ]] ||
    camera_fail "Headers do not match the running kernel $CAM_KERNEL. Boot the matching kernel or install matching headers first."
  camera_require_commands sudo dkms git make curl xzcat gzip which tar find sort xargs install cp mv mktemp chmod modprobe sed mkdir rm
  if camera_owned_source; then camera_verify_owned_source; fi

  camera_work_dir="$(mktemp -d -t macbook81-camera.XXXXXXXX)"
  camera_root_stage=
  trap camera_install_cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  if ! camera_firmware_matches; then
    printf 'Extracting firmware 5.60.0 using pinned upstream %s...\n' "$CAM_FIRMWARE_COMMIT"
    camera_fetch_source https://github.com/patjak/facetimehd-firmware.git "$CAM_FIRMWARE_COMMIT" "$camera_work_dir/firmware"
    make -C "$camera_work_dir/firmware" FW_VER=5.60.0
    camera_hash_matches "$camera_work_dir/firmware/firmware.bin" "$CAM_FIRMWARE_HASH" || camera_fail 'Extracted firmware checksum does not match.'
    camera_hash_matches "$camera_work_dir/firmware/1675_01XX.dat" "$CAM_CALIBRATION_HASH" || camera_fail 'Extracted sensor calibration checksum does not match.'
    chmod 0644 "$camera_work_dir/firmware/firmware.bin" "$camera_work_dir/firmware/1675_01XX.dat"
  fi

  if ! camera_owned_source; then
    printf 'Preparing driver release %s (%s)...\n' "$CAM_DRIVER_RELEASE" "$CAM_DRIVER_COMMIT"
    camera_fetch_source https://github.com/patjak/facetimehd.git "$CAM_DRIVER_COMMIT" "$camera_work_dir/driver"
    mkdir "$camera_work_dir/source"
    git -C "$camera_work_dir/driver" archive HEAD | tar -x -C "$camera_work_dir/source"
    [[ "$(sed -n 's/^PACKAGE_VERSION=//p' "$camera_work_dir/source/dkms.conf")" == "$CAM_DKMS_VERSION" ]] || camera_fail 'Unexpected upstream DKMS version.'
    printf '%s\n' "$CAM_OWNER" > "$camera_work_dir/source/.macbook81-camera-owner"
    camera_source_manifest "$camera_work_dir/source" > "$camera_work_dir/source/.macbook81-camera-sha256"
  fi

  # Recheck before the first privileged mutation. Do not replace a setup that
  # appeared while sources were downloading.
  if ! camera_owned_source && camera_has_existing_driver; then
    camera_fail 'Another facetimehd installation appeared during preparation; leaving it unchanged.'
  fi
  camera_check_other_versions
  camera_check_firmware_conflicts
  sudo -v
  if ! camera_owned_source; then
    camera_root_stage="$(sudo mktemp -d "$CAM_SRC_PARENT/.macbook81-camera.XXXXXXXX")"
    sudo cp -R -- "$camera_work_dir/source/." "$camera_root_stage/"
    sudo chmod 0755 "$camera_root_stage"
    sudo mv --no-clobber -T -- "$camera_root_stage" "$CAM_SRC_DIR"
    [[ ! -d "$camera_root_stage" ]] || camera_fail 'Driver source appeared concurrently; no source was overwritten.'
    camera_root_stage=
  fi
  camera_verify_owned_source

  if ! camera_firmware_matches; then
    [[ -d "$CAM_FW_DIR" ]] || sudo install -d -m 0755 "$CAM_FW_DIR"
    local name
    for name in firmware.bin 1675_01XX.dat; do
      if [[ ! -e "$CAM_FW_DIR/$name" ]]; then
        sudo cp --no-clobber -- "$camera_work_dir/firmware/$name" "$CAM_FW_DIR/$name"
        sudo chmod 0644 "$CAM_FW_DIR/$name"
      fi
    done
    camera_firmware_matches || camera_fail 'Installed firmware failed checksum verification; stopping before loading the driver.'
  fi

  if [[ ! -d "$CAM_DKMS_DIR/$CAM_DKMS_VERSION" ]]; then
    sudo dkms add -m "$CAM_MODULE" -v "$CAM_DKMS_VERSION"
  fi
  local status
  status="$(sudo dkms status -m "$CAM_MODULE" -v "$CAM_DKMS_VERSION" -k "$CAM_KERNEL")"
  if [[ "$status" == *': installed'* && "$status" != *': installed' ]]; then
    camera_fail "DKMS reports an installed module with a warning; inspect it before replacement: $status"
  fi
  if [[ "$status" != *': installed' ]]; then
    sudo dkms install -m "$CAM_MODULE" -v "$CAM_DKMS_VERSION" -k "$CAM_KERNEL"
    status="$(sudo dkms status -m "$CAM_MODULE" -v "$CAM_DKMS_VERSION" -k "$CAM_KERNEL")"
  fi
  [[ "$status" == "$CAM_MODULE/$CAM_DKMS_VERSION, $CAM_KERNEL, "*': installed' ]] ||
    camera_fail "DKMS did not report a clean installed module for the running kernel: $status"
  sudo modprobe "$CAM_MODULE"
  printf '\nCamera driver installed for %s and module load succeeded.\n' "$CAM_KERNEL"
  printf 'Check: bash scripts/check-camera.sh\n'
  printf 'Then select its video node and test with mpv; see docs/camera.md.\n'
  printf 'This does not verify camera discovery in desktop or sandboxed apps.\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
