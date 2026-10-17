#!/usr/bin/env python3
"""Interactive, reversible MacBook8,1 speaker EQ audition.

Backs up the existing user PipeWire filter-chain config, changes only
the 258 Hz peaking EQ gain from 0.0 to +2.5 dB on L and R, and temporarily
selects the existing virtual EQ sink. Does not modify the high-pass filters,
raw speaker channel routing, DKMS modules or firmware.

--restore recovers the backup if an earlier run was interrupted.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

CONFIG = Path.home() / ".config/pipewire/pipewire.conf.d/51-macbook81-speaker.conf"
STATE = Path(os.getenv("XDG_STATE_HOME") or (Path.home() / ".local/state")) / "macbook81-audio-audition"
BACKUP = STATE / "original.conf"
DEFAULT = STATE / "original-sink.txt"
EQ_SINK = "input.MacBook_Speaker"

def run(*args, capture=False, check=True):
    return subprocess.run(args, text=True, capture_output=capture, check=check)

def ensure_environment():
    if os.geteuid() == 0:
        raise RuntimeError("Run as your normal desktop user, not with sudo")
    if not sys.stdin.isatty():
        raise RuntimeError("Open an interactive terminal to audition or restore")
    if not all(shutil.which(p) for p in ("pactl", "systemctl")):
        raise RuntimeError("Missing pactl or systemctl")
    model = Path("/sys/class/dmi/id/product_name")
    if not model.is_file() or model.read_text().strip() != "MacBook8,1":
        raise RuntimeError("Only MacBook8,1 is supported")

def wait_for_audio():
    for _ in range(12):
        probe = run("pactl", "info", capture=True, check=False)
        if probe.returncode == 0:
            return
        time.sleep(0.5)
    raise RuntimeError("PipeWire audio server did not become ready")

def reload_filter():
    run("systemctl", "--user", "restart", "pipewire.service")
    run("systemctl", "--user", "try-restart", "wireplumber.service", check=False)
    wait_for_audio()

def build_variant(original, voice=False):
    updated = original
    for name in ("L_peq1", "R_peq1"):
        pattern = (r"(\bname\s*=\s*" + re.escape(name) +
                   r'\s+label\s*=\s*bq_peaking\s*\n\s*control\s*=\s*\{'
                   r'\s*"Freq"\s*=\s*258\.0\s+"Q"\s*=\s*0\.79\s+'
                   r'"Gain"\s*=\s*)0\.0\b')
        updated, count = re.subn(pattern, lambda m: m.group(1) + ("4.0" if voice else "2.5"), updated)
        if voice and count == 1:
            # Shift the SAME filter's centre frequency from 258 to 185 Hz.
            frequency = (r'(\bname\s*=\s*' + re.escape(name)
                         + r'\s+label\s*=\s*bq_peaking\s+control\s*=\s*\{\s*"Freq"\s*=\s*)258\.0')
            updated, fcount = re.subn(frequency, lambda m: m.group(1) + "185.0", updated)
            if fcount != 1:
                raise RuntimeError(f"Could not retune {name} to 185 Hz.")
        if count != 1:
            raise RuntimeError(f"Expected one {name} gain=0.0 filter; found {count}. No change made.")
    return updated

def switch_output(target):
    """Switch output and move ordinary PulseAudio app streams, not filter links."""
    run("pactl", "set-default-sink", target)
    detail = run("pactl", "list", "sink-inputs", capture=True).stdout
    moved = 0
    for block in re.split(r"(?=^Sink Input #\d+\s*$)", detail, flags=re.M):
        match = re.search(r"^Sink Input #(\d+)\s*$", block, re.M)
        if not match or "node.link-group =" in block or 'node.group = "filter-chain-' in block:
            continue
        app = re.search(r'application\.name = "([^"]+)"', block)
        if not app or app.group(1).lower() in ("pipewire", "wireplumber"):
            continue
        result = run("pactl", "move-sink-input", match.group(1), target, check=False)
        if result.returncode == 0:
            moved += 1
    print(f"Selected {target}; moved {moved} running PulseAudio app stream(s).")
    print("If playback is still on the other device, choose the output for that app")
    print("in Plasma Sound > Applications, or restart playback.")


def sink_available(name):
    """Match the sink's exact PipeWire/Pulse name, not a substring of a line."""
    result = run("pactl", "list", "short", "sinks", capture=True, check=False)
    if result.returncode != 0:
        return False
    return any(len(fields := line.split()) > 1 and fields[1] == name
               for line in result.stdout.splitlines())


