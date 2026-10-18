#!/usr/bin/env python3
"""Exercise camera installer guards and ownership without root or hardware.

The real shell scripts run against a temporary filesystem. Network, package,
module and privilege commands are PATH shims; ordinary file operations remain
real. Only the effective-UID guards and fixture paths/hashes are overridden.
This tests installer behavior, not a kernel build or live camera capture.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
FIRMWARE = b"test firmware, not an Apple firmware binary\n"
CALIBRATION = b"test sensor calibration\n"

# Every command that could access hardware, gain privilege or download content
# is intercepted. The sudo shim does not elevate and only accepts file paths
# within this test's temporary directory.
SHIM = r'''
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

name = Path(sys.argv[0]).name
args = sys.argv[1:]
root = Path(os.environ["CAMERA_TEST_ROOT"])
mode = os.environ.get("CAMERA_TEST_MODE", "")
with (root / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps([name, *args]) + "\n")
source = root / "usr/src/facetimehd-0.7.0.1"
dkms = root / "var/lib/dkms/facetimehd"
version = dkms / "0.7.0.1"
loaded = root / "sys/module/facetimehd"
available = root / "module-available"

def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)

if name == "sudo":
    if args == ["-v"]:
        sys.exit(0)
    if not args or args[0] not in {"mktemp", "cp", "chmod", "mv", "install", "dkms", "modprobe", "rm"}:
        fail("test blocked unexpected sudo command")
    if args[0] not in {"dkms", "modprobe"}:
        for item in args[1:]:
            if item.startswith("/") and not Path(item).resolve().is_relative_to(root):
                fail("test blocked file operation outside fixture")
    sys.exit(subprocess.run(args, check=False).returncode)
elif name == "stat":
    # Model root ownership inside the fixture, even on ordinary-user CI.
    if args[:2] == ["-c", "%u"] and Path(args[-1]).resolve().is_relative_to(root):
        print("0")
    else:
        fail("test blocked stat outside fixture")
elif name == "modinfo":
    if not available.exists():
        sys.exit(1)
    print("filename: fixture/facetimehd.ko")
elif name == "modprobe":
    if args == ["-r", "facetimehd"]:
        if mode == "busy":
            fail("facetimehd is in use")
        if loaded.exists():
            loaded.rmdir()
    elif args == ["facetimehd"]:
        loaded.mkdir(parents=True, exist_ok=True)
    else:
        fail("unexpected module operation")
elif name == "dkms":
    if args[0] == "add":
        version.mkdir(parents=True)
        (version / "source").symlink_to(source, target_is_directory=True)
    elif args[0] == "status":
        if (version / "installed").exists():
            print("facetimehd/0.7.0.1, fixture-kernel, x86_64: installed")
        elif version.exists():
            print("facetimehd/0.7.0.1: added")
    elif args[0] == "install":
        if mode == "build-failure":
            fail("fixture build failed")
        (version / "installed").write_text("installed\n")
        available.touch()
    elif args[0] == "remove":
        shutil.rmtree(version)
        if not any(dkms.iterdir()):
            dkms.rmdir()
        available.unlink(missing_ok=True)
    else:
        fail("unexpected DKMS operation")
elif name == "git":
    if args[:2] == ["init", "--quiet"]:
        Path(args[2]).mkdir()
        sys.exit(0)
    if args[0] != "-C":
        fail("unexpected git operation")
    dest = Path(args[1])
    operation = args[2]
    kind = dest.name
    if operation == "fetch":
        if mode == "fetch-failure":
            fail("fixture download failed")
        (dest / "head").write_text(args[-1])
    elif operation == "checkout":
        pass
    elif operation == "rev-parse":
        print("wrong-commit" if mode == "wrong-pin-" + kind else (dest / "head").read_text())
    elif operation == "archive":
        with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as archive:
            for path in sorted((root / "driver-fixture").iterdir()):
                data = path.read_bytes()
                if path.name == "dkms.conf" and mode == "wrong-dkms-version":
                    data = data.replace(b"0.7.0.1", b"unexpected")
                info = tarfile.TarInfo(path.name)
                info.mode = 0o644
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
    else:
        fail("unexpected git operation")
elif name == "make":
    if mode == "extraction-failure":
        fail("fixture firmware extraction failed")
    if len(args) != 3 or args[0] != "-C" or args[2] != "FW_VER=5.60.0":
        fail("unexpected firmware extraction command")
    dest = Path(args[1])
    for filename in ("firmware.bin", "1675_01XX.dat"):
        data = (root / "firmware-fixture" / filename).read_bytes()
        if mode == "bad-hash-" + filename:
            data += b"corrupted"
        (dest / filename).write_bytes(data)
elif name == "fuser":
    sys.exit(1)
elif name in {"lspci", "pacman", "v4l2-ctl", "wpctl"}:
    print("fixture diagnostic output")
elif name == "which":
    sys.exit(0)
else:
    fail("test blocked unexpected network or service command: " + name)
'''


class CameraScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="camera-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "usr/src/facetimehd-0.7.0.1"
        self.fw = self.root / "usr/lib/firmware/facetimehd"
        self.dkms = self.root / "var/lib/dkms/facetimehd"
        self.headers = self.root / "headers"
        self.loaded = self.root / "sys/module/facetimehd"
        self.video = self.root / "sys/class/video4linux"
        self.dev = self.root / "dev"
        self.log = self.root / "calls.jsonl"
        self.bin = self.root / "bin"
        for path in (self.bin, self.src.parent, self.headers / "include/config",
                     self.root / "work", self.dev, self.video,
                     self.root / "pci/0000:02:00.0", self.root / "driver-fixture",
                     self.root / "firmware-fixture"):
            path.mkdir(parents=True, exist_ok=True)
        (self.root / "model").write_text("MacBook8,1\n")
        (self.root / "arch-release").touch()
        (self.root / "pci/0000:02:00.0/vendor").write_text("0x14e4\n")
        (self.root / "pci/0000:02:00.0/device").write_text("0x1570\n")
        (self.headers / "Makefile").touch()
        (self.headers / "include/config/kernel.release").write_text("fixture-kernel\n")
        (self.root / "driver-fixture/dkms.conf").write_text(
            "PACKAGE_NAME=facetimehd\nPACKAGE_VERSION=0.7.0.1\n")
        (self.root / "driver-fixture/driver.c").write_text("/* fixture source */\n")
        (self.root / "firmware-fixture/firmware.bin").write_bytes(FIRMWARE)
        (self.root / "firmware-fixture/1675_01XX.dat").write_bytes(CALIBRATION)
        shim = self.bin / "command-shim"
        shim.write_text(f"#!{sys.executable}\n" + textwrap.dedent(SHIM))
        shim.chmod(0o755)
        for name in ("sudo", "dkms", "modprobe", "modinfo", "git", "make", "stat",
                     "curl", "wget", "ssh", "systemctl", "pacman", "lspci",
                     "v4l2-ctl", "wpctl", "fuser", "which"):
            (self.bin / name).symlink_to(shim)
        self.env = dict(os.environ, PATH=f"{self.bin}:/usr/bin:/bin",
                        TMPDIR=str(self.root / "work"), CAMERA_TEST_ROOT=str(self.root))
        self.paths = {
            "CAM_KERNEL": "fixture-kernel", "CAM_SRC_PARENT": self.src.parent,
            "CAM_SRC_DIR": self.src, "CAM_DKMS_DIR": self.dkms, "CAM_FW_DIR": self.fw,
            "CAM_HEADERS_DIR": self.headers, "CAM_DMI_PATH": self.root / "model",
            "CAM_PCI_DIR": self.root / "pci", "CAM_VIDEO_DIR": self.video,
            "CAM_DEV_DIR": self.dev, "CAM_ARCH_RELEASE": self.root / "arch-release",
            "CAM_LOADED_MODULE": self.loaded,
            "CAM_FIRMWARE_HASH": hashlib.sha256(FIRMWARE).hexdigest(),
            "CAM_CALIBRATION_HASH": hashlib.sha256(CALIBRATION).hexdigest(),
        }

    def run_script(self, name="install", mode="", umask="022"):
        assignments = "\n".join(f"{key}={shlex.quote(str(value))}"
                                for key, value in self.paths.items())
        script = (f"source {shlex.quote(str(SCRIPTS / (name + '-camera.sh')))}\n"
                  f"{assignments}\n"
                  "camera_require_user() { :; }\n"
                  "camera_require_root() { :; }\n"
                  f"umask {umask}\nmain\n")
        return subprocess.run(["bash", "-c", script], text=True, capture_output=True,
                              env=dict(self.env, CAMERA_TEST_MODE=mode), timeout=30)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def clear_calls(self):
        self.log.unlink(missing_ok=True)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_no_mutation_commands(self):
        self.assertFalse([call for call in self.calls()
                          if call[0] in {"sudo", "modprobe"}
                          or (call[0] == "dkms" and call[1] != "status")], self.calls())

    def install_firmware(self):
        self.fw.mkdir(parents=True)
        (self.fw / "firmware.bin").write_bytes(FIRMWARE)
        (self.fw / "1675_01XX.dat").write_bytes(CALIBRATION)

    def make_manual_install(self, complete=True):
        self.src.mkdir()
        (self.src / "user-source.c").write_text("keep this source\n")
        if complete:
            (self.root / "module-available").touch()
            self.install_firmware()

    @staticmethod
    def snapshot(directory):
        return {str(path.relative_to(directory)): (path.read_bytes(), path.stat().st_ino,
                                                   path.stat().st_mtime_ns)
                for path in directory.rglob("*") if path.is_file() and not path.is_symlink()}

    def test_wrong_model_and_missing_camera_stop_before_mutation(self):
        (self.root / "model").write_text("MacBook9,1\n")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Only MacBook8,1", result.stderr)
        self.assert_no_mutation_commands()
        (self.root / "model").write_text("MacBook8,1\n")
        (self.root / "pci/0000:02:00.0/device").write_text("0x0000\n")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("14e4:1570 was not found", result.stderr)
        self.assert_no_mutation_commands()
        self.assertFalse(self.src.exists())

    def test_missing_or_mismatched_headers_stop_before_download(self):
        release = self.headers / "include/config/kernel.release"
        for content in (None, "different-kernel\n"):
            with self.subTest(content=content):
                release.unlink(missing_ok=True)
                if content is not None:
                    release.write_text(content)
                self.clear_calls()
                result = self.run_script()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("headers", result.stderr.lower())
                self.assert_no_mutation_commands()
                self.assertFalse([call for call in self.calls() if call[0] == "git"])

    def test_complete_manual_install_is_preserved_and_not_adopted(self):
        self.make_manual_install()
        before = self.snapshot(self.src), self.snapshot(self.fw)
        shutil.rmtree(self.headers)
        result = self.run_script()
        self.assert_success(result)
        self.assertIn("not adopted", result.stdout)
        self.assertEqual(before, (self.snapshot(self.src), self.snapshot(self.fw)))
        self.assertFalse((self.src / ".macbook81-camera-owner").exists())
        self.assert_no_mutation_commands()

    def test_incomplete_manual_install_is_preserved(self):
        self.make_manual_install(complete=False)
        before = self.snapshot(self.src)
        for module_available in (False, True):
            with self.subTest(module_available=module_available):
                if module_available:
                    (self.root / "module-available").touch()
                result = self.run_script()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("existing facetimehd installation needs inspection", result.stderr)
                self.assertEqual(before, self.snapshot(self.src))
                self.assert_no_mutation_commands()

    def test_different_firmware_is_never_overwritten(self):
        self.install_firmware()
        (self.fw / "firmware.bin").write_bytes(b"an existing firmware version")
        before = self.snapshot(self.fw)
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Preserving different", result.stderr)
        self.assertEqual(before, self.snapshot(self.fw))
        self.assert_no_mutation_commands()

    def test_compressed_and_symlink_firmware_are_preserved(self):
        self.fw.mkdir(parents=True)
        for suffix in (".xz", ".zst", ""):
            with self.subTest(suffix=suffix):
                target = self.fw / ("firmware.bin" + suffix)
                if suffix:
                    target.write_bytes(b"existing compressed firmware")
                else:
                    target.symlink_to(self.root / "firmware-fixture/firmware.bin")
                result = self.run_script()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Preserving", result.stderr)
                self.assertTrue(target.exists())
                self.assert_no_mutation_commands()
                target.unlink()

    def test_download_pin_extraction_and_hash_failures_precede_privilege(self):
        for mode in ("fetch-failure", "wrong-pin-firmware", "extraction-failure",
                     "bad-hash-firmware.bin", "bad-hash-1675_01XX.dat",
                     "wrong-pin-driver", "wrong-dkms-version"):
            with self.subTest(mode=mode):
                self.clear_calls()
                result = self.run_script(mode=mode)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assert_no_mutation_commands()
                self.assertFalse(self.src.exists())
                self.assertFalse(self.fw.exists())
                self.assertFalse(self.dkms.exists())
                self.assertEqual(list((self.root / "work").iterdir()), [],
                                 result.stdout + result.stderr)

    def test_fresh_install_and_rerun_preserve_source_and_firmware(self):
        self.assert_success(self.run_script(umask="077"))
        self.assertTrue((self.src / ".macbook81-camera-owner").is_file())
        self.assertTrue((self.src / ".macbook81-camera-sha256").is_file())
        self.assertEqual((self.dkms / "0.7.0.1/source").resolve(), self.src)
        self.assertEqual((self.fw / "firmware.bin").read_bytes(), FIRMWARE)
        self.assertEqual((self.fw / "1675_01XX.dat").read_bytes(), CALIBRATION)
        self.assertTrue(self.loaded.is_dir())
        self.assertEqual((self.src / ".macbook81-camera-owner").stat().st_mode & 0o777, 0o644)
        before = self.snapshot(self.src), self.snapshot(self.fw)
        self.clear_calls()
        self.assert_success(self.run_script())
        self.assertEqual(before, (self.snapshot(self.src), self.snapshot(self.fw)))
        self.assertFalse([call for call in self.calls() if call[0] in {"git", "make"}])
        self.assertFalse([call for call in self.calls()
                          if call[0] == "dkms" and call[1] in {"add", "install"}])

    def test_failed_build_can_be_retried_without_replacing_prepared_files(self):
        result = self.run_script(mode="build-failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("retained for diagnosis/retry", result.stderr)
        before = self.snapshot(self.src), self.snapshot(self.fw)
        self.clear_calls()
        self.assert_success(self.run_script())
        self.assertEqual(before, (self.snapshot(self.src), self.snapshot(self.fw)))
        self.assertFalse([call for call in self.calls() if call[0] in {"git", "make"}])
        self.assertTrue((self.dkms / "0.7.0.1/installed").exists())

    def test_uninstaller_refuses_manual_source(self):
        self.make_manual_install()
        before = self.snapshot(self.src), self.snapshot(self.fw)
        result = self.run_script("uninstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not owned by this installer", result.stderr)
        self.assertEqual(before, (self.snapshot(self.src), self.snapshot(self.fw)))
        self.assert_no_mutation_commands()

    def test_changed_managed_source_blocks_retry_and_uninstall(self):
        self.assert_success(self.run_script())
        (self.src / "driver.c").write_text("user changes\n")
        before = self.snapshot(self.src), self.snapshot(self.fw)
        self.clear_calls()
        for operation in ("install", "uninstall"):
            with self.subTest(operation=operation):
                result = self.run_script(operation)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("driver source has changed", result.stderr)
                self.assertEqual(before, (self.snapshot(self.src), self.snapshot(self.fw)))
                self.assert_no_mutation_commands()

    def test_foreign_dkms_source_blocks_uninstall(self):
        self.assert_success(self.run_script())
        foreign = self.root / "foreign-source"
        foreign.mkdir()
        (foreign / "keep").write_text("another installation\n")
        registered = self.dkms / "0.7.0.1/source"
        registered.unlink()
        registered.symlink_to(foreign, target_is_directory=True)
        self.clear_calls()
        result = self.run_script("uninstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("different source directory", result.stderr)
        self.assertTrue((foreign / "keep").is_file())
        self.assertTrue(self.src.is_dir())
        self.assertEqual(registered.resolve(), foreign)
        self.assert_no_mutation_commands()

    def test_added_local_file_or_link_is_preserved_on_retry_and_uninstall(self):
        self.assert_success(self.run_script())
        target = self.root / "user-notes"
        target.write_text("keep my notes\n")
        for kind in ("file", "symlink"):
            with self.subTest(kind=kind):
                addition = self.src / ".macbook81-camera-notes"
                if kind == "file":
                    addition.write_text("keep local notes\n")
                else:
                    addition.symlink_to(target)
                before = self.snapshot(self.src), self.snapshot(self.fw)
                self.clear_calls()
                for operation in ("install", "uninstall"):
                    result = self.run_script(operation)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(before, (self.snapshot(self.src), self.snapshot(self.fw)))
                    self.assertTrue(addition.exists())
                    self.assertEqual(target.read_text(), "keep my notes\n")
                    self.assert_no_mutation_commands()
                addition.unlink()

    def test_unexpected_dkms_symlinks_are_preserved(self):
        self.assert_success(self.run_script())
        foreign = self.root / "foreign-version"
        foreign.mkdir()
        for name in ("9.9.9", "kernel-foreign-x86_64"):
            with self.subTest(name=name):
                entry = self.dkms / name
                entry.symlink_to(foreign, target_is_directory=True)
                self.clear_calls()
                for operation in ("install", "uninstall"):
                    result = self.run_script(operation)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("unexpected DKMS entry", result.stderr)
                    self.assertEqual(entry.resolve(), foreign)
                    self.assertTrue(self.src.is_dir())
                    self.assert_no_mutation_commands()
                entry.unlink()
        # A normal per-kernel link into this installation remains acceptable.
        own_target = self.dkms / "0.7.0.1/fixture-kernel/x86_64"
        own_target.mkdir(parents=True)
        (self.dkms / "kernel-fixture-kernel-x86_64").symlink_to(own_target, target_is_directory=True)
        self.assert_success(self.run_script())

    def test_busy_module_stops_uninstall_before_file_removal(self):
        self.assert_success(self.run_script())
        before = self.snapshot(self.src), self.snapshot(self.fw)
        self.clear_calls()
        result = self.run_script("uninstall", mode="busy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no files were removed", result.stderr)
        self.assertEqual(before, (self.snapshot(self.src), self.snapshot(self.fw)))
        self.assertTrue((self.dkms / "0.7.0.1/installed").exists())
        self.assertFalse([call for call in self.calls() if call[:2] == ["dkms", "remove"]])

    def test_managed_uninstall_preserves_all_firmware_and_unrelated_source(self):
        self.assert_success(self.run_script())
        (self.fw / "other-sensor.dat").write_bytes(b"keep other firmware")
        other = self.src.parent / "another-driver"
        other.mkdir()
        (other / "keep").touch()
        before = self.snapshot(self.fw), self.snapshot(other)
        self.clear_calls()
        self.assert_success(self.run_script("uninstall"))
        self.assertFalse(self.src.exists())
        self.assertFalse((self.dkms / "0.7.0.1").exists())
        self.assertFalse(self.loaded.exists())
        self.assertEqual(before, (self.snapshot(self.fw), self.snapshot(other)))

    def test_partial_build_rollback_needs_no_loaded_module(self):
        self.assertNotEqual(self.run_script(mode="build-failure").returncode, 0)
        self.assertFalse(self.loaded.exists())
        before = self.snapshot(self.fw)
        self.clear_calls()
        self.assert_success(self.run_script("uninstall"))
        self.assertFalse(self.src.exists())
        self.assertEqual(before, self.snapshot(self.fw))
        self.assertFalse([call for call in self.calls() if call[0] == "modprobe"])

    def test_diagnostics_are_read_only_and_find_the_facetimehd_node(self):
        self.make_manual_install()
        self.loaded.mkdir(parents=True)
        node = self.video / "video3"
        (node / "device/driver").mkdir(parents=True)
        (node / "name").write_text("FaceTime HD Camera\n")
        (node / "device/driver/module").symlink_to(self.loaded, target_is_directory=True)
        (self.dev / "video3").touch()
        before = self.snapshot(self.src), self.snapshot(self.fw)
        result = self.run_script("check")
        self.assert_success(result)
        self.assertIn(f"mpv av://v4l2:{self.dev}/video3", result.stdout)
        self.assertIn("does not prove live capture", result.stdout)
        self.assertEqual(before, (self.snapshot(self.src), self.snapshot(self.fw)))
        self.assert_no_mutation_commands()


if __name__ == "__main__":
    unittest.main()
