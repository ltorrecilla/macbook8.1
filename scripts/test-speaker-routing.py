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
# Retest at a known audible frequency and isolate the lower-frequency case.
# Use --bass-follow-up; the default 8-test sequence remains unchanged.
FOLLOWUP_TESTS = (
    ("FL alone, reference at 490 Hz", 490, (1, 0, 0, 0)),
    ("FL alone, bass at 230 Hz", 230, (1, 0, 0, 0)),
    ("FR alone, reference at 490 Hz", 490, (0, 1, 0, 0)),
    ("FR alone, bass at 230 Hz", 230, (0, 1, 0, 0)),
    ("LEFT FL+RL in phase at 490 Hz", 490, (1, 0, 1, 0)),
    ("LEFT FL+RL opposite phase at 490 Hz", 490, (1, 0, -1, 0)),
    ("RIGHT FR+RR in phase at 490 Hz", 490, (0, 1, 0, 1)),
    ("RIGHT FR+RR opposite phase at 490 Hz", 490, (0, 1, 0, -1)),
)

# Recheck the user's original silent paired 230 Hz tests against individual
# channels in the same session, at the same source amplitude.
BASS_PAIR_TESTS = (
    ("FL alone at 230 Hz", 230, (1, 0, 0, 0)),
    ("RL alone at 230 Hz", 230, (0, 0, 1, 0)),
    ("LEFT FL+RL in phase at 230 Hz", 230, (1, 0, 1, 0)),
    ("LEFT FL+RL opposite phase at 230 Hz", 230, (1, 0, -1, 0)),
    ("FR alone at 230 Hz", 230, (0, 1, 0, 0)),
    ("RR alone at 230 Hz", 230, (0, 0, 0, 1)),
    ("RIGHT FR+RR in phase at 230 Hz", 230, (0, 1, 0, 1)),
    ("RIGHT FR+RR opposite phase at 230 Hz", 230, (0, 1, 0, -1)),
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
    parser.add_argument("--bass-pairs-230", action="store_true",
                        help="Repeat individual and paired channels all at 230 Hz")
    parser.add_argument("--bass-follow-up", action="store_true",
                        help="At 490 Hz, compare phase; at 230 Hz, isolate single-channel audibility")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.bass_follow_up and args.bass_pairs_230:
        parser.error('Choose only one diagnostic mode')
    tests = BASS_PAIR_TESTS if args.bass_pairs_230 else (FOLLOWUP_TESTS if args.bass_follow_up else TESTS)
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
    if args.bass_pairs_230:
        print("Same-frequency follow-up: compare single and paired channels at 230 Hz.")
        print("Record audible, faint, or silent; note which phase pair sounds fuller.")
    if args.bass_follow_up:
        print("Follow-up: compare FL/FR at 490 vs 230 Hz, then paired channels at 490 Hz.")
        print("If 230 Hz remains silent, it may be attenuated by the speakers or audio path.")
    print("This does not change your default sink, PipeWire configuration, or driver.")
    print("Keep system volume modest. Stop if audio distorts or is uncomfortable.")
    ratings = []
    print("For each tone, note the physical side and whether it sounds full or thin.\n")
    with tempfile.TemporaryDirectory(prefix="mb81-audio-test-") as tmp:
        p = Path(tmp) / "test.raw"
        for i, (label, frequency, gains) in enumerate(tests, 1):
            cmd = ["pw-play", "--raw", "--rate=44100", "--format=s16", "--channels=4",
                   "--channel-map=FL,FR,RL,RR", f"--target={TARGET}", "--volume=0.35", str(p)]
            print(f"[{i}/{len(tests)}] {label} ({frequency} Hz)")
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
            if args.bass_pairs_230:
                rating = input("Heard [a=audible, f=faint, s=silent, q=quit]: ").strip().lower()
                if rating == "q":
                    break
                ratings.append((i, label, {"a":"audible", "f":"faint", "s":"silent"}.get(rating,"unspecified")))
            print()
    if args.bass_pairs_230:
        print("Results to share:")
        for i, label, rating in ratings:
            print(f"{i}. {label}: {rating}")
        print("Also say whether the in-phase or opposite-phase pair sounded fuller on each side.")
    elif args.bass_follow_up:
        print("Done. Report each test as audible / very faint / silent / playback error.")
    else:
        print("Done. Note whether each channel sounded and which phase pairing was fuller.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped. No configuration changes made.")
        sys.exit(130)
