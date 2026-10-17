#!/usr/bin/env python3
"""Stage a *local* MacBook8,1 source archive without installing anything.

Accepts the collector's macbook81-audio-details.tar.gz. Extracts only known
source/config members into a NEW directory, with hashes. Neither builds kernel
modules nor changes audio settings. Staged files MUST NOT be installed blindly.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import tempfile

# Only files needed for research toward a DKMS build. Old root installer,
# DKMS remover, resume scripts, reports and personal session data are excluded.
SOURCE_FILES = [
    "dkms.conf", "dkms_build.sh", "install.cirrus.driver.sh",
    "install.generic.driver.sh", "install.azx.driver.sh",
    "Makefile_cs420x", "Makefile_cirrus",
    "patch_cirrus/cs420x.c", "patch_cirrus/patch_cirrus.c",
    "patch_cirrus/patch_cirrus_a1534_pcm.h",
    "patch_cirrus/patch_cirrus_a1534_setup.h",
    "patch_cirrus/patch_cirrus_macbook81_setup.h",
    "patch_cirrus/Makefile_cs420x", "patch_cirrus/Makefile_cirrus",
    "patch_cirrus/Makefile_azx",
]
CONFIG_FILES = ["mb81-singlecmd.conf", "wireplumber-rawpcm.conf", "pipewire-speaker.conf"]
REQUIRED = {"source/" + p for p in SOURCE_FILES} | {"config/" + p for p in CONFIG_FILES}
MAX_FILE = 1_000_000


def error(message):
    raise ValueError(message)


def read_selected(path):
    result = {}
    with tarfile.open(path, "r:gz") as archive:
        members = {}
        for member in archive:
            # Refuse duplicate entries and links; only extract a fixed whitelist.
            name = member.name.removeprefix("./")
            parts = PurePosixPath(name).parts
            if name not in REQUIRED:
                continue
            if ".." in parts or PurePosixPath(name).is_absolute():
                error(f"Unsafe member path: {name}")
            if name in members:
                error(f"Duplicate source entry: {name}")
            if not member.isfile() or not 0 < member.size <= MAX_FILE:
                error(f"Invalid member type or size: {name}")
            members[name] = member
        missing = REQUIRED - members.keys()
        if missing:
            error("Missing required source/config files: " + ", ".join(sorted(missing)))
        for name, member in sorted(members.items()):
            stream = archive.extractfile(member)
            if stream is None:
                error(f"Cannot read {name}")
            data = stream.read(MAX_FILE + 1)
            if len(data) != member.size:
                error(f"Truncated or oversize member: {name}")
            result[name] = data
    if b'PACKAGE_NAME="macbook12-audio"' not in result["source/dkms.conf"]:
        error("Unknown DKMS source layout")
    for module in (b'snd-hda-codec-cs420x', b'snd-hda-codec-generic', b'snd-hda-intel'):
        if module not in result["source/dkms.conf"]:
            error("DKMS recipe missing module " + module.decode())
    return result


def stage(source, destination):
    source = Path(source).expanduser().resolve()
    destination = Path(destination).expanduser().absolute()
    if not source.is_file():
        error(f"Archive not found: {source}")
    if destination.exists() or destination.is_symlink():
        error(f"Refusing to overwrite existing path: {destination}")
    if not destination.parent.is_dir():
        error(f"Destination parent directory does not exist: {destination.parent}")
    data = read_selected(source)
    temp = Path(tempfile.mkdtemp(prefix=".mb81-audio-stage-", dir=destination.parent))
    try:
        manifest = {"collector_archive_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "files": {}}
        for name, contents in sorted(data.items()):
            target = temp / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents)
            target.chmod(0o700 if name in ("source/dkms_build.sh", "source/install.cirrus.driver.sh") else 0o600)
            manifest["files"][name] = hashlib.sha256(contents).hexdigest()
        (temp / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        (temp / "NOT-INSTALLABLE-YET.txt").write_text(
            "This is a local DKMS-source STAGING BUNDLE, not an installer.\n"
            "NEVER run any install.*.sh from this folder on your working MacBook.\n"
            "Missing verified suspend/resume and jack-switch service assets.\n"
            "Build scripts download kernel tarballs without verified hashes.\n"
            "Arch/CachyOS initramfs hooks and kernel update integration not validated.\n"
            "Three patched HDA modules must be built and installed together.\n"
            "No files from this staging bundle should be published without\n"
            "license/provenance and private-data review.\n"
        )
        temp.rename(destination)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return len(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="Input audio-details.tar.gz from collector")
    parser.add_argument("destination", help="NEW staging directory, must not exist")
    args = parser.parse_args()
    try:
        count = stage(args.archive, args.destination)
    except (OSError, tarfile.TarError, ValueError) as ex:
        print("ERROR:", ex, file=sys.stderr)
        return 1
    print(f"Staged {count} known source and config files in {args.destination}")
    print("NO kernel drivers, PipeWire settings, initramfs or services were changed.")
    print("Read NOT-INSTALLABLE-YET.txt; do not run the legacy installers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
