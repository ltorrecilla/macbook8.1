#!/usr/bin/env python3
"""Bounded, fail-closed supervisor for the exact graph installed by manage-native.py.

Does not alter the global default or restart system audio. Does not promise
reconnection after suspend: stop safely, then diagnose before enabling startup.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

RAW = "MacBook_Speaker_Raw"
SINK = "MacBook_Speaker_D_Preview"
MANAGED = Path.home() / ".config" / "macbook81-dplus-native"
STOP = False


def handle_signal(_signal, _frame):
    global STOP
    STOP = True


def run_command(*argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True,
                          timeout=5).stdout.strip()


def outputs():
    return {line.split()[1] for line in run_command("pactl", "list", "short", "sinks").splitlines()
            if len(line.split()) > 1}


def default():
    return run_command("pactl", "get-default-sink")


def sink_visible(names):
    return SINK in names or "input." + SINK in names


def guard_before_start():
    if os.geteuid() == 0:
        raise RuntimeError("Never run this user service as root")
    if not (MANAGED / "dplus.conf").is_file():
        raise RuntimeError("Generated D+ config missing. Run manage-native.py install")
    current = outputs()
    if RAW not in current:
        raise RuntimeError("Raw is unavailable; refusing to start D+")
    if default() != RAW:
        raise RuntimeError("Raw must be the global default before starting opt-in D+")
    if sink_visible(current):
        raise RuntimeError("D+ preview already exists; refusing duplicate output")
    try:
        status = subprocess.run(["systemctl", "--user", "is-active", "--quiet",
                                 "macbook81-dplus.service"], timeout=5)
        if status.returncode == 0:
            raise RuntimeError("Obsolete FFmpeg D+ service is active; stop it first")
    except FileNotFoundError:
        pass


def run():
    guard_before_start()
    if any(os.environ.get(name) for name in ("PIPEWIRE_CONFIG_DIR", "PIPEWIRE_REMOTE", "PIPEWIRE_RUNTIME_DIR")):
        raise RuntimeError("Inherited PipeWire override detected; refusing")
    env = os.environ.copy()
    env["PIPEWIRE_CONFIG_DIR"] = str(MANAGED)
    env["PIPEWIRE_REMOTE"] = "pipewire-0"
    env.pop("PIPEWIRE_DAEMON", None)
    env.pop("PIPEWIRE_CORE", None)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    proc = subprocess.Popen(["pipewire", "-c", "dplus.conf"], env=env,
                            stdin=subprocess.DEVNULL, start_new_session=True)
    try:
        # A registered virtual sink is NOT evidence of DSP PCM activation.
        start_deadline = time.monotonic() + 12.0
        ready = False
        while not STOP and time.monotonic() < start_deadline:
            if proc.poll() is not None:
                raise RuntimeError("PipeWire D+ client exited on startup")
            names = outputs()
            if default() != RAW:
                raise RuntimeError("Default changed from Raw; stopping experimental D+")
            if RAW not in names:
                raise RuntimeError("Raw disappeared; stopping experimental D+")
            if sink_visible(names):
                ready = True
                break
            time.sleep(0.3)
        if not ready and not STOP:
            raise RuntimeError("D+ output not registered within 12 seconds")
        if ready:
            print("D+ sink registered (audio MUST be tested separately); Raw remains default", flush=True)
        while not STOP:
            if proc.poll() is not None:
                raise RuntimeError("PipeWire D+ child exited")
            names = outputs()
            if default() != RAW:
                raise RuntimeError("Default changed away from Raw; stopping, no changes made")
            if RAW not in names or not sink_visible(names):
                raise RuntimeError("Raw/D+ disappeared; stopping (no unsafe reconnection)")
            time.sleep(1)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        print("Stopped only the managed D+ client; system default not modified", flush=True)


def main():
    try:
        run()
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"D+ stopped safely: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
