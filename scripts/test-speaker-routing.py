#!/usr/bin/env python3
"""Read-only MacBook8,1 TDM speaker test, using low-volume four-channel PCM.

No root access, no audio configuration changes. Requires PipeWire's pw-play.
"""
import argparse
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

RATE = 44_100
TARGET = "MacBook_Speaker_Raw"
TESTS = (
    ("FL only — note where sound comes from", 490, (1, 0, 0, 0)),
    ("FR only — note where sound comes from", 490, (0, 1, 0, 0)),
    ("RL only — note where sound comes from", 490, (0, 0, 1, 0)),
    ("RR only — note where sound comes from", 490, (0, 0, 0, 1)),
    ("LEFT pair FL+RL in phase — compare fullness", 230, (1, 0, 1, 0)),
    ("LEFT pair FL+RL opposite phase — compare fullness", 230, (1, 0, -1, 0)),
    ("RIGHT pair FR+RR in phase — compare fullness", 230, (0, 1, 0, 1)),
    ("RIGHT pair FR+RR opposite phase — compare fullness", 230, (0, 1, 0, -1)),
)


def write_raw_pcm(path: Path, frequency: int, gains: tuple[int, int, int, int], seconds=1.3) -> None:
    """Four-channel signed 16-bit PCM at 44.1 kHz; ~-20 dBFS peak per channel."""
    frames = int(RATE * seconds)
    fade_samples = int(RATE * 0.035)
    pack = struct.Struct("<hhhh").pack
    with path.open("wb") as f:
        for index in range(frames):
            envelope = min(1.0, index / fade_samples, (frames - 1 - index) / fade_samples)
            sample = int(32767 * 0.1 * max(0.0, envelope) * math.sin(2 * math.pi * frequency * index / RATE))
            f.write(pack(*(sample * gain for gain in gains)))


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="mb81-audio-test-") as tmp:
        p = Path(tmp) / "test.raw"
        write_raw_pcm(p, 490, (1, 0, 0, 0), seconds=0.06)
        data = p.read_bytes()
        assert len(data) == int(RATE * 0.06) * 8
        for fl, fr, rl, rr in struct.iter_unpack("<hhhh", data):
            assert fr == rl == rr == 0
            assert abs(fl) <= 3277
        write_raw_pcm(p, 230, (1, 0, -1, 0), seconds=0.06)
        for fl, fr, rl, rr in struct.iter_unpack("<hhhh", p.read_bytes()):
            assert fr == rr == 0 and rl == -fl
    print("PASS: four-channel PCM layout and phase-inversion tests")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Check sample layout without playing audio")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if os.geteuid() == 0:
        parser.error("Run as your normal desktop user, not with sudo")
    if not sys.stdin.isatty():
        parser.error("Requires an interactive terminal; no audio has been played")
    if not shutil.which("pw-play"):
        parser.error("pw-play was not found; check your PipeWire installation")
    if shutil.which("pactl"):
        probe = subprocess.run(["pactl", "list", "short", "sinks"], capture_output=True, text=True)
        if probe.returncode or TARGET not in probe.stdout:
            parser.error(f"Could not find sink {TARGET}; current audio setup may differ")
    print("\nMacBook8,1 speaker routing check (8 quiet tests)")
    print("This does not change your default sink, PipeWire configuration, or driver.")
    print("Keep system volume modest. Stop if audio distorts or is uncomfortable.")
    print("For each tone, note the physical side and whether it sounds full or thin.\n")
    with tempfile.TemporaryDirectory(prefix="mb81-audio-test-") as tmp:
        p = Path(tmp) / "test.raw"
        for i, (label, frequency, gains) in enumerate(TESTS, 1):
            cmd = ["pw-play", "--raw", "--rate=44100", "--format=s16", "--channels=4",
                   "--channel-map=FL,FR,RL,RR", f"--target={TARGET}", "--volume=0.35", str(p)]
            print(f"[{i}/{len(TESTS)}] {label} ({frequency} Hz)")
            answer = input("Press Enter to play, or type q then Enter to stop: ").strip().lower()
            if answer in ("q", "quit", "exit"):
                print("Stopped. No configuration changes made.")
                break
            write_raw_pcm(p, frequency, gains)
            try:
                subprocess.run(cmd, check=True)
            except (subprocess.CalledProcessError, OSError) as exc:
                print(f"Playback failed: {exc}", file=sys.stderr)
                return 1
            print()
    print("Done. Note whether each channel sounded and which phase pairing was fuller.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped. No configuration changes made.")
        sys.exit(130)
