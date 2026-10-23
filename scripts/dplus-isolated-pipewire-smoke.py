#!/usr/bin/env python3
"""Opt-in hardware-disconnected PipeWire bq_raw startup smoke test.

Starts a disposable PipeWire daemon using its own config and UNIX socket.
No session manager, ALSA device, playback, default changes, or service restart.
Checks that two stereo unity-biquad filter nodes appear, then stops that child.
Does not validate D+ v4 coefficients or limiter.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

SOCKET = "dplus-test-0"
CAPTURE = "dplus_isolated_capture"
PLAYBACK = "dplus_isolated_output"

def config_text() -> str:
    return """# Disposable D+ smoke test: NO hardware/session-manager modules
context.properties = {
    core.daemon = true
    core.name = dplus-test-0
    default.clock.rate = 48000
    default.clock.allowed-rates = [ 48000 ]
    default.clock.quantum = 1024
}
context.spa-libs = {
    support.* = support/libspa-support
    audio.convert.* = audioconvert/libspa-audioconvert
}
context.modules = [
    { name = libpipewire-module-protocol-native }
    { name = libpipewire-module-client-node }
    { name = libpipewire-module-adapter }
    { name = libpipewire-module-filter-chain
      args = {
        node.description = "D+ isolated unity biquad smoke test"
        filter.graph = {
          nodes = [
            { type = builtin name = left_unity label = bq_raw
              config = { coefficients = [ { rate = 48000 b0 = 1 b1 = 0 b2 = 0 a0 = 1 a1 = 0 a2 = 0 } ] }
            }
            { type = builtin name = right_unity label = bq_raw
              config = { coefficients = [ { rate = 48000 b0 = 1 b1 = 0 b2 = 0 a0 = 1 a1 = 0 a2 = 0 } ] }
            }
          ]
          inputs = [ "left_unity:In" "right_unity:In" ]
          outputs = [ "left_unity:Out" "right_unity:Out" ]
        }
        capture.props = {
          node.name = dplus_isolated_capture
          node.description = "D+ isolated input (not hardware)"
          media.class = Audio/Sink
          node.passive = true
          audio.channels = 2
          audio.position = [ FL FR ]
        }
        playback.props = {
          node.name = dplus_isolated_output
          node.description = "D+ isolated output (no hardware target)"
          node.passive = true
          node.dont-fallback = true
          node.dont-reconnect = true
          audio.channels = 2
          audio.position = [ FL FR ]
        }
      }
    }
]
"""

def scan_objects(objects):
    nodes = {o.get("info", {}).get("props", {}).get("node.name") for o in objects
             if isinstance(o, dict) and o.get("type") == "PipeWire:Interface:Node"
             and isinstance(o.get("info"), dict)}
    return CAPTURE in nodes and PLAYBACK in nodes, nodes

def safe_env(root):
    env = os.environ.copy()
    env.update({
        "PIPEWIRE_RUNTIME_DIR": str(root / "runtime"),
        "PIPEWIRE_CONFIG_DIR": str(root / "config"),
        "PIPEWIRE_REMOTE": SOCKET,
        "PIPEWIRE_CORE": SOCKET,
        "PIPEWIRE_DAEMON": "true",
        "XDG_CONFIG_HOME": str(root / "config"),
    })
    return env

def client_env(daemon_env):
    env = daemon_env.copy()
    for key in ("PIPEWIRE_DAEMON", "PIPEWIRE_CORE", "PIPEWIRE_CONFIG_DIR"):
        env.pop(key, None)
    env["PIPEWIRE_NO_CONFIG"] = "true"
    return env

def run_smoke(inspect_only=False):
    if os.geteuid() == 0:
        raise RuntimeError("Run as ordinary user, not sudo/root")
    for program in ("pipewire", "pw-dump"):
        if not shutil.which(program):
            raise RuntimeError("Missing executable: " + program)
    with tempfile.TemporaryDirectory(prefix="dplus-pw-isolated-") as folder:
        root = Path(folder)
        runtime, config = root / "runtime", root / "config"
        runtime.mkdir(mode=0o700)
        config.mkdir(mode=0o700)
        (config / "dplus-isolated.conf").write_text(config_text(), encoding="utf-8")
        if inspect_only:
            print("No PipeWire process started. Generated configuration:")
            print(config_text())
            return 0
        env = safe_env(root)
        logfile = root / "pipewire.log"
        with logfile.open("wb") as log:
            daemon = None
            try:
                daemon = subprocess.Popen(["pipewire", "-c", "dplus-isolated.conf"],
                                          env=env, stdin=subprocess.DEVNULL,
                                          stdout=log, stderr=subprocess.STDOUT,
                                          start_new_session=True)
                deadline = time.monotonic() + 8
                last_error = ""
                while time.monotonic() < deadline:
                    if daemon.poll() is not None:
                        break
                    try:
                        check = subprocess.run(["pw-dump"], env=client_env(env),
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE,
                                               text=True, timeout=2, check=False)
                        if check.returncode == 0:
                            ok, nodes = scan_objects(json.loads(check.stdout))
                            if ok:
                                print("PASS: isolated 48-kHz PipeWire bq_raw stereo graph initialized.")
                                print("Nodes:", CAPTURE, PLAYBACK)
                                print("Private socket:", runtime / SOCKET)
                                print("No speaker, ALSA, PipeWire-Pulse or service changes.")
                                return 0
                            last_error = "Expected nodes missing; found " + repr(sorted(str(n) for n in nodes))
                        else:
                            last_error = check.stderr.strip()[-350:]
                    except (json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
                        last_error = str(exc)
                    time.sleep(0.25)
                log.flush()
                tail = logfile.read_text(encoding="utf-8", errors="replace")[-1800:]
                raise RuntimeError("Isolated graph unavailable: " + last_error
                                   + "\nPrivate daemon log:\n" + tail)
            finally:
                if daemon is not None and daemon.poll() is None:
                    try:
                        daemon.send_signal(signal.SIGTERM)
                        daemon.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        daemon.kill()
                        daemon.wait(timeout=2)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-config", action="store_true",
                        help="Print isolated configuration without launching a process")
    args = parser.parse_args(argv)
    try:
        return run_smoke(args.show_config)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
