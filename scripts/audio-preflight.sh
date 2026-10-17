#!/usr/bin/env bash
# Read-only MacBook8,1 audio installer readiness check (no sudo required).
set -u
failures=0
warnings=0
pass() { printf '[OK]   %s\n' "$*"; }
warn() { printf '[WAIT] %s\n' "$*"; warnings=$((warnings+1)); }
fail() { printf '[BLOCK] %s\n' "$*"; failures=$((failures+1)); }

[[ "${EUID:-$(id -u)}" -ne 0 ]] || warn 'Run as your desktop user; read-only checks need no sudo'
model=$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)
[[ "$model" == 'MacBook8,1' ]] && pass "Hardware: $model" || fail "Unsupported model: ${model:-unknown}"
command -v pacman >/dev/null && pass 'Arch-family pacman present' || fail 'pacman unavailable: CachyOS-only preparation'
command -v dkms >/dev/null && pass 'DKMS present' || fail 'DKMS missing'
command -v mkinitcpio >/dev/null && pass 'mkinitcpio present' || fail 'mkinitcpio missing'
command -v make >/dev/null && pass 'make present' || warn 'Build tools incomplete: make missing'
command -v cc >/dev/null && pass 'C compiler present' || warn 'Build tools incomplete: cc missing'
kver=$(uname -r)
[[ -d "/usr/lib/modules/$kver/build" || -d "/lib/modules/$kver/build" ]] && pass "Kernel headers: $kver" || fail "No build headers for $kver"
if command -v dkms >/dev/null; then
    if dkms status 2>/dev/null | grep -Eq '^macbook12-audio/0\.1, .*: installed'; then
        pass 'Existing macbook12-audio/0.1 installed (do not overwrite!)'
    else
        warn 'No known working macbook12-audio/0.1 install found'
    fi
fi
if [[ -L /var/lib/dkms/macbook12-audio/0.1/source ]]; then
    link=$(readlink /var/lib/dkms/macbook12-audio/0.1/source || true)
    pass "DKMS source link: $link"
fi
for name in snd_hda_intel snd_hda_codec_cs420x snd_hda_codec_generic; do
    if command -v modinfo >/dev/null; then
        module=$(modinfo -n "$name" 2>/dev/null || true)
        [[ "$module" == *'/updates/dkms/'* ]] && pass "$name: DKMS version" || warn "$name: not resolved to a DKMS file (${module:-unknown})"
    fi
done
for path in /etc/modprobe.d/mb81-singlecmd.conf "$HOME/.config/wireplumber/wireplumber.conf.d/51-mb81-rawpcm-speaker.conf"; do
    [[ -r "$path" ]] && pass "Config present: $path" || warn "Config absent: $path"
done
if command -v pactl >/dev/null; then
    sinks=$(pactl list short sinks 2>/dev/null || true)
    grep -q 'MacBook_Speaker_Raw' <<< "$sinks" && pass 'MacBook_Speaker_Raw available' || warn 'Raw speaker sink not visible'
fi
printf '\nRead-only preflight: %s blockers, %s warnings.\n' "$failures" "$warnings"
printf 'No installation is attempted by this script. Do NOT uninstall your working DKMS modules.\n'
(( failures == 0 ))
