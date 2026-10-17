#!/usr/bin/env bash
# Read-only inventory of MacBook8,1 patched audio driver evidence.
set -euo pipefail
out="${1:-macbook81-audio-evidence.txt}"
[[ ! -e "$out" && ! -L "$out" ]] || { echo "Refusing to overwrite $out" >&2; exit 1; }
(
  set -C
  {
    echo "MacBook8,1 audio inventory (review paths/config before sharing)"
    printf 'Model: '; cat /sys/class/dmi/id/product_name 2>/dev/null || true
    printf 'Kernel: '; uname -r
    echo; echo "DKMS status:"
    if command -v dkms >/dev/null; then dkms status || true; fi
    echo; echo "Audio module details:"
    for mod in snd_hda_intel snd_hda_codec_cs420x snd_hda_codec_generic snd_hda_codec snd_hda_core; do
      echo "$mod"
      if command -v modinfo >/dev/null; then
        modinfo -F filename "$mod" 2>/dev/null || true
        modinfo -F vermagic "$mod" 2>/dev/null || true
      fi
    done
    echo; echo "DKMS source symlinks:"
    if [[ -d /var/lib/dkms ]]; then
      find /var/lib/dkms -mindepth 2 -maxdepth 3 -name source -type l -print 2>/dev/null || true
    fi
    echo; echo "Candidate patch / DKMS source paths (no source contents):"
    for dir in /usr/src /var/lib/dkms "$HOME"; do
      [[ -d "$dir" ]] || continue
      find "$dir" -maxdepth 4 -type f \( -iname '*cs420*' -o -name 'dkms.conf' -o -name '*.patch' -o -name '*.diff' \) -print 2>/dev/null | head -n 100 || true
    done
    echo; echo "Audio modprobe config:"
    if [[ -r /etc/modprobe.d/mb81-singlecmd.conf ]]; then cat /etc/modprobe.d/mb81-singlecmd.conf; fi
    echo; echo "PipeWire config candidates (paths only):"
    for dir in "$HOME/.config/pipewire" "$HOME/.config/wireplumber" /etc/pipewire /etc/wireplumber; do
      [[ -d "$dir" ]] || continue
      find "$dir" -maxdepth 4 -type f \( -name '*.conf' -o -name '*.lua' \) -print 2>/dev/null | head -n 100 || true
    done
    echo; echo "Sinks and default:"
    if command -v pactl >/dev/null; then pactl list short sinks || true; pactl get-default-sink || true; fi
  } > "$out"
)
echo "Saved $out. Review private paths and config before uploading."
