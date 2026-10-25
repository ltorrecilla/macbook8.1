#!/usr/bin/env python3
"""Explicitly route ONE normal application stream between Raw and native D+.

No global-default changes, no WirePlumber configuration, no service edits.
Only an active named application on Raw may be sent to D+; never route the
D+ to-Raw processor back to its own D+ input (dangerous feedback loop).
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import re
import subprocess
import sys
import time
from typing import Callable

RAW = "MacBook_Speaker_Raw"
DPLUS = "MacBook_Speaker_D_Preview"
DPLUS_ALIASES = (DPLUS, "input." + DPLUS)
UNIT = "macbook81-dplus-native.service"


@dataclasses.dataclass(frozen=True)
class Stream:
    sid: int
    sink_id: int
    app: str
    media: str
    node: str
    corked: bool


class RouteError(Exception):
    pass


def run_command(*args: str) -> str:
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    try:
        completed = subprocess.run(args, capture_output=True, text=True,
                                   env=env, timeout=6, check=True)
        return completed.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        raise RouteError(f"Command failed: {' '.join(args)}: {exc}") from exc


def get_sinks(command: Callable[..., str] = run_command) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in command("pactl", "list", "short", "sinks").splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0].isdigit():
            result[fields[1]] = int(fields[0])
    return result


def _parse_prop(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    return value


def parse_long_inputs(text: str) -> dict[int, dict]:
    result: dict[int, dict] = {}
    current: dict | None = None
    for line in text.splitlines():
        match = re.match(r"^Sink Input #(\d+)\s*$", line)
        if match:
            sid = int(match.group(1))
            current = {"sid": sid, "props": {}, "corked": None}
            result[sid] = current
            continue
        if current is None:
            continue
        match = re.match(r"^\s+Corked:\s*(yes|no)\s*$", line, flags=re.I)
        if match:
            current["corked"] = match.group(1).lower() == "yes"
            continue
        match = re.match(r"^\s+([a-zA-Z][a-zA-Z0-9_.-]+)\s*=\s*(.*)$", line)
        if match:
            current["props"][match.group(1)] = _parse_prop(match.group(2))
    return result


def get_streams(command: Callable[..., str] = run_command) -> list[Stream]:
    long = parse_long_inputs(command("pactl", "list", "sink-inputs"))
    streams: list[Stream] = []
    for line in command("pactl", "list", "short", "sink-inputs").splitlines():
        cols = line.split()
        if len(cols) < 2 or not cols[0].isdigit() or not cols[1].isdigit():
            continue
        sid, sink_id = int(cols[0]), int(cols[1])
        item = long.get(sid, {})
        props = item.get("props", {})
        streams.append(Stream(sid, sink_id, props.get("application.name", ""),
                              props.get("media.name", ""), props.get("node.name", ""),
                              item.get("corked") is not False))
    return streams


def is_system_stream(stream: Stream) -> bool:
    # Explicit allowlisting of normal applications is safer than moving an
    # unnamed user-session processing stream back into its own virtual sink.
    if not stream.app.strip() or stream.app.casefold() in {
        "pipewire", "wireplumber", "macbook speaker (eq) output"
    }:
        return True
    fingerprints = (stream.media.casefold(), stream.node.casefold(), stream.app.casefold())
    return any(any(marker in value for marker in (
        "dplus_preview_to_raw", "macbook8,1 d+ safe eq preview output",
        "macbook speaker (eq) output", "macbook81-dplus", "macbook_speaker_dsp_out",
    )) for value in fingerprints)


def selected_stream(streams: list[Stream], *, stream_id: int | None, app: str | None,
                    require_playing: bool) -> Stream:
    if stream_id is not None:
        candidates = [s for s in streams if s.sid == stream_id]
    else:
        candidates = [s for s in streams if s.app.casefold() == (app or "").casefold()]
        if require_playing:
            candidates = [s for s in candidates if not s.corked]
    candidates = [s for s in candidates if not is_system_stream(s)]
    if not candidates:
        raise RouteError("No matching normal application stream. Play audio, then run 'list'.")
    if len(candidates) != 1:
        ids = ", ".join(str(s.sid) for s in candidates)
        raise RouteError(f"Ambiguous application: active stream IDs {ids}; use --id ID")
    chosen = candidates[0]
    if require_playing and chosen.corked:
        raise RouteError(f"Stream {chosen.sid} is paused (Corked: yes); play audio first")
    return chosen


def dplus_sink_name(sinks: dict[str, int]) -> str | None:
    for name in DPLUS_ALIASES:
        if name in sinks:
            return name
    return None


def route(destination: str, *, stream_id: int | None, app: str | None,
          command: Callable[..., str] = run_command,
          sleep: Callable[[float], None] = time.sleep) -> tuple[Stream, int]:
    if os.geteuid() == 0:
        raise RouteError("Run this as your desktop user, never with sudo")
    sinks = get_sinks(command)
    if RAW not in sinks:
        raise RouteError("Physical Raw speaker output is missing. No change made")
    current_default = command("pactl", "get-default-sink").strip()
    if current_default != RAW:
        raise RouteError(f"Global default is {current_default!r}, not Raw. No change made")
    dplus_name = dplus_sink_name(sinks)
    if destination == "dplus":
        if not dplus_name:
            raise RouteError("Managed D+ sink not found; run 'manage-native.py start' first")
        try:
            active = command("systemctl", "--user", "is-active", UNIT).strip()
        except RouteError:
            raise RouteError("Could not verify the managed native D+ service; no change made")
        if active != "active":
            raise RouteError("Managed native D+ service is not active; no change made")
    streams = get_streams(command)
    chosen = selected_stream(streams, stream_id=stream_id, app=app,
                             require_playing=(destination == "dplus"))
    raw_id = sinks[RAW]
    dplus_ids = {sinks[n] for n in DPLUS_ALIASES if n in sinks}
    if destination == "dplus":
        if chosen.sink_id != raw_id:
            if chosen.sink_id in dplus_ids:
                print(f"Stream {chosen.sid} is already connected to D+")
                return chosen, chosen.sink_id
            raise RouteError("Refusing to hijack a stream on headphones/Bluetooth/another output")
        target = dplus_name
        wanted = sinks[dplus_name]
    else:
        if chosen.sink_id == raw_id:
            print(f"Stream {chosen.sid} is already connected to Raw")
            return chosen, raw_id
        if chosen.sink_id not in dplus_ids:
            raise RouteError("Refusing to move an application away from an unrelated output")
        target = RAW
        wanted = raw_id

    command("pactl", "move-sink-input", str(chosen.sid), target)
    # Give WirePlumber time to accept or revert the requested target. Never
    # claim success based on an exit code if the stream was bounced to Raw.
    sleep(0.4)
    new_default = command("pactl", "get-default-sink").strip()
    now = {s.sid: s for s in get_streams(command)}
    if new_default != RAW:
        raise RouteError(f"Global default changed to {new_default!r}; stop the trial. No default changes made by this tool")
    if chosen.sid not in now:
        raise RouteError("The application's stream disappeared while moving; check playback")
    actual = now[chosen.sid].sink_id
    if actual != wanted:
        raise RouteError(f"Move did not stick: stream {chosen.sid} is on sink {actual}, expected {wanted}. No automatic retry")
    print(f"Stream {chosen.sid} ({chosen.app}) moved to {target}. Raw remains global default")
    if destination == "dplus":
        print("To undo: python3 scripts/dplus/route-app.py raw --id", chosen.sid)
    return chosen, wanted


def display(streams: list[Stream], sinks: dict[str, int]) -> None:
    names = {num: name for name, num in sinks.items()}
    print("ID     State       Application               Sink                 Title")
    for s in streams:
        if is_system_stream(s):
            continue
        app = s.app[:24]
        title = s.media[:56]
        status = "paused" if s.corked else "playing"
        print(f"{s.sid:<6} {status:<11} {app:<25} {names.get(s.sink_id,str(s.sink_id)):<20} {title}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="Show app streams and their actual sink (read-only)")
    for cmd in ("dplus", "raw"):
        p = sub.add_parser(cmd, help=f"Move exactly one eligible normal application to {cmd}")
        choice = p.add_mutually_exclusive_group(required=True)
        choice.add_argument("--app", help="Exact application.name, only if one playing stream")
        choice.add_argument("--id", dest="sid", type=int, help="Exact sink-input stream ID from list")
    args = parser.parse_args(argv)
    try:
        if os.geteuid() == 0:
            raise RouteError("Run without sudo")
        if args.cmd == "list":
            display(get_streams(), get_sinks())
        else:
            route(args.cmd, stream_id=getattr(args, "sid", None),
                  app=getattr(args, "app", None))
        return 0
    except RouteError as exc:
        print("STOP:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
