#!/usr/bin/env python3
"""Temporary voice-warmth A/B audition targeting PipeWire nodes directly.

Requires a local audio file with speech and ffmpeg + pw-play. It does NOT change
the default sink or move browser/audio application streams. The old filter
configuration is backed up and restored, including after Ctrl-C.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

CONFIG = Path.home() / ".config/pipewire/pipewire.conf.d/51-macbook81-speaker.conf"
STATE = Path(os.getenv("XDG_STATE_HOME") or (Path.home() / ".local/state")) / "macbook81-audio-audition"
BACKUP = STATE / "original.conf"
DEFAULT = STATE / "original-sink.txt"
EQ_SINK = "input.MacBook_Speaker"
RAW_SINK = "MacBook_Speaker_Raw"


def run(*args, capture=False, check=True):
    return subprocess.run(args, text=True, capture_output=capture, check=check)


def ensure_environment():
    if os.geteuid() == 0:
        raise RuntimeError("Run as your normal desktop user, not with sudo")
    if not sys.stdin.isatty():
        raise RuntimeError("Run in an interactive terminal")
    if not all(shutil.which(p) for p in ("pactl", "systemctl")):
        raise RuntimeError("Missing pactl or systemctl")
    model = Path("/sys/class/dmi/id/product_name")
    if not model.is_file() or model.read_text().strip() != "MacBook8,1":
        raise RuntimeError("Only MacBook8,1 is supported")


def wait_for_audio():
    for _ in range(20):
        if run("pactl", "info", capture=True, check=False).returncode == 0:
            return
        time.sleep(0.5)
    raise RuntimeError("PipeWire audio server did not become ready")


def sink_available(name):
    result = run("pactl", "list", "short", "sinks", capture=True, check=False)
    return result.returncode == 0 and any(
        len(fields := line.split()) > 1 and fields[1] == name
        for line in result.stdout.splitlines()
    )


def wait_for_sink(name, seconds=15):
    for _ in range(max(1, int(seconds * 2))):
        if sink_available(name):
            return True
        time.sleep(0.5)
    return sink_available(name)


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
        updated, count = re.subn(
            pattern, lambda m: m.group(1) + ("4.0" if voice else "2.5"), updated)
        if count != 1:
            raise RuntimeError(f"Expected one untouched {name} EQ filter; found {count}.")
        if voice:
            frequency = (r'(\bname\s*=\s*' + re.escape(name) +
                         r'\s+label\s*=\s*bq_peaking\s+control\s*=\s*\{\s*"Freq"\s*=\s*)258\.0')
            updated, fcount = re.subn(
                frequency, lambda m: m.group(1) + "185.0", updated)
            if fcount != 1:
                raise RuntimeError(f"Cannot retune {name} to 185 Hz.")
    return updated


def restore():
    if not BACKUP.is_file():
        print("No previous audition backup found; nothing to restore.")
        return
    print("Restoring original PipeWire EQ configuration...")
    if not CONFIG.is_file() or CONFIG.read_bytes() != BACKUP.read_bytes():
        shutil.copy2(BACKUP, CONFIG)
        reload_filter()
    else:
        print("Original EQ configuration is already in place; not restarting PipeWire.")
    if DEFAULT.is_file():
        old = DEFAULT.read_text().strip()
        if old:
            # The current experiment never changes the default sink.
            # Older versions did, so restore it only when actually changed.
            current = run("pactl", "get-default-sink", capture=True, check=False)
            if current.returncode != 0 or current.stdout.strip() != old:
                if not wait_for_sink(old):
                    print(f"Saved default output {old} is unavailable; backup retained.")
                    raise RuntimeError("Cannot restore previous default sink yet")
                run("pactl", "set-default-sink", old)
                print("Original default sink restored:", old)
            else:
                print("Original default sink already selected:", old)
    BACKUP.unlink()
    DEFAULT.unlink(missing_ok=True)
    try:
        STATE.rmdir()
    except OSError:
        pass
    print("Original EQ settings restored.")


def prepare_samples(source, temp_dir):
    if not shutil.which("ffmpeg") or not shutil.which("pw-play"):
        raise RuntimeError("Install ffmpeg and PipeWire pw-play before starting")
    file = Path(source).expanduser().resolve()
    if not file.is_file():
        raise RuntimeError(f"Not a local audio file: {file}")
    stereo = Path(temp_dir) / "speech-stereo.wav"
    quad = Path(temp_dir) / "speech-four-channel.raw"
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-i", str(file), "-map", "0:a:0", "-t", "12", "-vn",
        "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(stereo))
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-i", str(stereo),
        "-af", "pan=4c|c0=c0|c1=c1|c2=c0|c3=c1",
        "-ar", "44100", "-f", "s16le", str(quad))
    if stereo.stat().st_size < 1000 or quad.stat().st_size < 1000:
        raise RuntimeError("Audio excerpt was too short or empty")
    return stereo, quad


def play_sample(mode, stereo, quad):
    if mode == "e":
        target = EQ_SINK
        command = ("pw-play", "--target=" + target, "--volume=0.25", str(stereo))
    else:
        target = RAW_SINK
        command = ("pw-play", "--raw", "--rate=44100", "--format=s16",
                   "--channels=4", "--channel-map=FL,FR,RL,RR",
                   "--target=" + target, "--volume=0.25", str(quad))
    if not wait_for_sink(target, seconds=5):
        raise RuntimeError(f"PipeWire playback node missing: {target}")
    print(f"Playing 12-second excerpt directly to {target}.")
    run(*command)


def audition(source, voice=False):
    if BACKUP.exists():
        raise RuntimeError("Previous audition backup exists; run --restore first.")
    if not CONFIG.is_file() or CONFIG.is_symlink():
        raise RuntimeError(f"Expected a regular EQ file at {CONFIG}")
    variant = build_variant(CONFIG.read_text(), voice=voice)
    wait_for_audio()
    old = run("pactl", "get-default-sink", capture=True).stdout.strip()
    if not (sink_available(EQ_SINK) and sink_available(RAW_SINK)):
        raise RuntimeError("Required EQ and raw nodes are not both present")
    with tempfile.TemporaryDirectory(prefix="mb81-voice-ab-") as temp_dir:
        stereo, quad = prepare_samples(source, temp_dir)
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(STATE, 0o700)
        shutil.copy2(CONFIG, BACKUP)
        DEFAULT.write_text(old + "\n")
        print("Config backed up; restarting PipeWire briefly.")
        try:
            CONFIG.write_text(variant)
            reload_filter()
            if not wait_for_sink(EQ_SINK):
                raise RuntimeError("EQ node did not reappear after restart")
            print("\nA/B audition using a 12-second sample, without changing default output.")
            print("EQ: " + ("+4 dB at 185 Hz" if voice else "+2.5 dB at 258 Hz"))
            print("High-pass protection unchanged. Start with low system volume.")
            print("Press e to hear EQ, r to hear RAW, q to quit and restore.")
            while True:
                option = input("Choose [e/r/q]: ").strip().lower()
                if option in ("q", ""):
                    break
                if option in ("e", "r"):
                    play_sample(option, stereo, quad)
                else:
                    print("Enter e, r, or q.")
        finally:
            restore()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", action="store_true",
                        help="Test voice body: +4 dB at 185 Hz")
    parser.add_argument("--file", type=str,
                        help="Path to local speech/audio file (mp3, flac, wav, etc.)")
    parser.add_argument("--restore", action="store_true",
                        help="Restore from an interrupted or older audition")
    args = parser.parse_args()
    ensure_environment()
    if args.restore:
        restore()
    else:
        if not args.file:
            parser.error("Specify --file /path/to/speech.mp3 (no settings were changed)")
        audition(args.file, voice=args.voice)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Backups are restored automatically when possible.")
        sys.exit(130)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        if BACKUP.is_file():
            print("If needed, run: python3 scripts/try-warm-audio.py --restore",
                  file=sys.stderr)
        sys.exit(1)
