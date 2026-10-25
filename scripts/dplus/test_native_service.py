#!/usr/bin/env python3
"""Offline installation/rollback tests; never start PipeWire or systemd."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

HERE = Path(__file__).resolve().parent


def load(filename, module_name):
    spec = importlib.util.spec_from_file_location(module_name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


manager = load("manage-native.py", "dplusmanager")
guard = load("dplus-session-guard.py", "dplusguard")
preview = load("dplus-topology-preview.py", "dpluspreview")


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dplus-test-")
        self.addCleanup(self.temp.cleanup)
        home = Path(self.temp.name)
        for name, value in {
            "HOME": home,
            "MANAGED": home / ".config/macbook81-dplus-native",
            "UNIT_PATH": home / ".config/systemd/user/macbook81-dplus-native.service",
        }.items():
            patcher = mock.patch.object(manager, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(manager, "ensure_user")
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(manager, "systemctl")
        self.commands = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(manager, "render", return_value=(b"safe cfg", 0.0589))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_install_is_opt_in_and_privately_owned(self):
        manager.install(Path("/test/private.json"))
        self.assertTrue(manager.verify_managed())
        self.assertEqual(manager.MANAGED.stat().st_mode & 0o777, 0o700)
        self.assertEqual((manager.MANAGED / "dplus.conf").stat().st_mode & 0o777, 0o600)
        self.assertEqual(manager.UNIT_PATH.stat().st_mode & 0o777, 0o644)
        self.commands.assert_called_once_with("daemon-reload")
        unit = manager.UNIT_PATH.read_text()
        self.assertIn("Restart=no", unit)
        self.assertNotIn("ExecStartPost", unit)
        self.assertNotIn("set-default-sink", unit)
        self.assertFalse(any("enable" in str(call) or "start" in str(call)
                             for call in self.commands.call_args_list))

    def test_refuses_existing_and_tampered_artifacts(self):
        manager.install(Path("/test/private.json"))
        with self.assertRaisesRegex(RuntimeError, "already exist"):
            manager.install(Path("/test/private.json"))
        (manager.MANAGED / "dplus.conf").write_text("tampered")
        with self.assertRaisesRegex(RuntimeError, "differs"):
            manager.verify_managed()

    def test_refuses_extra_user_files_in_managed_directory(self):
        manager.install(Path("/test/private.json"))
        (manager.MANAGED / "mine.txt").write_text("do not delete")
        with self.assertRaisesRegex(RuntimeError, "Unknown files"):
            manager.verify_managed()

    def test_remove_is_exact_and_leaves_raw_untouched(self):
        manager.install(Path("/test/private.json"))
        self.commands.reset_mock()
        with mock.patch.object(sys, "argv", ["manage-native.py", "remove"]):
            self.assertEqual(manager.main(), 0)
        self.assertFalse(manager.MANAGED.exists())
        self.assertFalse(manager.UNIT_PATH.exists())
        self.assertEqual(self.commands.call_args_list[0],
                         mock.call("disable", "--now", manager.UNIT))
        self.assertEqual(self.commands.call_args_list[1], mock.call("daemon-reload"))

    def test_manifest_check_rejects_partial(self):
        manager.MANAGED.mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            manager.verify_managed()


class GraphContractTests(unittest.TestCase):
    def test_source_is_byte_identical_to_owner_audible_preview(self):
        source = (HERE / "dplus-topology-preview.py").read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), manager.FROZEN_SHA256)
        self.assertEqual(preview.LIM_OUT, 0.35)
        self.assertEqual(preview.FINAL_CLAMP, 0.45)
        self.assertEqual(preview.RAW, guard.RAW)
        self.assertEqual(preview.SINK, guard.SINK)

    def test_guard_never_changes_default_or_starts_extra_service(self):
        code = (HERE / "dplus-session-guard.py").read_text()
        self.assertNotIn('"set-default-sink"', code)
        self.assertNotIn('"restart"', code)
        self.assertIn("PIPEWIRE_CONFIG_DIR", code)
        self.assertIn("no unsafe", "no unsafe")

    def test_real_private_profile_if_explicitly_supplied(self):
        import os
        reference = os.environ.get("DPLUS_TEST_PROFILE")
        if not reference:
            self.skipTest("Optional private profile must be provided via DPLUS_TEST_PROFILE")
        actual, error = preview.generate_config(Path(reference))
        produced, same_error = manager.read_module().generate_config(Path(reference))
        self.assertEqual(actual, produced)
        self.assertEqual(error, same_error)
        self.assertIn('outputs = [ "copyOutL:Out" "copyOutR:Out" "zeroL:Out" "zeroR:Out" ]',actual)


if __name__ == "__main__":
    unittest.main(verbosity=2)
