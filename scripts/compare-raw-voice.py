#!/usr/bin/env python3
"""A/B compare original vs voice-warmed playback on MacBook_Speaker_Raw.

Creates temporary 4-channel samples from the same local speech/music excerpt.
No system or PipeWire configuration changes. Requires ffmpeg and pw-play.
"""
import argparse
from array import array
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

SINK = "MacBook_Speaker_Raw"
RATE = 44100
SECONDS = 12


def command(*args, capture=False):
    return subprocess.run(args, check=True, capture_output=capture, text=True)


def generate_stereo(source, dest, start):
    command("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-ss", str(start), "-i", str(source), "-map", "0:a:0",
            "-t", str(SECONDS), "-vn", "-ar", str(RATE), "-ac", "2",
            "-c:a", "pcm_s16le", str(dest))
    if dest.stat().st_size < 2048:
        raise RuntimeError("Audio excerpt is too short or empty")


def generate_raw(stereo, dest, warm):
    # Identical 6dB headroom and channel duplication for both samples.
    eq = ("equalizer=f=210:t=q:w=1.0:g=3.5,"
          "equalizer=f=3000:t=q:w=1.4:g=-1.5,") if warm else ""
    filters = eq + "volume=-6dB,pan=4c|c0=c0|c1=c1|c2=c0|c3=c1"
    command("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-i", str(stereo), "-map", "0:a:0", "-vn", "-af", filters,
            "-ar", str(RATE), "-c:a", "pcm_s16le", "-f", "s16le", str(dest))
    if dest.stat().st_size < 2048 or dest.stat().st_size % 8 != 0:
        raise RuntimeError("Generated PCM file is empty or not four-channel S16")


def rms(samples):
    return math.sqrt(sum(float(x) * x for x in samples) / max(1, len(samples)))


def match_rms(baseline, modified):
    """Match overall digital RMS, retaining headroom (not perceived loudness)."""
    reference = array("h")
    reference.frombytes(baseline.read_bytes())
    samples = array("h")
    samples.frombytes(modified.read_bytes())
    if sys.byteorder != "little":
        reference.byteswap()
        samples.byteswap()
    target = rms(reference)
    current = rms(samples)
    if target < 1 or current < 1:
        raise RuntimeError("Excerpt is mostly silence; choose another speech section")
    factor = min(target / current, (32767 * 0.7) / max(1, max(abs(v) for v in samples)))
    for i in range(len(samples)):
        samples[i] = round(samples[i] * factor)
    if sys.byteorder != "little":
        samples.byteswap()
    modified.write_bytes(samples.tobytes())
    return target, rms(array("h", modified.read_bytes())), factor


def prepare_audio(source, temp, start):
    stereo = temp / "speech.wav"
    raw = temp / "raw-unchanged.pcm"
    warm = temp / "voice-warm.pcm"
    generate_stereo(source, stereo, start)
    generate_raw(stereo, raw, False)
    generate_raw(stereo, warm, True)
    before, after, factor = match_rms(raw, warm)
    return raw, warm, before, after, factor


def self_test():
    with tempfile.TemporaryDirectory(prefix="mb81-voice-selftest-") as root:
        folder = Path(root)
        example = folder / "speech-test.wav"
        with wave.open(str(example), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(RATE)
            for i in range(RATE):
                x = (0.22 * math.sin(2 * math.pi * 210 * i / RATE)
                     + 0.10 * math.sin(2 * math.pi * 3000 * i / RATE))
                val = int(32767 * x)
                w.writeframesraw(struct.pack("<hh", val, val))
        raw, warm, original, modified, factor = prepare_audio(example, folder, 0.0)
        assert raw.stat().st_size == warm.stat().st_size
        assert raw.read_bytes() != warm.read_bytes()
        assert abs(original - modified) / original < 0.02
        print(f"PASS: four-channel PCM layout and RMS matching (factor {factor:.3f}).")
    return 0


def audition(source, start):
    if os.geteuid() == 0:
        raise RuntimeError("Run as your regular desktop user, not sudo")
    if not sys.stdin.isatty():
        raise RuntimeError("Use an interactive terminal")
    model = Path("/sys/class/dmi/id/product_name")
    if not model.is_file() or model.read_text().strip() != "MacBook8,1":
        raise RuntimeError("This test is designed for MacBook8,1 only")
    if not shutil.which("pw-play"):
        raise RuntimeError("pw-play was not found")
    sinks = command("pactl", "list", "short", "sinks", capture=True).stdout
    if not any(len(fields := line.split()) > 1 and fields[1] == SINK
               for line in sinks.splitlines()):
        raise RuntimeError(f"Expected sink {SINK} is unavailable")
    if not source.is_file():
        raise RuntimeError(f"Audio file not found: {source}")
    with tempfile.TemporaryDirectory(prefix="mb81-voice-compare-") as root:
        raw, warm, original, modified, factor = prepare_audio(source, Path(root), start)
        print("\nA/B voice test: BOTH samples go to MacBook_Speaker_Raw.")
        print("B: +3.5 dB at 210 Hz, -1.5 dB at 3 kHz, with headroom.")
        print("Digital RMS roughly matched; perceived loudness may differ.")
        print("Use modest volume. Stop if playback distorts.")
        while True:
            option = input("Play [a] original, [b] fuller voices, or [q] exit: ").strip().lower()
            if option in ("q", ""):
                break
            if option not in ("a", "b"):
                print("Choose a, b or q")
                continue
            chosen = raw if option == "a" else warm
            command("pw-play", "--raw", "--rate=44100", "--format=s16",
                    "--channels=4", "--channel-map=FL,FR,RL,RR",
                    f"--target={SINK}", "--volume=0.25", str(chosen))
            print("Completed", option.upper())
        print("Finished; no audio configuration changes made.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", help="Local music or speech file (MP3, WAV, FLAC etc.)")
    parser.add_argument("--start", type=float, default=0, help="Start time in seconds")
    parser.add_argument("--self-test", action="store_true", help="Test generation without speakers")
    args = parser.parse_args()
    try:
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg must be installed")
        if args.self_test:
            return self_test()
        if not args.file or not math.isfinite(args.start) or args.start < 0:
            parser.error("Provide --file /path/to/speech.mp3 and a nonnegative --start")
        audition(Path(args.file).expanduser().resolve(), args.start)
        return 0
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print("ERROR:", error, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped; no audio settings changed.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
