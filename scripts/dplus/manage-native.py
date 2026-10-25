#!/usr/bin/env python3
"""Install/inspect/remove the experimental MacBook8,1 D+ *user* service.

No root, no edits to PipeWire/WirePlumber's normal configuration, no automatic
start or enable. Generated config remains local: private reference JSON is
NEVER copied into the public repo or exported from the computer.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "dplus-topology-preview.py"
GUARD = HERE / "dplus-session-guard.py"
HOME = Path.home()
MANAGED = HOME / ".config" / "macbook81-dplus-native"
UNIT_PATH = HOME / ".config" / "systemd" / "user" / "macbook81-dplus-native.service"
UNIT = UNIT_PATH.name
FILES = {"dplus.conf", "dplus-session-guard.py"}
MANIFEST = "manifest.json"
FROZEN_SHA256 = "105a8bd171248a1ec0707bfc552d8dfebe4bdd8f65873af071f67e190c8862c2"
MARKER = "# Managed by macbook8.1 D+ native experimental installer"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_module():
    if digest(FROZEN.read_bytes()) != FROZEN_SHA256:
        raise RuntimeError("Working preview source changed. Refusing unknown DSP graph")
    spec = importlib.util.spec_from_file_location("approved_dplus_preview", FROZEN)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def unit_text():
    # %% not used: systemd %h expands the user's home, without shell quoting.
    return f"""{MARKER}
[Unit]
Description=MacBook8,1 D+ Native PipeWire speaker preview (experimental)
After=pipewire.service pipewire-pulse.service wireplumber.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 %h/.config/macbook81-dplus-native/dplus-session-guard.py
Restart=no
TimeoutStopSec=10

[Install]
WantedBy=default.target
"""


def render(profile: Path):
    module = read_module()
    config, error = module.generate_config(profile.resolve(strict=True))
    if error > .12 or 'outputs = [ "copyOutL:Out" "copyOutR:Out" "zeroL:Out" "zeroR:Out" ]' not in config:
        raise RuntimeError("Frozen topology or 48-kHz response check failed")
    if 'target.object = "MacBook_Speaker_Raw"' not in config:
        raise RuntimeError("Raw playback target missing")
    return config.encode("utf-8"), error


def ensure_user():
    if os.geteuid() == 0:
        raise RuntimeError("Never run as sudo/root. This installs only for your user")


def systemctl(*args, check=True):
    return subprocess.run(["systemctl", "--user", *args], check=check)


def manifest_for(artifacts):
    return {"schema": 1, "files": {name: digest(data) for name, data in artifacts.items()}}


def existing():
    return MANAGED.exists() or UNIT_PATH.exists()


def install(profile: Path):
    ensure_user()
    config, error = render(profile)
    if existing():
        raise RuntimeError("Managed D+ files already exist; refusing to overwrite. Run status/remove first")
    if not GUARD.is_file():
        raise RuntimeError("Installer guard file missing")
    artifacts = {"dplus.conf": config, "dplus-session-guard.py": GUARD.read_bytes(),
                 "unit": unit_text().encode("utf-8")}
    created = []
    try:
        MANAGED.mkdir(parents=True, mode=0o700, exist_ok=False)
        created.append(MANAGED)
        MANAGED.chmod(0o700)
        UNIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            path = MANAGED / name
            path.write_bytes(artifacts[name])
            path.chmod(0o600)
            created.append(path)
        manifest_data = (json.dumps(manifest_for(artifacts), indent=2, sort_keys=True) + "\n").encode()
        manifest = MANAGED / MANIFEST
        manifest.write_bytes(manifest_data)
        manifest.chmod(0o600)
        created.append(manifest)
        UNIT_PATH.write_bytes(artifacts["unit"])
        UNIT_PATH.chmod(0o644)
        created.append(UNIT_PATH)
        systemctl("daemon-reload")
    except BaseException:
        for item in reversed(created):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                try: item.rmdir()
                except OSError: pass
        raise
    print("Installed local D+ config and user unit; NOT started, NOT enabled")
    print(f"Response-matched 48k EQ magnitude fit max deviation: {error:.4f} dB (not phase/limiter parity)")
    print("Next: python3 scripts/dplus/manage-native.py start")


def verify_managed():
    manifest_path = MANAGED / MANIFEST
    if not manifest_path.is_file() or not UNIT_PATH.is_file():
        raise RuntimeError("Managed files incomplete or absent")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or set(data.get("files", {})) != FILES | {"unit"}:
        raise RuntimeError("Unexpected manifest; do not remove unknown files")
    for name, expected in data["files"].items():
        path = UNIT_PATH if name == "unit" else MANAGED / name
        if not path.is_file() or digest(path.read_bytes()) != expected:
            raise RuntimeError(f"Managed file {path} differs from installed version; refusing to remove")
    if set(p.name for p in MANAGED.iterdir()) != FILES | {MANIFEST}:
        raise RuntimeError("Unknown files in managed directory; refusing to remove")
    return True


def status():
    print("Local install:", "present" if existing() else "absent")
    if existing():
        try:
            verify_managed()
            print("Managed file integrity: OK")
        except (RuntimeError, OSError, ValueError) as exc:
            print("Managed file integrity:", exc)
    systemctl("is-enabled", UNIT, check=False)
    systemctl("is-active", UNIT, check=False)
    subprocess.run(["pactl", "get-default-sink"], check=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    cmd = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "install"):
        sub = cmd.add_parser(name)
        sub.add_argument("--profile", required=True, type=Path)
    for name in ("start", "stop", "status", "remove"):
        cmd.add_parser(name)
    args = ap.parse_args()
    try:
        ensure_user()
        if args.cmd == "check":
            _, error = render(args.profile)
            print(f"PASS: frozen topology, reference identity and 48k fit ({error:.4f} dB magnitude only)")
            print("No changes made. This does not prove live PipeWire audio")
        elif args.cmd == "install":
            install(args.profile)
        elif args.cmd == "start":
            verify_managed()
            systemctl("start", UNIT)
            print("Started opt-in user service; Raw must remain default. Verify sound manually")
        elif args.cmd == "stop":
            systemctl("stop", UNIT)
            print("Stopped managed D+ only; did not change the default output")
        elif args.cmd == "status":
            status()
        elif args.cmd == "remove":
            if not existing():
                print("No managed D+ installation found")
            else:
                verify_managed()
                systemctl("disable", "--now", UNIT)
                for name in FILES | {MANIFEST}:
                    (MANAGED / name).unlink()
                MANAGED.rmdir()
                UNIT_PATH.unlink()
                systemctl("daemon-reload")
                print("Removed only managed files and user unit; Raw and other audio untouched")
        return 0
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print("STOP:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
