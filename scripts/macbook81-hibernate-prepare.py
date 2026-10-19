#!/usr/bin/env python3
"""Prepare the reviewed MacBook8,1 for a separate manual hibernation test.

HARDWARE UNTESTED. This helper never initiates sleep, rebuilds an initramfs,
changes boot parameters, unloads a driver, or disables zram. Default: --check.
It is deliberately restricted to the exact installation reviewed in this chat.

Usage (run from the directory containing this file):
  sudo python3 macbook81-hibernate-prepare.py --check
  sudo python3 macbook81-hibernate-prepare.py --apply
  sudo python3 macbook81-hibernate-prepare.py --status

Preparation archives the unused e236... boot directory, creates a 10 GiB SSD
swapfile in a top-level @swap subvolume, adds its mount/swap entries to fstab,
and sets HibernateMode=shutdown. Backups and recovery notes are written under
/var/backups/macbook81-hibernate/. It uses systemd's EFI HibernateLocation
mechanism; the running kernel's active initramfs must contain resume support.

Only after successful preparation (CanHibernate yes or challenge), save all
work before the first manual test: systemctl hibernate. After power-off, use
the power button and select linux-cachyos 7.2.9-2-cachyos again. Check that the
same session returns, then check keyboard/trackpad, audio, Wi-Fi, Bluetooth,
and camera. A fresh login alone does not demonstrate successful restoration.
Do not update the kernel between hibernating and restoring the session.

If preparation stops, keep its report and do not blindly rerun --apply or
delete active swap. --status remains available after partial preparation.
If restoring repeatedly hangs, a one-time noresume kernel parameter allows
a fresh boot, abandoning the saved hibernation session.

Sources:
https://github.com/systemd/systemd/blob/v261/src/shared/hibernate-util.c
https://github.com/systemd/systemd/blob/v261/src/sleep/sleep.c
https://www.freedesktop.org/software/systemd/man/systemd-hibernate-resume-generator.html
https://github.com/archlinux/mkinitcpio/blob/master/install/systemd
https://btrfs.readthedocs.io/en/latest/Swapfile.html
https://man7.org/linux/man-pages/man8/swapon.8.html
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

KERNEL = "7.2.9-2-cachyos"
MACHINE = "f1d9c71eb83b40baa8a21f233674ca7b"
OLD_MACHINE = "e236028073f84f21be594c22fdbfe6f9"
ROOT_UUID = "7dfc4697-c530-4f90-838d-6fb25ded719b"
BOOT = Path("/boot")
LIMINE = BOOT / "limine.conf"
DEFAULTS = Path("/etc/default/limine")
FSTAB = Path("/etc/fstab")
SWAP = Path("/swap/swapfile")
DROPIN = Path("/etc/systemd/sleep.conf.d/70-macbook81-hibernate.conf")
BACKUPS = Path("/var/backups/macbook81-hibernate")
TAG = "macbook81-hibernate-prepare"
SLEEP_TEXT = b"[Sleep]\nHibernateMode=shutdown\n"
GIB = 1024 ** 3
LOG = None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(*args, timeout=180):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                            env={**os.environ, "LC_ALL": "C", "SYSTEMD_PAGER": "cat"})
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args!r}\n"
                           f"{result.stdout.strip()}\n{result.stderr.strip()}")
    return result.stdout.strip()


def digest(path, algorithm="sha256"):
    value = hashlib.new(algorithm)
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def regular(path):
    require(path.exists() and not path.is_symlink() and path.is_file(),
            f"Expected an existing regular file, not a symlink: {path}")


def atomic_write(path, data, mode=0o600, owner=(0, 0), preserve=None, exclusive=False):
    descriptor, temporary = tempfile.mkstemp(prefix=".mb81-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            os.fchown(stream.fileno(), *owner)
            if preserve is not None:
                for name in os.listxattr(preserve):
                    os.setxattr(stream.fileno(), name, os.getxattr(preserve, name))
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            os.link(temporary, path)  # Publish atomically, refusing an existing destination.
        else:
            os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def mount_info(mountpoint):
    data = json.loads(run("findmnt", "--json", "--mountpoint", mountpoint,
                          "--output", "TARGET,SOURCE,FSTYPE,UUID,OPTIONS"))
    entries = data.get("filesystems", [])
    require(len(entries) == 1 and entries[0]["target"] == mountpoint,
            f"Expected an exact mount at {mountpoint}")
    return entries[0]


def swaps():
    # swapon selects columns through --show=; it has no --json or --output.
    output = run("swapon", "--show=NAME,TYPE,SIZE,USED,PRIO", "--bytes",
                 "--noheadings", "--raw")
    entries = []
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = line.split()
        require(len(fields) == 5, f"Unexpected swapon output row: {line!r}")
        name, kind, size, used, priority = fields
        require(re.fullmatch(r"[0-9]+", size) and re.fullmatch(r"[0-9]+", used)
                and re.fullmatch(r"-?[0-9]+", priority),
                f"Unexpected numeric values in swapon output: {line!r}")
        # Raw output escapes unusual path characters. The exact-host checks
        # below accept only /dev/zram0 and /swap/swapfile, which need no decoding.
        entries.append({"name": name, "type": kind, "size": int(size),
                        "used": int(used), "prio": int(priority)})
    return entries


def tree_manifest(root):
    def walk_error(error):
        raise error

    manifest = {}
    for directory, directories, files in os.walk(root, followlinks=False, onerror=walk_error):
        for name in sorted(directories + files):
            path = Path(directory) / name
            relative = str(path.relative_to(root))
            entry = path.lstat()
            if stat.S_ISLNK(entry.st_mode):
                manifest[relative] = ["link", os.readlink(path)]
            elif stat.S_ISDIR(entry.st_mode):
                manifest[relative] = ["directory"]
            elif stat.S_ISREG(entry.st_mode):
                manifest[relative] = ["file", entry.st_size, digest(path)]
            else:
                raise RuntimeError(f"Unexpected special file: {path}")
    return manifest


def active_boot_files():
    regular(LIMINE)
    configs = sorted(str(p) for p in BOOT.rglob("*")
                     if p.name.casefold() in {"limine.conf", "limine.cfg"})
    require(configs == [str(LIMINE)], f"Unexpected Limine configuration files: {configs}")
    text = LIMINE.read_text()
    require(OLD_MACHINE not in text, "The old boot directory is referenced by limine.conf.")
    require(not re.search(r"(?im)^\s*(?:include|include_path|config|config_path)\s*[:=]", text),
            "An included Limine configuration needs separate review.")
    found = {}
    for relative, expected in re.findall(r"boot\(\):(/[^\s#]+)#([0-9a-fA-F]+)", text):
        if relative.startswith(f"/{MACHINE}/"):
            require(".." not in Path(relative).parts, "Unexpected boot path traversal.")
            path = BOOT / relative.lstrip("/")
            regular(path)
            require(len(expected) == 128 and digest(path, "blake2b") == expected.lower(),
                    f"Limine BLAKE2b-512 hash does not match: {path}")
            found[str(path)] = expected.lower()
    needed = [str(BOOT / MACHINE / package / name)
              for package in ("linux-cachyos", "linux-cachyos-lts")
              for name in ("vmlinuz", "initramfs")]
    require(all(path in found for path in needed),
            "Both reviewed kernels and both initramfs files must have valid active hash references.")
    return found


def check():
    require(os.geteuid() == 0, "Run with sudo; checking the active initramfs requires root.")
    for program in ("findmnt", "btrfs", "lsinitcpio", "systemctl", "systemd-analyze", "swapon", "mount", "umount", "busctl"):
        require(shutil.which(program), f"Required program is not installed: {program}")
    require(Path("/sys/class/dmi/id/product_name").read_text().strip() == "MacBook8,1",
            "This helper is restricted to MacBook8,1.")
    require(os.uname().release == KERNEL, f"The running kernel must still be {KERNEL}.")
    require(Path("/etc/machine-id").read_text().strip() == MACHINE,
            "This is not the installation reviewed in the chat.")
    require(not Path("/var/lib/pacman/db.lck").exists(), "A package operation is in progress.")
    root = mount_info("/")
    require(root["fstype"] == "btrfs" and root["uuid"] == ROOT_UUID,
            "The root filesystem does not match the reviewed Btrfs volume.")
    require("rw" in root["options"].split(","), "Root is not mounted read-write.")
    boot = mount_info("/boot")
    require(boot["fstype"] == "vfat" and "rw" in boot["options"].split(","),
            "The reviewed EFI partition must be mounted read-write at /boot.")
    require(shutil.disk_usage("/").free >= 12 * GIB, "At least 12 GiB free on root is required.")
    require(re.search(r"Total devices\s+1\b", run("btrfs", "filesystem", "show", "--raw", "/")),
            "This helper requires a single-device Btrfs filesystem.")
    for path in (DEFAULTS, FSTAB):
        regular(path)
    hashes = {str(p): digest(p) for p in (LIMINE, DEFAULTS, FSTAB)}
    boot_hashes = active_boot_files()
    commandline = Path("/proc/cmdline").read_text().split()
    require(not any(x == "noresume" or x.startswith(("resume=", "resume_offset=", "noresume="))
                    for x in commandline), "Existing resume/noresume parameters need separate review.")
    require("mem_sleep_default=s2idle" in commandline and
            any(x.startswith("initcall_blacklist=") and "dw_pci_driver_init" in x for x in commandline),
            "The reviewed s2idle and DMA workarounds are not active.")
    require("[s2idle]" in Path("/sys/power/mem_sleep").read_text(), "s2idle is not currently selected.")
    require("disk" in Path("/sys/power/state").read_text().split(), "Kernel hibernation is unavailable.")
    require(Path("/sys/power/resume").read_text().strip() == "0:0" and
            Path("/sys/power/resume_offset").read_text().strip() == "0",
            "A runtime resume destination is already configured; do not overwrite it.")
    version = re.search(r"^systemd\s+(\d+)", run("systemctl", "--version"))
    require(version and int(version[1]) >= 255, "systemd version 255 or newer is required.")
    efi = mount_info("/sys/firmware/efi/efivars")
    require(efi["fstype"] == "efivarfs" and "rw" in efi["options"].split(","),
            "Writable efivarfs is required for automatic EFI resume location discovery.")
    image = BOOT / MACHINE / "linux-cachyos/initramfs"
    image_files = set(line.strip().lstrip("./") for line in run("lsinitcpio", str(image)).splitlines())
    required = {"usr/lib/systemd/systemd-hibernate-resume",
                "usr/lib/systemd/system-generators/systemd-hibernate-resume-generator",
                "usr/lib/systemd/system/systemd-hibernate-resume.service"}
    require(required <= image_files, f"Active initramfs lacks resume components: {sorted(required-image_files)}")
    initial_swaps = swaps()
    require([(s["name"], s["prio"]) for s in initial_swaps] == [("/dev/zram0", 100)],
            "Expected only /dev/zram0 at priority 100; existing disk swap needs separate review.")
    require(not os.path.lexists("/swap"), "/swap already exists; it will not be reused or overwritten.")
    subvolumes = run("btrfs", "subvolume", "list", "-a", "/")
    paths = [line.split(" path ", 1)[1].removeprefix("<FS_TREE>/")
             for line in subvolumes.splitlines() if " path " in line]
    require("@swap" not in paths, "A top-level @swap subvolume already exists.")
    fstab = FSTAB.read_bytes()
    for line in fstab.decode().splitlines():
        fields = line.partition("#")[0].split()
        if not fields:
            continue
        require("@swap" not in line and "/swap" not in fields[:2], "fstab already refers to the planned swap.")
        require(not (len(fields) > 2 and fields[2] == "swap" and not fields[0].startswith("/dev/zram")),
                "fstab already contains persistent swap; refusing to add another target.")
    require(TAG.encode() not in fstab, "An earlier preparation block already exists in fstab.")
    require(not os.path.lexists(DROPIN), f"The planned configuration already exists: {DROPIN}")
    require(not DROPIN.parent.is_symlink(), "The sleep drop-in directory must not be a symlink.")
    sleep_config = run("systemd-analyze", "--no-pager", "cat-config", "systemd/sleep.conf")
    for key, value in re.findall(r"(?im)^\s*(HibernateMode|AllowHibernation)\s*=\s*([^\n]*)", sleep_config):
        allowed = ("shutdown",) if key.lower() == "hibernatemode" else ("yes", "true", "1")
        require(value.strip().lower() in allowed, f"Existing conflicting sleep setting: {key}={value}")
    old = BOOT / OLD_MACHINE
    require(old.is_dir() and not old.is_symlink(), "The reviewed unused boot directory is absent or a symlink.")
    manifest = tree_manifest(old)
    require(manifest and any(v[0] == "file" for v in manifest.values()), "Old boot archive would be empty.")
    return {"original_hashes": hashes, "active_boot_hashes": boot_hashes,
            "old_manifest": manifest, "initial_swaps": initial_swaps,
            "fstab_bytes": fstab, "fstab_stat": FSTAB.stat(),
            "sleep_config": sleep_config, "applespi_in_initramfs": any("applespi" in p for p in image_files)}


class Journal:
    def __init__(self, plan):
        require(not BACKUPS.is_symlink(), "Backup directory must not be a symlink.")
        BACKUPS.mkdir(mode=0o700, parents=True, exist_ok=True)
        require(BACKUPS.stat().st_uid == 0, "Backup directory is not owned by root.")
        os.chmod(BACKUPS, 0o700)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.path = BACKUPS / stamp
        self.path.mkdir(mode=0o700)
        self.state = {"helper": TAG, "hardware_tested": False, "backup": str(self.path),
                      "kernel": KERNEL, "machine_id": MACHINE, "root_uuid": ROOT_UUID,
                      "original_hashes": plan["original_hashes"], "active_boot_hashes": plan["active_boot_hashes"],
                      "fstab_original_metadata": {"mode": stat.S_IMODE(plan["fstab_stat"].st_mode),
                                                  "uid": plan["fstab_stat"].st_uid, "gid": plan["fstab_stat"].st_gid},
                      "checkpoints": [], "prepared": False}
        self.event("Backup directory created")

    def event(self, message, **values):
        self.state.update(values)
        self.state["checkpoints"].append(message)
        atomic_write(self.path / "state.json", (json.dumps(self.state, indent=2) + "\n").encode())
        with (self.path / "preparation.log").open("a") as stream:
            os.chmod(stream.name, 0o600)
            stream.write(message + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        print(message, flush=True)


def unchanged(plan):
    for path, expected in plan["original_hashes"].items():
        require(digest(path) == expected, f"Configuration changed during preparation: {path}")
    require(active_boot_files() == plan["active_boot_hashes"], "Active boot configuration changed.")


def apply(plan):
    global LOG
    LOG = Journal(plan)
    top = LOG.path / "top-level-mount"
    mounted = False
    recovery = ("No sleep is initiated by this helper. Read state.json and preparation.log before recovery.\n"
                "If /swap/swapfile is active, swapoff must succeed before unmounting /swap.\n"
                "If swapoff fails, STOP; keep the swapfile and filesystem intact.\n"
                "Remove only this helper's sleep drop-in, and only if its SHA256 matches state.json.\n"
                "Restore saved fstab only if current SHA256 matches fstab_written_sha256; otherwise review\n"
                "and remove only the block between this helper's BEGIN/END markers. Run systemctl daemon-reload.\n"
                "Do not delete the swapfile or @swap subvolume automatically. The unused boot files remain\n"
                "archived here; copying them back consumes EFI partition capacity and is not required to boot.\n")
    atomic_write(LOG.path / "RECOVERY.txt", recovery.encode())
    try:
        unchanged(plan)
        for source, name in ((LIMINE, "limine.conf"), (DEFAULTS, "limine-defaults"), (FSTAB, "fstab")):
            shutil.copy2(source, LOG.path / name)
            require(digest(LOG.path / name) == plan["original_hashes"][str(source)], "Configuration backup mismatch.")
        atomic_write(LOG.path / "sleep-config-before.txt", plan["sleep_config"].encode())
        LOG.event("Original configurations backed up")
        old = BOOT / OLD_MACHINE
        archive = LOG.path / OLD_MACHINE
        shutil.copytree(old, archive, symlinks=True)
        require(tree_manifest(archive) == plan["old_manifest"] == tree_manifest(old), "Boot archive verification failed.")
        os.sync()
        LOG.event("Unused boot directory copied, byte-verified, and synced", archived_boot=str(archive),
                  archived_boot_manifest=plan["old_manifest"])
        unchanged(plan)
        shutil.rmtree(old)
        os.sync()
        require(active_boot_files() == plan["active_boot_hashes"], "Active boot hashes changed after cleanup.")
        LOG.event("Only the verified unused boot directory removed", boot_cleanup_complete=True)
        top.mkdir(mode=0o700)
        run("mount", "-t", "btrfs", "-o", "subvolid=5", f"UUID={ROOT_UUID}", str(top))
        mounted = True
        require(not os.path.lexists(top / "@swap"), "@swap appeared after preflight; refusing to overwrite it.")
        run("btrfs", "subvolume", "create", str(top / "@swap"))
        LOG.event("Top-level @swap subvolume created", created_subvolume="@swap")
        run("umount", str(top))
        mounted = False
        Path("/swap").mkdir(mode=0o700)
        run("mount", "-t", "btrfs", "-o", "subvol=/@swap,noatime", f"UUID={ROOT_UUID}", "/swap")
        os.chmod("/swap", 0o700)
        LOG.event("New @swap subvolume mounted privately at /swap", created_mount="/swap")
        run("btrfs", "filesystem", "mkswapfile", "--size", "10G", str(SWAP), timeout=300)
        os.chmod(SWAP, 0o600)
        offset = run("btrfs", "inspect-internal", "map-swapfile", "-r", str(SWAP))
        require(offset.isdigit() and int(offset) > 0, "Btrfs did not return a valid page-based resume offset.")
        require(SWAP.stat().st_size == 10 * GIB and stat.S_IMODE(SWAP.stat().st_mode) == 0o600,
                "Unexpected swapfile size or permissions.")
        LOG.event("10 GiB Btrfs swapfile created and mapping validated", swapfile=str(SWAP), resume_offset=int(offset))
        run("swapon", "--priority", "10", str(SWAP))
        require(sorted((s["name"], s["prio"]) for s in swaps()) == [("/dev/zram0", 100), (str(SWAP), 10)],
                "Swap state differs from the planned zram plus disk swap configuration.")
        LOG.event("New disk swap activated at priority 10; zram preserved at priority 100", swap_activated=True)
        unchanged(plan)
        block = (f"\n# BEGIN {TAG}\nUUID={ROOT_UUID} /swap btrfs subvol=/@swap,noatime 0 0\n"
                 f"{SWAP} none swap defaults,pri=10 0 0\n# END {TAG}\n").encode()
        updated = plan["fstab_bytes"] + (b"" if plan["fstab_bytes"].endswith(b"\n") else b"\n") + block
        metadata = plan["fstab_stat"]
        LOG.event("Intended fstab content hash recorded before commit",
                  fstab_written_sha256=hashlib.sha256(updated).hexdigest(), fstab_committed=False)
        atomic_write(FSTAB, updated, stat.S_IMODE(metadata.st_mode), (metadata.st_uid, metadata.st_gid), preserve=FSTAB)
        LOG.event("Tagged mount and swap entries written to fstab", fstab_committed=True)
        DROPIN.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        require(not DROPIN.parent.is_symlink(), "Sleep drop-in directory became a symlink.")
        require(not os.path.lexists(DROPIN), "Sleep drop-in appeared after preflight; refusing to overwrite it.")
        LOG.event("Intended sleep configuration hash recorded before commit", sleep_dropin=str(DROPIN),
                  sleep_dropin_sha256=hashlib.sha256(SLEEP_TEXT).hexdigest(), sleep_dropin_committed=False)
        atomic_write(DROPIN, SLEEP_TEXT, mode=0o644, exclusive=True)
        LOG.event("Only hibernation completion mode set to shutdown", sleep_dropin_committed=True)
        run("systemctl", "daemon-reload")
        os.sync()
        eligibility = run("busctl", "call", "org.freedesktop.login1", "/org/freedesktop/login1",
                          "org.freedesktop.login1.Manager", "CanHibernate")
        ready = eligibility in ('s "yes"', 's "challenge"')
        LOG.event("Preparation complete" if ready else "STOP: preparation exists, but hibernation is not currently available",
                  can_hibernate=eligibility, prepared=ready)
        print(f"\nReport and recovery guidance: {LOG.path}\nCanHibernate: {eligibility}")
        print("No sleep test was run. Hibernation and hardware restoration remain UNTESTED.")
        return 0 if ready else 2
    finally:
        if mounted or os.path.ismount(top):
            try:
                run("umount", str(top))
                LOG.event("Temporary top-level mount released")
            except Exception as error:
                LOG.event(f"Temporary mount needs manual release: {error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="read-only preflight (the default)")
    group.add_argument("--apply", action="store_true", help="validate, archive unused boot files, and prepare disk hibernation")
    group.add_argument("--status", action="store_true", help="show present swap, sleep configuration, and eligibility without changes")
    args = parser.parse_args()
    try:
        if args.status:
            print(json.dumps(swaps(), indent=2))
            print(run("systemd-analyze", "--no-pager", "cat-config", "systemd/sleep.conf"))
            print(run("busctl", "call", "org.freedesktop.login1", "/org/freedesktop/login1",
                      "org.freedesktop.login1.Manager", "CanHibernate"))
            return 0
        print("Read-only preflight; no hibernation/resume hardware test has been performed.")
        plan = check()
        print(f"Preflight passed. Current initramfs contains applespi: {plan['applespi_in_initramfs']}")
        if not args.apply:
            print("No files or mounts changed. --apply prepares the separate manual test without triggering sleep.")
            return 0
        return apply(plan)
    except (Exception, KeyboardInterrupt) as error:
        print(f"\nSTOP: {error}", file=sys.stderr)
        if LOG:
            try:
                LOG.event(f"STOPPED: {error}", prepared=False, error=str(error))
            except Exception:
                pass
            print(f"Partial preparation may exist. Review {LOG.path}/state.json and RECOVERY.txt.\n"
                  "Do not remove active swap or retry blindly. No sleep was triggered.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