def wait_for_sink(name, seconds=15):
    for _ in range(max(1, int(seconds * 2))):
        if sink_available(name):
            return True
        time.sleep(0.5)
    return sink_available(name)


def restore():
    if not BACKUP.is_file():
        print("No previous audition backup found; nothing to restore.")
        return
    print("Restoring original PipeWire EQ configuration...")
    # An interrupted restore may already have copied the config successfully.
    # Do not restart PipeWire unnecessarily or overwrite the backup.
    if not CONFIG.is_file() or CONFIG.read_bytes() != BACKUP.read_bytes():
        shutil.copy2(BACKUP, CONFIG)
        reload_filter()
    else:
        print("Original EQ configuration is already in place; not restarting PipeWire.")
    if DEFAULT.is_file():
        old = DEFAULT.read_text().strip()
        if old:
            if not wait_for_sink(old):
                print("Original EQ configuration is restored, but the previous")
                print(f"default output ({old}) is not available yet.")
                print("Backup retained; do NOT start another audition.")
                print("Check: pactl list short sinks")
                print("Check: systemctl --user status wireplumber --no-pager")
                raise RuntimeError("Saved default audio sink is unavailable; backup preserved")
            run("pactl", "set-default-sink", old)
            print("Original default sink restored:", old)
    # Only remove the backup after the saved default has been restored.
    BACKUP.unlink()
    DEFAULT.unlink(missing_ok=True)
    try:
        STATE.rmdir()
    except OSError:
        pass
    print("Original EQ settings restored.")

def audition(voice=False):
    if BACKUP.exists():
        raise RuntimeError("Previous audition backup exists. Run --restore first; refusing to overwrite it.")
    if not CONFIG.is_file() or CONFIG.is_symlink():
        raise RuntimeError(f"Expected a regular PipeWire EQ config at {CONFIG}")
    variant = build_variant(CONFIG.read_text(), voice=voice)
    wait_for_audio()
    old_sink = run("pactl", "get-default-sink", capture=True).stdout.strip()
    current_sinks = run("pactl", "list", "short", "sinks", capture=True).stdout
    if EQ_SINK not in current_sinks or "MacBook_Speaker_Raw" not in current_sinks:
        raise RuntimeError("Expected MacBook8,1 EQ and raw sinks are missing")
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)
    shutil.copy2(CONFIG, BACKUP)
    DEFAULT.write_text(old_sink + "\n")
    print("Backing up original EQ. PipeWire will restart; this may interrupt audio.")
    try:
        CONFIG.write_text(variant)
        reload_filter()
        if EQ_SINK not in run("pactl", "list", "short", "sinks", capture=True).stdout:
            raise RuntimeError("EQ sink did not reappear after restart")
        print("\nAudio audition active: " + ("+4 dB at 185 Hz (voice)" if voice else "+2.5 dB at 258 Hz (warm)"))
        print("Both original high-pass speaker protection filters are unchanged.")
        print("Lower volume first to 25–35%. Compare a familiar spoken voice at matched loudness.")
        print("Enter e for modified EQ, r for original raw, q to quit and restore.")
        print("Do not edit the PipeWire configuration while the audition is active.")
        switch_output(EQ_SINK)
        while True:
            choice = input("Choose [e/r/q]: ").strip().lower()
            if choice == "e":
                switch_output(EQ_SINK)
            elif choice == "r":
                switch_output("MacBook_Speaker_Raw")
            elif choice in ("q", ""):
                break
            else:
                print("Please enter e, r or q.")
    finally:
        restore()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", action="store_true", help="Audition +4 dB at 185 Hz to give spoken voices more body")
    parser.add_argument("--restore", action="store_true",
                        help="Recover config from an interrupted earlier audition")
    args = parser.parse_args()
    ensure_environment()
    if args.restore:
        restore()
    else:
        audition(voice=args.voice)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted; restoration runs automatically where possible.")
        sys.exit(130)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        if BACKUP.is_file():
            print("If the filter is left modified, run: python3 scripts/try-warm-audio.py --restore",
                  file=sys.stderr)
        sys.exit(1)
