#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check/recover an EXISTING MacBook8,1 macbook12-audio/0.1 installation.

Read-only by default. --repair requires root, uses the registered driver source,
does not install prerequisites or reload hardware/change user audio settings.
See docs/audio-update-recovery.md. This is not a fresh-install audio installer.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

PACKAGE = "macbook12-audio"
VERSION = "0.1"
MODULES = ("snd-hda-codec-cs420x", "snd-hda-codec-generic", "snd-hda-intel")
# Stable CachyOS kernels only; do not silently substitute a release for an RC.
KERNEL_RE = re.compile(r"(?P<release>\d+\.\d+(?:\.\d+)?)-[A-Za-z0-9_.+\-]+")


class Stop(RuntimeError):
    pass


@dataclass(frozen=True)
class Kernel:
    version: str
    package: str
    directory: Path

    @property
    def url(self) -> str:
        match = KERNEL_RE.fullmatch(self.version)
        if not match:
            raise Stop(f"Unsupported kernel release: {self.version}")
        release = match.group("release")
        major = release.split(".")[0]
        return f"https://cdn.kernel.org/pub/linux/kernel/v{major}.x/linux-{release}.tar.xz"


class Recovery:
    def __init__(self, root: Path = Path("/")) -> None:
        # Alternate root is for imported tests only; not exposed through the CLI.
        self.root = root
        self.log = None
        self.logdir = None

    def path(self, relative: str) -> Path:
        return self.root / relative.lstrip("/")

    def say(self, message: str) -> None:
        print(message, flush=True)
        if self.log:
            self.log.write(message + "\n")
            self.log.flush()

    def run(self, args: list[str], *, env=None, check=True) -> str:
        self.say("+ " + shlex.join(args))
        result = subprocess.run(args, env=env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False)
        if self.log:
            self.log.write(result.stdout)
            self.log.flush()
        if check and result.returncode:
            raise Stop(f"Command failed ({result.returncode}): {shlex.join(args)}\n"
                       + result.stdout[-8000:])
        return result.stdout if result.returncode == 0 else ""

    def require(self, *names: str) -> None:
        missing = [name for name in names if not shutil.which(name)]
        if missing:
            raise Stop("Required existing tools missing: " + ", ".join(missing)
                       + ". Nothing will be installed automatically.")

    def host(self) -> None:
        model = self.path("sys/class/dmi/id/product_name").read_text().strip()
        if model != "MacBook8,1" or platform.machine() != "x86_64":
            raise Stop("This helper is restricted to MacBook8,1 on x86_64.")
        release = self.path("etc/os-release").read_text()
        if not re.search(r'^ID=[\"\']?cachyos[\"\']?$', release, re.M):
            raise Stop("This helper is restricted to CachyOS.")
        self.require("pacman", "dkms", "modinfo")

    def kernels(self, selected: str | None) -> list[Kernel]:
        if selected and not KERNEL_RE.fullmatch(selected):
            raise Stop("Invalid/unsupported --kernel; use an exact stable kernel release.")
        found = []
        for directory in sorted(self.path("usr/lib/modules").iterdir()):
            if selected and directory.name != selected:
                continue
            base = directory / "pkgbase"
            image = directory / "vmlinuz"
            if not base.is_file() or not image.is_file():
                continue  # Ignore stale DKMS-only directories from removed kernels.
            name = base.read_text().strip()
            if not re.fullmatch(r"linux-cachyos(?:-[a-z0-9-]+)?", name):
                continue
            if not KERNEL_RE.fullmatch(directory.name):
                raise Stop(f"Unsupported installed kernel: {directory.name}")
            # A directory name alone is not evidence that its kernel is installed.
            owner = self.run(["pacman", "-Qqo", str(image)], check=False).strip()
            if owner != name:
                raise Stop(f"Cannot verify package ownership of {image}; stop for review.")
            found.append(Kernel(directory.name, name, directory))
        if not found:
            raise Stop("No matching package-owned CachyOS kernel image found. "
                       "Do not build against a stale/running-but-removed kernel.")
        return found

    def status(self) -> str:
        text = self.run(["dkms", "status"])
        if "macbook12-audio-driver/" in text:
            raise Stop("Another MacBook audio DKMS package is present; resolve overlap first.")
        return text

    @staticmethod
    def installed(status: str, version: str) -> bool:
        pattern = (rf"^{re.escape(PACKAGE)}/{re.escape(VERSION)},\s*"
                   rf"{re.escape(version)},\s*x86_64:\s*installed(?:\s|$)")
        return bool(re.search(pattern, status, re.M))

    def module_problem(self, kernel: Kernel) -> str:
        expected = (kernel.directory / "updates/dkms").resolve()
        for name in MODULES:
            value = self.run(["modinfo", "-k", kernel.version, "-n", name],
                             check=False).strip()
            file = Path(value) if value else None
            if not file or not file.is_file() or file.resolve().parent != expected:
                return f"{name} does not resolve to a file under {expected}"
            magic = self.run(["modinfo", "-F", "vermagic", str(file)], check=False).split()
            if not magic or magic[0] != kernel.version:
                return f"Wrong/missing vermagic for {name} on {kernel.version}"
        return ""

    def source(self) -> None:
        folder = self.path(f"var/lib/dkms/{PACKAGE}/{VERSION}/source")
        config = (folder / "dkms.conf").read_text()
        names = re.findall(r'^BUILT_MODULE_NAME\[\d+\]\s*=\s*"([^"]+)"', config, re.M)
        if len(names) != 3 or set(names) != set(MODULES):
            raise Stop("Registered source is not the expected three-module audio package.")
        for key, value in (("PACKAGE_NAME", PACKAGE), ("PACKAGE_VERSION", VERSION)):
            if not re.search(rf'^{key}\s*=\s*"{re.escape(value)}"\s*$', config, re.M):
                raise Stop("Unexpected DKMS source identity; no fresh installation attempted.")
        if not (folder / "dkms_build.sh").is_file():
            raise Stop("Registered dkms_build.sh is missing; preserve the source checkout.")
        self.say(f"Using already-registered source: {folder.resolve()}")

    def toolchain(self, kernel: Kernel) -> dict[str, str]:
        build = kernel.directory / "build"
        if not (build / "Makefile").is_file() or not (build / "Module.symvers").is_file():
            raise Stop(f"Missing prepared headers/symbols for {kernel.version}. "
                       f"Check {kernel.package}-headers; no package installation attempted.")
        release = (build / "include/config/kernel.release").read_text().strip()
        if release != kernel.version:
            raise Stop(f"Header mismatch: {kernel.version} versus {release}")
        config = (build / ".config").read_text()
        # Do not inherit desktop compiler overrides or stale GNU make flags.
        env = os.environ.copy()
        for key in ("LLVM", "LLVM_IAS", "CC", "LD", "AR", "NM", "STRIP", "OBJCOPY",
                    "OBJDUMP", "READELF", "HOSTCC", "HOSTCXX", "HOSTAR", "HOSTLD",
                    "CROSS_COMPILE", "ARCH", "MAKEFLAGS", "MFLAGS", "KERNELRELEASE"):
            env.pop(key, None)
        env["LC_ALL"] = "C"
        if re.search(r"^CONFIG_CC_IS_CLANG=y$", config, re.M):
            self.require("clang", "clang++", "ld.lld", "llvm-ar", "llvm-nm", "llvm-strip",
                         "llvm-objcopy", "llvm-objdump", "llvm-readelf")
            actual = self.run(["clang", "--version"])
            expected = re.search(r'^CONFIG_CLANG_VERSION=(\d+)$', config, re.M)
            major = re.search(r"clang version (\d+)", actual)
            if expected and major and int(expected[1]) // 10000 != int(major[1]):
                raise Stop(f"Clang major version differs from headers for {kernel.version}.")
            env.update(LLVM="1", CC="clang", LD="ld.lld")
            self.say(f"{kernel.version}: selecting Clang/LLVM")
        elif re.search(r"^CONFIG_CC_IS_GCC=y$", config, re.M):
            self.require("gcc", "ld")
            env.update(CC="gcc", LD="ld")
            self.say(f"{kernel.version}: selecting GCC")
        else:
            raise Stop(f"Unrecognized compiler configuration for {kernel.version}")
        return env

    def start_log(self) -> None:
        parent = self.path("var/log/macbook81-audio-recovery")
        if parent.exists() and (parent.is_symlink() or parent.stat().st_uid != 0
                                or parent.stat().st_mode & 0o022):
            raise Stop(f"Unsafe recovery log directory: {parent}")
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-")
        self.logdir = Path(tempfile.mkdtemp(prefix=stamp, dir=parent))
        self.log = (self.logdir / "session.log").open("x", encoding="utf-8")
        self.say(f"Recovery log: {self.logdir / 'session.log'}")

    def archive_failure(self, kernel: Kernel) -> None:
        source = self.path(f"var/lib/dkms/{PACKAGE}/{VERSION}/build/make.log")
        if self.logdir and source.is_file():
            target = self.logdir / f"make-{kernel.version}.log"
            shutil.copyfile(source, target)
            self.say(f"Preserved build log: {target}")
            ending = source.read_text(errors="replace")[-16000:]
            if "Network is unreachable" in ending or "apt-get: command not found" in ending:
                self.say("Source-download failure or Ubuntu fallback. Do not install apt-get. "
                         "A successful precheck does not guarantee network access inside DKMS.")

    def execute(self, *, repair: bool, selected: str | None = None) -> int:
        self.host()
        if repair:
            if os.geteuid() != 0:
                raise Stop("Use sudo for --repair. --check needs no sudo.")
            if self.path("var/lib/pacman/db.lck").exists():
                raise Stop("Package-manager lock exists. Finish the update first; do not delete it.")
        kernels = self.kernels(selected)
        self.say("Running kernel: " + platform.release())
        self.say("Selected INSTALLED kernels: " + ", ".join(k.version for k in kernels))
        status = self.status()
        pending = []
        inconsistent = []
        for kernel in kernels:
            if not self.installed(status, kernel.version):
                pending.append(kernel)
                self.say(f"NEEDS BUILD: {kernel.version}")
            else:
                problem = self.module_problem(kernel)
                if problem:
                    inconsistent.append(f"{kernel.version}: {problem}")
                else:
                    self.say(f"ON-DISK MODULES OK: {kernel.version}")
        if inconsistent:
            raise Stop("DKMS reports installed but files disagree. No forced replacement.\n"
                       + "\n".join(inconsistent))
        if not repair:
            if pending:
                self.say("No changes made. After the update, connect to the internet and run "
                         "this script with sudo and --repair.")
                return 2
            self.say("No changes made. On-disk checks do not prove live playback or boot-image contents.")
            return 0
        self.require("limine-mkinitcpio")
        environments = {}
        if pending:
            self.require("wget", "make", "bash", "tar")
            self.source()
            # Validate ALL target headers/tools before modifying ANY module installation.
            for kernel in pending:
                environments[kernel.version] = self.toolchain(kernel)
        self.start_log()
        # Exact source checks only; do not fall back to a different kernel's archive.
        for kernel in pending:
            self.run(["wget", "--spider", "--timeout=20", "--tries=1", kernel.url])
        for kernel in pending:
            self.say(f"Building {PACKAGE}/{VERSION} for {kernel.version}; no other DKMS package targeted.")
            try:
                self.run(["dkms", "install", "-m", PACKAGE, "-v", VERSION, "-k", kernel.version],
                         env=environments[kernel.version])
            except Stop:
                self.archive_failure(kernel)
                raise
            if not self.installed(self.status(), kernel.version):
                raise Stop(f"DKMS did not confirm installed for {kernel.version}")
            problem = self.module_problem(kernel)
            if problem:
                raise Stop(problem)
        # Also refresh when already installed: a prior interrupted run may have
        # installed modules but failed before completing the boot-image step.
        self.run(["limine-mkinitcpio"])
        self.say("ON-DISK REPAIR COMPLETE. No services restarted, no audio settings changed, no reboot initiated.")
        self.say("Save work and shut down normally, then boot the checked kernel. Verify CS4208 Speaker "
                 "(PCH device 2), IEC958 sharing off, and playback through MacBook_Speaker_Raw.")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="read-only on-disk check (default)")
    modes.add_argument("--repair", action="store_true", help="rebuild missing audio modules and boot images")
    parser.add_argument("--kernel", help="one exact installed kernel; default: all installed CachyOS kernels")
    args = parser.parse_args(argv)
    recovery = Recovery()
    try:
        return recovery.execute(repair=args.repair, selected=args.kernel)
    except (Stop, OSError, subprocess.SubprocessError) as error:
        recovery.say(f"STOP: {error}")
        recovery.say("No automatic rollback or reboot. Keep existing kernels/source; do not rerun the legacy installer.")
        return 1
    except KeyboardInterrupt:
        recovery.say("Interrupted. Do not assume the build or boot images completed; rerun after checking the logs.")
        return 130
    finally:
        if recovery.log:
            recovery.log.close()


if __name__ == "__main__":
    sys.exit(main())
