#!/usr/bin/env bash
# Gather only named missing audio installer helpers (read-only to the OS).
set -euo pipefail
umask 077
out="${1:-macbook81-audio-support.tar.gz}"
if [[ -e "$out" || -L "$out" ]]; then echo "Refusing to overwrite $out" >&2; exit 1; fi
[[ $(cat /sys/class/dmi/id/product_name 2>/dev/null || true) == MacBook8,1 ]] || { echo 'MacBook8,1 required' >&2; exit 1; }
[[ $EUID -ne 0 ]] || { echo 'Run without sudo' >&2; exit 1; }
temp=$(mktemp -d)
trap 'rm -rf -- "$temp"' EXIT
mkdir -p "$temp/files"
printf 'Read before sharing. File paths and source contents may contain personal information.\n' > "$temp/README-REVIEW-FIRST.txt"
: > "$temp/file-list.txt"
count=0
# Look for ONLY the three missing upstream installer dependencies in likely places.
# No system settings changed; no general data harvested.
for root in /usr/local/bin /etc/systemd/system /etc/systemd/user /usr/local/src/macbook81-audio-repair "$HOME"; do
    [[ -d $root ]] || continue
    depth=3; [[ $root == "$HOME" ]] && depth=7
    while IFS= read -r -d '' file; do
        [[ -r $file && -f $file && ! -L $file ]] || continue
        ((count+=1))
        if (( count > 40 )); then echo 'Collected up to 40 matching files; stopping.' >> "$temp/file-list.txt"; break 2; fi
        base=$(basename -- "$file")
        cp -- "$file" "$temp/files/$(printf '%03d' "$count")-$base"
        printf '%03d-%s <- %s\n' "$count" "$base" "$file" >> "$temp/file-list.txt"
    done < <(find "$root" -maxdepth "$depth" -type f \( -name 'efi_recover.py' -o -name 'mb81-resume-recover.service' -o -name 'mb81-jack-switch.service' \) -print0 2>/dev/null || true)
done
if (( count == 0 )); then printf 'None of the three files found in searched locations.\n' >> "$temp/file-list.txt"; fi
printf 'Collected %s file(s).\n' "$count" >> "$temp/file-list.txt"
tar -czf "$out" -C "$temp" .
printf 'Saved %s (%s matching files). Review with tar -tzf and inspect before uploading.\n' "$out" "$count"
