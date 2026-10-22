#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only MacBook8,1 pre-reboot kernel compatibility report (no root needed)."""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path("/")
MODULES = ("snd-hda-codec-cs420x", "snd-hda-codec-generic", "snd-hda-intel")
PATTERN = re.compile(r"__initstub__kmod_dw_dmac_pci__\d+_\d+_dw_pci_driver_init\d+")

def command(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True, check=False).stdout
    except OSError:
        return ""

def read(path):
    try:
        return pathlib.Path(path).read_text(errors="replace")
    except OSError:
        return ""

def main():
    if read("/sys/class/dmi/id/product_name").strip() != "MacBook8,1":
        print("STOP: This check is only for MacBook8,1.")
        return 2
    running = command("uname", "-r").strip()
    cmdline = read("/proc/cmdline")
    limine = read("/etc/default/limine")
    print("Running:", running)
    kernels = []
    for folder in sorted(pathlib.Path("/usr/lib/modules").glob("*")):
        if (folder / "vmlinuz").is_file() and (folder / "pkgbase").is_file():
            pkg = read(folder / "pkgbase").strip()
            if pkg.startswith("linux-cachyos"):
                kernels.append(folder)
    if not kernels:
        print("STOP: No installed CachyOS kernel images found")
        return 2
    warnings = 0
    for folder in kernels:
        version = folder.name
        print("\nKernel:", version)
        missing = []
        for module in MODULES:
            location = command("modinfo", "-k", version, "-n", module).strip()
            if "/updates/dkms/" not in location or not pathlib.Path(location).is_file():
                missing.append(module)
        if missing:
            warnings += 1
            print("  AUDIO NOT READY: missing patched modules:", ", ".join(missing))
        else:
            print("  AUDIO ON DISK: patched module paths exist (not a live playback test)")
        # /proc/kallsyms applies ONLY to the running kernel, not a future kernel.
        symbols = set()
        if version == running:
            symbols = set(PATTERN.findall(read("/proc/kallsyms")))
        else:
            for name in (folder / "build/System.map", pathlib.Path("/boot") / ("System.map-" + version)):
                if name.is_file():
                    symbols = set(PATTERN.findall(read(name)))
                    break
        if not symbols:
            warnings += 1
            print("  SPI UNVERIFIED: no usable initcall symbols; do NOT assume this kernel is safe")
        elif not any(symbol in limine for symbol in symbols):
            warnings += 1
            print("  SPI NOT READY: matching DMA initcall symbol missing in /etc/default/limine")
            for symbol in sorted(symbols):
                print("    candidate:", symbol)
            print("  Review before editing: symbols are kernel-build-specific")
        elif version == running and not any(symbol in cmdline for symbol in symbols):
            warnings += 1
            print("  SPI NOT ACTIVE: persistent config has symbol but running cmdline does not")
        else:
            print("  SPI CONFIGURED: matching symbol found; functional boot test still required")
    # Optional experimental D+ service is a separate user-session concern.
    # A disabled unit is not a kernel compatibility failure.
    print("\\nD+ service (optional, user session):")
    if "SUDO_UID" in __import__("os").environ:
        print("  UNCHECKED: run as the desktop user without sudo")
    else:
        enabled = command("systemctl", "--user", "is-enabled", "macbook81-dplus.service").strip()
        active = command("systemctl", "--user", "is-active", "macbook81-dplus.service").strip()
        print("  Enabled:", enabled or "unknown")
        print("  Active:", active or "unknown")
        print("  NOTE: good Raw playback does not prove D+ processing; prior A/V-sync delay remains open")
    print("\nResult:", "REVIEW REQUIRED; do not reboot into unchecked new kernel" if warnings else
          "No detected blockers; this does not prove hardware will work after reboot")
    return 2 if warnings else 0

if __name__ == "__main__":
    sys.exit(main())
