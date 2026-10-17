#!/usr/bin/env bash
# Create a reviewable evidence bundle for the MacBook8,1 audio patch and speaker routing.
# Read-only with respect to system settings; copies selected files to a local archive.
set -euo pipefail
umask 077
out="${1:-macbook81-audio-details.tar.gz}"
if (( $# > 1 )); then echo 'Usage: bash collect-macbook81-audio-details.sh [output.tar.gz]' >&2; exit 2; fi
if [[ -e "$out" || -L "$out" ]]; then echo "Refusing to overwrite $out" >&2; exit 1; fi
if [[ "$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)" != 'MacBook8,1' ]]; then
  echo 'This script is intended only for MacBook8,1.' >&2; exit 1
fi
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/config" "$work/source"
{
  echo 'MacBook8,1 audio route and patch evidence'
  echo 'Review archive contents before sharing; config and paths may be personal.'
  printf 'Kernel: '; uname -r
  printf 'DKMS source target: '; readlink -f /var/lib/dkms/macbook12-audio/0.1/source 2>/dev/null || true
  echo
  echo '--- DKMS ---'
  if command -v dkms >/dev/null 2>&1; then dkms status 2>&1 || true; fi
  echo
  echo '--- AUDIO SINKS ---'
  if command -v pactl >/dev/null 2>&1; then
    pactl get-default-sink 2>&1 || true
    pactl list sinks 2>&1 || true
  fi
  echo
  echo '--- WIREPLUMBER ---'
  if command -v wpctl >/dev/null 2>&1; then wpctl status 2>&1 || true; fi
  echo
  echo '--- SOURCE MANIFEST ---'
} > "$work/report.txt"
for entry in \
  "$HOME/.config/pipewire/pipewire.conf.d/51-macbook81-speaker.conf:pipewire-speaker.conf" \
  "$HOME/.config/wireplumber/wireplumber.conf.d/51-mb81-rawpcm-speaker.conf:wireplumber-rawpcm.conf" \
  '/etc/modprobe.d/mb81-singlecmd.conf:mb81-singlecmd.conf'; do
  path="${entry%:*}"; name="${entry##*:}"
  if [[ -f "$path" && -r "$path" ]]; then
    cp -- "$path" "$work/config/$name"
    echo "Copied config: $name" >> "$work/report.txt"
  else
    echo "Unavailable config: $path" >> "$work/report.txt"
  fi
done
source_dir='/usr/local/src/macbook81-audio-repair'
count=0
if [[ -d "$source_dir" && -r "$source_dir" ]]; then
  while IFS= read -r -d '' file; do
    (( count < 250 )) || { echo 'Source collection capped at 250 files' >> "$work/report.txt"; break; }
    rel="${file#./}"
    [[ -r "$source_dir/$rel" ]] || continue
    mkdir -p -- "$work/source/$(dirname -- "$rel")"
    cp -- "$source_dir/$rel" "$work/source/$rel"
    printf 'source/%s\n' "$rel" >> "$work/report.txt"
    ((count+=1))
  done < <(cd "$source_dir" && find . -maxdepth 8 -type f -size -1048577c \
    \( -name '*.c' -o -name '*.h' -o -name '*.patch' -o -name '*.diff' \
       -o -name 'dkms.conf' -o -name 'Makefile*' -o -name 'Kbuild*' \
       -o -name 'LICENSE*' -o -name 'COPYING*' -o -name '*.sh' \) -print0)
else
  echo "Source directory inaccessible: $source_dir" >> "$work/report.txt"
fi
tar -C "$work" -czf "$out" .
echo "Created $out ($count source files)."
echo 'IMPORTANT: Inspect with tar -tzf and extract locally to review before uploading.'
