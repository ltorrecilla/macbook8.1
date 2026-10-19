# SPDX-License-Identifier: MIT
"""Simulated workflow tests. No real DKMS, network, module, or boot-image operations."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "repair_audio", Path(__file__).parents[1] / "scripts/repair-audio.py")
audio = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audio
SPEC.loader.exec_module(audio)

OLD = "7.2.9-2-cachyos"
NEW = "7.2.11-1-cachyos"
LTS = "6.18.55-2-cachyos-lts"


class FakeRecovery(audio.Recovery):
    def __init__(self, root):
        super().__init__(root)
        self.calls = []
        self.owners = {}
        self.states = {}
        self.missing_tools = set()
        self.network_fails = False
        self.build_fails = None
        self.boot_fails = False
        self.clang_major = 23
        self.extra_status = ""

    def say(self, message):
        pass

    def require(self, *names):
        if self.missing_tools.intersection(names):
            raise audio.Stop("Missing tool")

    def start_log(self):
        self.logdir = self.root / "logs"
        self.logdir.mkdir(exist_ok=True)

    def run(self, args, *, env=None, check=True):
        self.calls.append((args, env))
        if args[:2] == ["pacman", "-Qqo"]:
            return self.owners.get(args[2], "")
        if args == ["dkms", "status"]:
            return self.extra_status + "\n".join(
                f"macbook12-audio/0.1, {version}, x86_64: {state} (Original modules exist)"
                for version, state in self.states.items())
        if args[0] == "modinfo":
            if args[1] == "-k":
                file = self.path(f"usr/lib/modules/{args[2]}/updates/dkms/{args[4]}.ko")
                return str(file) if file.exists() else ""
            version = Path(args[3]).parts[-4]
            return version + " SMP preempt mod_unload modversions"
        if args[0] == "clang":
            return f"clang version {self.clang_major}.1.1"
        if args[0] == "wget":
            if self.network_fails:
                raise audio.Stop("Network is unreachable")
            return "200 OK Remote file exists"
        if args[:2] == ["dkms", "install"]:
            version = args[-1]
            if version == self.build_fails:
                raise audio.Stop("Build failed")
            self.states[version] = "installed"
            self.modules(version)
            return "installed"
        if args == ["limine-mkinitcpio"]:
            if self.boot_fails:
                raise audio.Stop("Boot image generation failed")
            return "success"
        raise AssertionError(f"Unexpected command: {args}")

    def modules(self, version):
        for name in audio.MODULES:
            path = self.path(f"usr/lib/modules/{version}/updates/dkms/{name}.ko")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fake module -- not loadable")

    def add_kernel(self, version, package="linux-cachyos", installed=False, clang=True):
        directory = self.path(f"usr/lib/modules/{version}")
        (directory / "build/include/config").mkdir(parents=True)
        (directory / "pkgbase").write_text(package)
        (directory / "vmlinuz").write_text("fake kernel image")
        self.owners[str(directory / "vmlinuz")] = package
        (directory / "build/Makefile").write_text("fake")
        (directory / "build/Module.symvers").write_text("fake")
        (directory / "build/include/config/kernel.release").write_text(version)
        config = "CONFIG_CC_IS_CLANG=y\nCONFIG_CLANG_VERSION=230101\n" if clang else "CONFIG_CC_IS_GCC=y\n"
        (directory / "build/.config").write_text(config)
        if installed:
            self.states[version] = "installed"
            self.modules(version)
        return directory


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.r = FakeRecovery(self.root)
        for relative, text in (
            ("sys/class/dmi/id/product_name", "MacBook8,1"),
            ("etc/os-release", 'ID=cachyos\n'),
            ("var/lib/dkms/macbook12-audio/0.1/source/dkms.conf",
             'PACKAGE_NAME="macbook12-audio"\nPACKAGE_VERSION="0.1"\n' +
             "\n".join(f'BUILT_MODULE_NAME[{i}]="{name}"' for i, name in enumerate(audio.MODULES))),
            ("var/lib/dkms/macbook12-audio/0.1/source/dkms_build.sh", "#!/bin/bash\n"),
            ("home/luis/.config/pipewire/pipewire.conf.d/51-macbook81-speaker.conf", "user EQ"),
            ("etc/udev/rules.d/91-mb81-no-spdif-share.rules", "user mixer rule"),
        ):
            file = self.root / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)
        self.addCleanup(patch.stopall)
        patch.object(audio.platform, "machine", return_value="x86_64").start()
        patch.object(audio.platform, "release", return_value=OLD).start()
        patch.object(audio.os, "geteuid", return_value=0).start()

    def execute(self, **kwargs):
        return self.r.execute(repair=kwargs.pop("repair", True), **kwargs)

    def build_calls(self):
        return [(a, e) for a, e in self.r.calls if a[:2] == ["dkms", "install"]]

    def test_default_check_discovers_new_installed_kernel_not_running(self):
        self.r.add_kernel(NEW)
        self.assertEqual(self.execute(repair=False), 2)
        self.assertEqual(self.build_calls(), [])
        self.assertFalse(any(a[0] in ("wget", "limine-mkinitcpio") for a, _ in self.r.calls))
        self.assertFalse((self.root / "logs").exists())

    def test_healthy_check_is_read_only(self):
        self.r.add_kernel(NEW, installed=True)
        self.assertEqual(self.execute(repair=False), 0)
        self.assertFalse((self.root / "logs").exists())

    def test_new_kernel_repair_leaves_lts_installed_and_settings_untouched(self):
        self.r.add_kernel(LTS, "linux-cachyos-lts", installed=True)
        self.r.add_kernel(NEW)
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file() and
                  (".config" in p.parts or "udev" in p.parts)}
        self.assertEqual(self.execute(), 0)
        self.assertEqual([a[-1] for a, _ in self.build_calls()], [NEW])
        self.assertEqual(self.r.states[LTS], "installed")
        self.assertTrue(all(p.read_bytes() == data for p, data in before.items()))
        self.assertEqual(self.r.calls[-1][0], ["limine-mkinitcpio"])
        self.assertNotIn("--force", self.build_calls()[0][0])
        self.assertEqual(self.build_calls()[0][1]["LLVM"], "1")

    def test_missing_header_stops_before_network_build_or_boot(self):
        directory = self.r.add_kernel(NEW)
        (directory / "build/Makefile").unlink()
        with self.assertRaises(audio.Stop):
            self.execute()
        self.assertFalse(any(a[0] in ("wget", "limine-mkinitcpio") for a, _ in self.r.calls))
        self.assertEqual(self.build_calls(), [])

    def test_header_version_mismatch_stops(self):
        directory = self.r.add_kernel(NEW)
        (directory / "build/include/config/kernel.release").write_text(OLD)
        with self.assertRaises(audio.Stop):
            self.execute()
        self.assertEqual(self.build_calls(), [])

    def test_network_failure_stops_before_dkms_install(self):
        self.r.add_kernel(NEW)
        self.r.network_fails = True
        with self.assertRaisesRegex(audio.Stop, "Network"):
            self.execute()
        self.assertEqual(self.build_calls(), [])
        self.assertFalse(any(a == ["limine-mkinitcpio"] for a, _ in self.r.calls))

    def test_build_failure_never_regenerates_boot_images(self):
        self.r.add_kernel(NEW)
        self.r.build_fails = NEW
        with self.assertRaisesRegex(audio.Stop, "Build failed"):
            self.execute()
        self.assertFalse(any(a == ["limine-mkinitcpio"] for a, _ in self.r.calls))

    def test_all_headers_preflighted_before_any_build(self):
        self.r.add_kernel(NEW)
        broken = self.r.add_kernel(LTS, "linux-cachyos-lts")
        (broken / "build/Module.symvers").unlink()
        with self.assertRaises(audio.Stop):
            self.execute()
        self.assertEqual(self.build_calls(), [])

    def test_gcc_kernel_does_not_inherit_llvm(self):
        self.r.add_kernel(LTS, "linux-cachyos-lts", clang=False)
        with patch.dict(os.environ, {"LLVM": "1", "CC": "clang", "MAKEFLAGS": "-bad"}):
            self.execute()
        env = self.build_calls()[0][1]
        self.assertEqual(env["CC"], "gcc")
        self.assertNotIn("LLVM", env)
        self.assertNotIn("MAKEFLAGS", env)

    def test_clang_major_mismatch_stops(self):
        self.r.add_kernel(NEW)
        self.r.clang_major = 22
        with self.assertRaisesRegex(audio.Stop, "Clang major"):
            self.execute()
        self.assertEqual(self.build_calls(), [])

    def test_wrong_hardware_stops(self):
        self.r.path("sys/class/dmi/id/product_name").write_text("MacBook9,1")
        with self.assertRaisesRegex(audio.Stop, "restricted"):
            self.execute()
        self.assertEqual(self.r.calls, [])

    def test_wrong_distribution_stops(self):
        self.r.path("etc/os-release").write_text("ID=ubuntu\n")
        with self.assertRaisesRegex(audio.Stop, "CachyOS"):
            self.execute()

    def test_active_pacman_lock_stops_without_deleting_it(self):
        file = self.r.path("var/lib/pacman/db.lck")
        file.parent.mkdir(parents=True)
        file.touch()
        with self.assertRaisesRegex(audio.Stop, "lock"):
            self.execute()
        self.assertTrue(file.exists())
        self.assertEqual(self.r.calls, [])

    def test_stale_kernel_directory_ignored(self):
        directory = self.r.add_kernel(OLD, installed=True)
        (directory / "vmlinuz").unlink()
        self.r.add_kernel(NEW)
        self.execute()
        self.assertEqual([a[-1] for a, _ in self.build_calls()], [NEW])

    def test_unowned_kernel_image_rejected(self):
        self.r.add_kernel(NEW)
        self.r.owners.clear()
        with self.assertRaisesRegex(audio.Stop, "ownership"):
            self.execute()

    def test_wrong_module_paths_not_force_replaced(self):
        directory = self.r.add_kernel(NEW, installed=True)
        (directory / f"updates/dkms/{audio.MODULES[0]}.ko").unlink()
        with self.assertRaisesRegex(audio.Stop, "No forced"):
            self.execute()
        self.assertEqual(self.build_calls(), [])

    def test_conflicting_driver_package_stops(self):
        self.r.add_kernel(NEW)
        self.r.extra_status = "macbook12-audio-driver/0.1: added\n"
        with self.assertRaisesRegex(audio.Stop, "overlap"):
            self.execute()

    def test_wrong_source_module_count_stops(self):
        self.r.add_kernel(NEW)
        file = self.r.path("var/lib/dkms/macbook12-audio/0.1/source/dkms.conf")
        file.write_text('BUILT_MODULE_NAME[0]="snd-hda-codec-cs420x"\n')
        with self.assertRaisesRegex(audio.Stop, "three-module"):
            self.execute()
        self.assertEqual(self.build_calls(), [])

    def test_explicit_kernel_selects_only_requested_target(self):
        self.r.add_kernel(NEW)
        self.r.add_kernel(LTS, "linux-cachyos-lts")
        self.execute(selected=NEW)
        self.assertEqual([a[-1] for a, _ in self.build_calls()], [NEW])

    def test_exact_archive_url_no_minor_version_fallback(self):
        self.r.add_kernel(NEW)
        self.execute()
        urls = [a[-1] for a, _ in self.r.calls if a[0] == "wget"]
        self.assertEqual(urls, ["https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.2.11.tar.xz"])

    def test_already_installed_repair_refreshes_boot_without_rebuilding(self):
        self.r.add_kernel(NEW, installed=True)
        self.r.missing_tools.add("wget")
        self.execute()
        self.assertEqual(self.build_calls(), [])
        self.assertEqual(self.r.calls[-1][0], ["limine-mkinitcpio"])

    def test_boot_failure_is_not_reported_success(self):
        self.r.add_kernel(NEW, installed=True)
        self.r.boot_fails = True
        with self.assertRaisesRegex(audio.Stop, "Boot image"):
            self.execute()

    def test_missing_limine_tool_stops_before_build(self):
        self.r.add_kernel(NEW)
        self.r.missing_tools.add("limine-mkinitcpio")
        with self.assertRaises(audio.Stop):
            self.execute()
        self.assertEqual(self.build_calls(), [])

    def test_repair_requires_root(self):
        with patch.object(audio.os, "geteuid", return_value=1000):
            with self.assertRaisesRegex(audio.Stop, "sudo"):
                self.execute()

    def test_invalid_kernel_argument_rejected(self):
        with self.assertRaisesRegex(audio.Stop, "Invalid"):
            self.r.kernels("../../oops")

    def test_release_candidate_rejected_without_source_substitution(self):
        for version in ("7.3-rc1-cachyos", "7.3.0-rc1-1-cachyos"):
            with self.subTest(version=version):
                with self.assertRaisesRegex(audio.Stop, "Unsupported"):
                    _ = audio.Kernel(version, "linux-cachyos", self.root).url

    def test_archive_failure_retains_log(self):
        self.r.add_kernel(NEW)
        self.r.build_fails = NEW
        log = self.r.path("var/lib/dkms/macbook12-audio/0.1/build/make.log")
        log.parent.mkdir(parents=True)
        log.write_text("Network is unreachable\napt-get: command not found\n")
        with self.assertRaises(audio.Stop):
            self.execute()
        self.assertEqual((self.root / "logs" / f"make-{NEW}.log").read_text(), log.read_text())

    def test_subprocess_uses_predictable_locale_without_mutating_environment(self):
        runner = audio.Recovery(self.root)
        with patch.object(runner, "say"), patch.object(audio.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess(["dkms", "status"], 0, "installed")
            environment = {"LC_ALL": "de_CH.UTF-8", "CC": "clang"}
            self.assertEqual(runner.run(["dkms", "status"], env=environment), "installed")
            self.assertEqual(run.call_args.kwargs["env"]["LC_ALL"], "C")
            self.assertEqual(environment["LC_ALL"], "de_CH.UTF-8")


if __name__ == "__main__":
    unittest.main()
