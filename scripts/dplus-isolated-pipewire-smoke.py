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

def config_text(include_filter=True, active_probe=False) -> str:
    config = """# Disposable D+ smoke test: NO hardware/session-manager modules
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
    # Metadata protocol/factory support is required for pw-dump binding.
    # Limited to this generated disposable server configuration.
    { name = libpipewire-module-metadata }
    # Both sockets belong to this disposable test-only PipeWire server.
    # The manager probe uses -manager; the filter-chain streams use the base.
    # Neither socket nor this permission map exists in the production daemon.
    { name = libpipewire-module-access
      args = {
        access.socket = {
          dplus-test-0 = "unrestricted"
          dplus-test-0-manager = "unrestricted"
        }
      }
    }
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
    if active_probe:
        if not include_filter or config.count("          node.passive = true") != 2:
            raise ValueError("Invalid isolated active-probe configuration")
        # This is exclusively for a new disposable server. Without a session
        # manager or hardware target, ask the two filter streams to run.
        config = config.replace(
            "          node.passive = true",
            "          node.passive = false\n"
            "          node.always-process = true\n"
            "          node.autoconnect = false"
        )
    if include_filter:
        return config
    before, marker, _ = config.partition("    { name = libpipewire-module-filter-chain")
    if not marker:
        raise RuntimeError("Private graph configuration unexpectedly missing")
    return before + "]\n"


def scan_objects(objects):
    nodes = {o.get("info", {}).get("props", {}).get("node.name") for o in objects
             if isinstance(o, dict) and o.get("type") == "PipeWire:Interface:Node"
             and isinstance(o.get("info"), dict)}
    return CAPTURE in nodes and PLAYBACK in nodes, nodes

def inventory_summary(objects):
    """Only summarize object types/names from our private test server."""
    from collections import Counter
    kinds = Counter(str(obj.get("type", "?")) for obj in objects if isinstance(obj, dict))
    names = []
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        info = obj.get("info")
        if not isinstance(info, dict):
            continue
        props = info.get("props")
        if not isinstance(props, dict):
            continue
        name = props.get("node.name")
        if name is not None:
            names.append(str(name))
    return {"object_types": dict(sorted(kinds.items())),
            "advertised_node_names": sorted(names)[:15]}


def private_filter_ports(objects):
    """Inventory only ports belonging to the disposable test filter streams."""
    node_names = {}
    for obj in objects:
        if not isinstance(obj, dict) or obj.get("type") != "PipeWire:Interface:Node":
            continue
        info = obj.get("info")
        props = info.get("props") if isinstance(info, dict) else None
        if isinstance(props, dict) and props.get("node.name") in (CAPTURE, PLAYBACK):
            node_names[str(obj.get("id"))] = props["node.name"]
    ports = []
    for obj in objects:
        if not isinstance(obj, dict) or obj.get("type") != "PipeWire:Interface:Port":
            continue
        info = obj.get("info")
        props = info.get("props") if isinstance(info, dict) else None
        if not isinstance(props, dict):
            continue
        owner = node_names.get(str(props.get("node.id")))
        if owner is None:
            continue
        ports.append({
            "node": owner,
            "port": str(props.get("port.name", "?")),
            "direction": str(info.get("direction", props.get("port.direction", "?"))),
            "channel": str(props.get("audio.channel", "?")),
        })
    return sorted(ports, key=lambda x: (x["node"], x["port"]))


def private_graph_summary(objects):
    """Report bounded structural details from this disposable PipeWire registry.

    Include unassociated ports as well: a missing node.id relation must not
    be misreported as evidence that the server published zero port objects.
    """
    targets = {CAPTURE, PLAYBACK}
    nodes = []
    ports = []
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        kind = obj.get("type")
        info = obj.get("info")
        info = info if isinstance(info, dict) else {}
        props = info.get("props")
        props = props if isinstance(props, dict) else {}
        if kind == "PipeWire:Interface:Node" and props.get("node.name") in targets:
            nodes.append({
                "id": obj.get("id"),
                "name": props.get("node.name"),
                "state": info.get("state", "not reported"),
                "n_input_ports": info.get("n_input_ports", "not reported"),
                "n_output_ports": info.get("n_output_ports", "not reported"),
                "audio_channels": props.get("audio.channels", "not reported"),
                "media_class": props.get("media.class", "not reported"),
                "passive": props.get("node.passive", "not reported"),
            })
        if kind == "PipeWire:Interface:Port":
            ports.append({
                "id": obj.get("id"),
                "node.id": props.get("node.id", "not reported"),
                "port.name": props.get("port.name", "not reported"),
                "direction": info.get("direction", props.get("port.direction", "not reported")),
                "audio.channel": props.get("audio.channel", "not reported"),
            })
    return {
        "test_nodes": sorted(nodes, key=lambda row: str(row["name"])),
        "total_published_port_objects": len(ports),
        "published_port_sample": ports[:12],
        "matched_filter_port_count": len(private_filter_ports(objects)),
    }


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
    # Exclude inherited client/config overrides that could change the private test.
    for key in ("PIPEWIRE_NO_CONFIG", "PIPEWIRE_CONFIG_NAME", "PIPEWIRE_CONFIG_PREFIX"):
        env.pop(key, None)
    env["PIPEWIRE_LOG_SYSTEMD"] = "false"
    env["PIPEWIRE_DEBUG"] = "3"
    return env

def client_env(daemon_env):
    env = daemon_env.copy()
    for key in ("PIPEWIRE_DAEMON", "PIPEWIRE_CORE", "PIPEWIRE_CONFIG_DIR"):
        env.pop(key, None)
    # Keep the normal packaged client.conf so protocol-native can initialize.
    env.pop("PIPEWIRE_NO_CONFIG", None)
    return env

def private_phase(root, name, with_filter, active_probe=False):
    """Probe exactly one private daemon, returning success only after a JSON reply."""
    import stat

    directory = root / name
    runtime = directory / "runtime"
    config = directory / "config"
    runtime.mkdir(parents=True, mode=0o700)
    config.mkdir(mode=0o700)
    (config / "dplus-isolated.conf").write_text(
        config_text(with_filter, active_probe), encoding="utf-8")
    env = safe_env(directory)
    # pw-dump connects with the manager intention; the private
    # CORENAME-manager socket gets explicit, socket-scoped permissions.
    socket_path = runtime / (SOCKET + "-manager")
    logfile = directory / "pipewire.log"
    daemon = None
    last_error = "not yet connected"
    with logfile.open("wb") as log:
        try:
            daemon = subprocess.Popen(
                ["pipewire", "-c", "dplus-isolated.conf"], env=env,
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)
            # Wait for the private MANAGER socket BEFORE launching pw-dump. Otherwise
            # the client can block on a missing listener and mask startup errors.
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                if daemon.poll() is not None:
                    last_error = "private server exited with status " + str(daemon.returncode)
                    break
                try:
                    if stat.S_ISSOCK(socket_path.stat().st_mode):
                        break
                except FileNotFoundError:
                    pass
                time.sleep(0.15)
            else:
                last_error = "private socket never appeared"

            if not socket_path.is_socket():
                raise RuntimeError(last_error)

            # -r explicitly selects our socket, and PIPEWIRE_RUNTIME_DIR points
            # at the private location; no production server is contacted.
            deadline = time.monotonic() + (5 if active_probe else 9)
            while time.monotonic() < deadline:
                if daemon.poll() is not None:
                    last_error = "private server exited with status " + str(daemon.returncode)
                    break
                try:
                    probe = subprocess.run(
                        ["pw-dump", "--remote=" + SOCKET, "--no-colors"],
                        env=client_env(env), capture_output=True,
                        text=True, timeout=4, check=False)
                    if probe.returncode:
                        last_error = "client exit " + str(probe.returncode) + ": " + probe.stderr[-400:]
                    else:
                        objects = json.loads(probe.stdout)
                        if not isinstance(objects, list):
                            last_error = "client returned non-list JSON"
                        elif not with_filter:
                            return True
                        else:
                            ok, nodes = scan_objects(objects)
                            if ok:
                                if active_probe and private_graph_summary(objects)["total_published_port_objects"] == 0:
                                    last_error = (
                                        "active private graph has both nodes but still zero Port objects; "
                                        "states = " +
                                        json.dumps(private_graph_summary(objects)["test_nodes"])[:800]
                                    )
                                    time.sleep(0.25)
                                    continue
                                if with_filter:
                                    print("Private registry structure:", flush=True)
                                    print(json.dumps(private_graph_summary(objects), indent=2),
                                          flush=True)
                                    ports = private_filter_ports(objects)
                                    print("Private filter-chain port inventory:", flush=True)
                                    if ports:
                                        for port in ports:
                                            print("  " + port["node"] + " : " + port["port"]
                                                  + " [" + port["direction"] + ", "
                                                  + port["channel"] + "]", flush=True)
                                    else:
                                        print("  No port objects published in this snapshot.", flush=True)
                                return True
                            last_error = (
                                "connected but expected filter nodes absent: "
                                + json.dumps(inventory_summary(objects), sort_keys=True)[:1000]
                            )
                except subprocess.TimeoutExpired as exc:
                    stderr = exc.stderr or b""
                    if isinstance(stderr, bytes):
                        stderr = stderr.decode("utf-8", "replace")
                    last_error = "private client timed out: " + str(stderr)[-300:]
                except json.JSONDecodeError as exc:
                    last_error = "unreadable private client JSON: " + str(exc)
                time.sleep(0.25)
            raise RuntimeError(last_error)
        except RuntimeError as exc:
            log.flush()
            contents = logfile.read_text(encoding="utf-8", errors="replace")
            errors = [line for line in contents.splitlines()
                      if "[E]" in line or "filter-chain" in line.lower()
                      or "metadata" in line.lower()]
            diagnostic = "\n".join(errors[-14:])[-2400:]
            tail = contents[-1800:]
            raise RuntimeError(
                f"{name} phase failed: {exc}\n"
                f"private socket present={socket_path.is_socket()}; "
                f"private daemon alive={daemon is not None and daemon.poll() is None}\n"
                f"Relevant private log messages:\n{diagnostic or '(none)'}\n"
                f"Private daemon log tail:\n{tail or '(empty)'}") from exc
        finally:
            if daemon is not None and daemon.poll() is None:
                try:
                    daemon.send_signal(signal.SIGTERM)
                    daemon.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    daemon.kill()
                    daemon.wait(timeout=2)


def run_smoke(inspect_only=False, probe_activation=False):
    if os.geteuid() == 0:
        raise RuntimeError("Run as ordinary user, not sudo/root")
    for program in ("pipewire", "pw-dump"):
        if not shutil.which(program):
            raise RuntimeError("Missing executable: " + program)
    if inspect_only:
        print("No PipeWire process started. Generated configuration:")
        print(config_text())
        return 0
    with tempfile.TemporaryDirectory(prefix="dplus-pw-isolated-") as folder:
        root = Path(folder)
        print("Stage 1/2: testing the private native-protocol socket (no filters).", flush=True)
        private_phase(root, "core", with_filter=False)
        print("PASS: private PipeWire server and client handshake.", flush=True)
        print("Stage 2/2: checking private bq_raw filter-chain nodes.", flush=True)
        private_phase(root, "filter", with_filter=True)
        print("PASS: isolated 48-kHz PipeWire bq_raw stereo graph initialized.", flush=True)
        print("Nodes:", CAPTURE, PLAYBACK)
        print("No speakers, ALSA, or system audio services were used.")
        if probe_activation:
            print("Stage 3/3: testing private stream activation (no audio).", flush=True)
            private_phase(root, "active", with_filter=True, active_probe=True)
            print("PASS: isolated active graph published Port objects.", flush=True)
        return 0

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-config", action="store_true",
                        help="Print isolated configuration without launching a process")
    parser.add_argument("--probe-activation", action="store_true",
                        help="Also request processing in a third, private-only test server; no audio")
    args = parser.parse_args(argv)
    if args.show_config and args.probe_activation:
        parser.error("Choose --show-config or --probe-activation, not both")
    try:
        return run_smoke(args.show_config, args.probe_activation)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
