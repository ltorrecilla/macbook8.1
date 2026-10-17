#!/usr/bin/env python3
"""Read-only structural audit of user-collected MacBook8,1 audio archives.

Checks expected files, duplicate support-file hashes, service entrypoints and
legacy installer hazards. Does NOT extract, execute, build or install source.
A passing audit is NOT proof of installation safety.
"""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

SUPPORT_NAMES = (
    "efi_recover.py", "mb81-resume-recover.service", "mb81-jack-switch.service",
)
SOURCE_FILES = (
    "source/resume_recover.sh", "source/mb81-jack-switch.sh",
    "source/dkms.conf", "source/dkms_build.sh", "source/dkms.sh",
    "source/install.sh",
)
MAX_ARCHIVE_SIZE = 5_000_000
MAX_FILE_SIZE = 500_000


class AuditFailure(Exception):
    pass


def read_tar(path, allowed_names=None, allow_support=False):
    """Read only fixed subsets; never extract the archive to disk."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_ARCHIVE_SIZE:
        raise AuditFailure("Archive missing or above 5 MB size limit")
    files = {}
    with tarfile.open(path, "r:gz") as arc:
        for member in arc.getmembers():
            name = member.name
            if name.startswith("./"):
                name = name[2:]
            parts = PurePosixPath(name).parts
            if PurePosixPath(name).is_absolute() or ".." in parts:
                raise AuditFailure("Archive has an unsafe path")
            if not member.isfile():
                continue
            if allowed_names is not None and name not in allowed_names:
                continue
            if allow_support:
                if len(parts) != 2 or parts[0] != "files":
                    continue
                if not re.fullmatch(
                    r"\d{3}-(?:efi_recover\.py|mb81-resume-recover\.service|mb81-jack-switch\.service)",
                    parts[1],
                ):
                    continue
            if name in files:
                raise AuditFailure("Repeated file entry in archive")
            if not (0 < member.size <= MAX_FILE_SIZE):
                raise AuditFailure("Unexpected file size in archive")
            stream = arc.extractfile(member)
            if stream is None:
                raise AuditFailure("Unreadable selected file")
            data = stream.read(MAX_FILE_SIZE + 1)
            if len(data) != member.size:
                raise AuditFailure("Unexpected size for selected file")
            files[name] = data
    return files


def audit(source_archive, support_archive):
    original = read_tar(source_archive, allowed_names=set(SOURCE_FILES))
    support = read_tar(support_archive, allow_support=True)
    errors, notes = [], []
    for name in SOURCE_FILES:
        if name not in original:
            errors.append("Source archive missing " + name)
    grouped = {}
    for name in SUPPORT_NAMES:
        copies = [
            data for path, data in support.items()
            if path.split("/", 1)[1].endswith("-" + name)
        ]
        grouped[name] = copies
        if len(copies) != 2:
            errors.append(f"Expected 2 recovered copies of {name}; found {len(copies)}")
        elif copies[0] != copies[1]:
            errors.append(f"Source and installed copies differ: {name}")
    if errors:
        return False, errors, notes

    for name, copies in grouped.items():
        digest = hashlib.sha256(copies[0]).hexdigest()
        notes.append(f"MATCH {name}: 2 identical copies (SHA256 {digest[:16]}...)")

    required_targets = {
        "mb81-resume-recover.service": b"ExecStart=/usr/local/bin/mb81-resume-recover",
        "mb81-jack-switch.service": b"ExecStart=/usr/local/bin/mb81-jack-switch",
    }
    for name, target in required_targets.items():
        if target not in grouped[name][0]:
            errors.append(f"Unexpected ExecStart in {name}; review manually")
        else:
            notes.append(f"LINK {name}: target has corresponding .sh implementation")
    dkms = original["source/dkms.conf"]
    for mod in (b"snd-hda-codec-cs420x", b"snd-hda-codec-generic", b"snd-hda-intel"):
        if mod not in dkms:
            errors.append(f"DKMS recipe does not mention {mod.decode()}")
    if b"update-initramfs" in original["source/install.sh"]:
        notes.append("RISK: legacy installer assumes Ubuntu update-initramfs, not CachyOS mkinitcpio")
    if b"rm -rf $var_dkms_dir" in original["source/dkms.sh"]:
        notes.append("RISK: legacy dkms.sh deletes DKMS state; preserve original_module backups")
    if b"input.MacBook_Speaker" in original["source/mb81-jack-switch.sh"]:
        notes.append("RISK: jack-switch defaults to EQ, although owner prefers the raw sink")
    if b'os.open(f"{PCIDEV}/resource0"' in grouped["efi_recover.py"][0]:
        notes.append("RISK: codec recovery accesses controller MMIO; isolate it from default installation")
    notes.append("BLOCKED: no clean-install, kernel-upgrade, resume or uninstall safety tests are complete")
    return not errors, errors, notes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audio-details", required=True)
    p.add_argument("--audio-support", required=True)
    args = p.parse_args()
    try:
        consistent, errors, notes = audit(args.audio_details, args.audio_support)
    except (OSError, tarfile.TarError, AuditFailure) as exc:
        print(f"Archive audit could not complete: {exc}", file=sys.stderr)
        return 2
    for line in notes:
        print(line)
    for error in errors:
        print("FAIL:", error, file=sys.stderr)
    if consistent:
        print("PASS: recovered files match expected local snapshot structure.")
        print("NOT READY: evidence is consistent, but no public audio installer is safe yet.")
    else:
        print("FAIL: evidence bundle incomplete or inconsistent.", file=sys.stderr)
    return 0 if consistent else 1


if __name__ == "__main__":
    sys.exit(main())
